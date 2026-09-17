"""Durable control-plane workflow. Only the checked-in synthetic fixture is executable."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import Engine, and_, func, or_, select
from sqlalchemy.orm import Session

from dtd_api.models import (
    Dataset,
    DatasetVersion,
    Outbox,
    Project,
    Run,
    RunEvent,
    StageAttempt,
    User,
    WorkItem,
    now,
)

TERMINAL = {"succeeded", "succeeded_with_warnings", "failed", "cancelled"}
STAGES = ("profile_fixture", "summarize_fixture", "publish_fixture")
LEASE_SECONDS = 5
MAX_ATTEMPTS = 3
DEADLINE_SECONDS = 600


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def emit(db: Session, run: Run, kind: str, payload: dict[str, object]) -> None:
    """Caller holds the run row lock; sequence and state commit atomically."""
    run.event_sequence += 1
    db.add(RunEvent(run_id=run.id, sequence=run.event_sequence, type=kind, payload=payload))


def inputs_available(db: Session, run: Run) -> bool:
    return (
        db.scalar(
            select(Project.id)
            .join(User, Project.owner_id == User.id)
            .join(Dataset, Dataset.project_id == Project.id)
            .join(DatasetVersion, DatasetVersion.dataset_id == Dataset.id)
            .where(
                Project.id == run.project_id,
                DatasetVersion.id == run.dataset_version_id,
                Project.deleted_at.is_(None),
                Dataset.deleted_at.is_(None),
                Dataset.status == "ready",
                User.active.is_(True),
            )
            .with_for_update(of=(Project, Dataset, User))
        )
        is not None
    )


def terminal(db: Session, run: Run, job: WorkItem | None, status: str, reason: str) -> None:
    run.status = status
    run.finished_at = now()
    if job:
        job.state = "done"
        job.token = None
        job.lease_expires_at = None
    for attempt in db.scalars(
        select(StageAttempt).where(StageAttempt.run_id == run.id, StageAttempt.status == "running")
    ):
        attempt.status = "cancelled" if status == "cancelled" else "failed"
    emit(db, run, "run_finished", {"status": status, "reason": reason, "mode": "synthetic"})


def dispatch_one(engine: Engine) -> bool:
    """Transactional outbox delivery; duplicate messages cannot create duplicate work items."""
    with Session(engine) as db, db.begin():
        message = db.scalar(
            select(Outbox)
            .where(Outbox.delivered_at.is_(None))
            .order_by(Outbox.created_at, Outbox.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if message is None:
            return False
        run_id = message.payload.get("run_id")
        run = (
            db.scalar(
                select(Run)
                .where(Run.id == run_id, Run.project_id == message.project_id)
                .with_for_update()
            )
            if isinstance(run_id, str)
            else None
        )
        if message.topic == "run.requested" and run is not None and run.status not in TERMINAL:
            if db.get(WorkItem, run.id) is None:
                db.add(WorkItem(run_id=run.id, state="pending"))
        message.delivered_at = now()
        return True


@dataclass(frozen=True)
class Claim:
    run_id: str
    token: str
    generation: int
    stage: str
    attempt_id: str


def claim_one(engine: Engine) -> Claim | None:
    with Session(engine) as db, db.begin():
        timestamp = now()
        run = db.scalar(
            select(Run)
            .join(WorkItem, WorkItem.run_id == Run.id)
            .where(
                Run.status.in_(["queued", "running", "cancelling"]),
                or_(
                    WorkItem.state == "pending",
                    and_(WorkItem.state == "leased", WorkItem.lease_expires_at <= timestamp),
                ),
            )
            .order_by(Run.created_at, Run.id)
            .with_for_update(of=Run, skip_locked=True)
            .limit(1)
        )
        if run is None:
            return None
        job = db.get(WorkItem, run.id)
        assert job is not None
        if run.status == "cancelling" or not inputs_available(db, run):
            terminal(db, run, job, "cancelled", "Cancellation or unavailable input")
            return None
        if run.config != {"mode": "synthetic", "fixture": "sales-v1"}:
            terminal(db, run, job, "failed", "Unsupported workflow; execution remains disabled")
            return None
        if run.started_at and (timestamp - utc(run.started_at)).total_seconds() >= DEADLINE_SECONDS:
            terminal(db, run, job, "failed", "Run deadline exceeded")
            return None
        stage = next((item for item in STAGES if item not in run.checkpoint), None)
        if stage is None:
            terminal(db, run, job, "failed", "Invalid workflow checkpoint")
            return None
        previous = (
            db.scalar(
                select(func.max(StageAttempt.attempt_number)).where(
                    StageAttempt.run_id == run.id, StageAttempt.stage == stage
                )
            )
            or 0
        )
        if previous >= MAX_ATTEMPTS:
            terminal(db, run, job, "failed", "Stage retry budget exhausted")
            return None
        for old in db.scalars(
            select(StageAttempt).where(
                StageAttempt.run_id == run.id, StageAttempt.status == "running"
            )
        ):
            old.status = "failed"
        if job.state == "leased":
            emit(db, run, "warning", {"code": "LEASE_RECOVERED", "stage": stage})
        run.generation += 1
        run.status = "running"
        run.stage = stage
        run.started_at = run.started_at or timestamp
        job.state = "leased"
        job.token = str(uuid4())
        job.lease_expires_at = timestamp + timedelta(seconds=LEASE_SECONDS)
        attempt = StageAttempt(
            run_id=run.id,
            stage=stage,
            attempt_number=previous + 1,
            lease_expires_at=job.lease_expires_at,
            status="running",
        )
        db.add(attempt)
        db.flush()
        emit(db, run, "stage_started", {"stage": stage, "attempt": previous + 1})
        return Claim(run.id, job.token, run.generation, stage, attempt.id)


def heartbeat(engine: Engine, claim: Claim) -> bool:
    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if not valid_claim(run, job, claim):
            return False
        assert job is not None
        job.lease_expires_at = now() + timedelta(seconds=LEASE_SECONDS)
        attempt = db.get(StageAttempt, claim.attempt_id)
        if attempt:
            attempt.lease_expires_at = job.lease_expires_at
        return True


def valid_claim(run: Run | None, job: WorkItem | None, claim: Claim) -> bool:
    return bool(
        run
        and job
        and run.status == "running"
        and run.generation == claim.generation
        and job.state == "leased"
        and job.token == claim.token
        and job.lease_expires_at
        and utc(job.lease_expires_at) > now()
    )


def fixture_result(stage: str) -> dict[str, object]:
    """Fixed, reviewed arithmetic only. Never parse uploaded data or evaluate supplied code here."""
    if stage == "profile_fixture":
        return {"rows": 3, "columns": 3, "source": "checked-in synthetic aggregates"}
    if stage in {"summarize_fixture", "publish_fixture"}:
        return {"revenue": 12800 + 9600 + 4800, "orders": 80 + 64 + 32, "mode": "synthetic"}
    raise ValueError("Unknown fixed stage")


def complete(engine: Engine, claim: Claim, output: dict[str, object]) -> bool:
    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled", "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None
        if not inputs_available(db, run):
            terminal(db, run, job, "cancelled", "Input or owner no longer available")
            return False
        if run.started_at and (now() - utc(run.started_at)).total_seconds() >= DEADLINE_SECONDS:
            terminal(db, run, job, "failed", "Run deadline exceeded")
            return False
        if len(json.dumps(output)) > 65536 or output != fixture_result(claim.stage):
            terminal(db, run, job, "failed", "Synthetic stage output failed validation")
            return False
        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"
        run.checkpoint = {**run.checkpoint, claim.stage: output}
        emit(db, run, "stage_completed", {"stage": claim.stage})
        job.token = None
        job.lease_expires_at = None
        if claim.stage == STAGES[-1]:
            run.result = output
            terminal(db, run, job, "succeeded", "Synthetic workflow completed; no model executed")
        else:
            job.state = "pending"
        return True


def work_once(engine: Engine) -> bool:
    dispatched = dispatch_one(engine)
    claim = claim_one(engine)
    if claim is None:
        return dispatched
    complete(engine, claim, fixture_result(claim.stage))
    return True
