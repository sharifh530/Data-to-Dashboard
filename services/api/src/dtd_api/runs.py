import asyncio
import json
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from anyio import to_thread
from fastapi import APIRouter, Header, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import model_validator
from sqlalchemy import Engine, delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dtd_api.auth import AUTH, DB, MUTATION, digest
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.models import (
    AuditEvent,
    Dataset,
    DatasetVersion,
    IdempotencyRecord,
    Outbox,
    Project,
    Run,
    RunEvent,
    User,
    WebSession,
    WorkItem,
    new_id,
    now,
)
from dtd_api.projects import KEY, owned
from dtd_api.run_engine import TERMINAL, emit, terminal, utc

router = APIRouter(prefix="/api/v1", tags=["Synthetic runs"])


class DemoRunCreate(Contract):
    fixture: Literal["sales-v1"] = "sales-v1"


class AnalysisRunCreate(Contract):
    dataset_version_id: UUID
    target_column: str | None = None
    task_type: Literal["classification", "regression"] | None = None

    @model_validator(mode="after")
    def validate_target(self) -> "AnalysisRunCreate":
        if bool(self.target_column) != bool(self.task_type):
            raise ValueError("target_column and task_type must be provided together")
        return self


class RunView(Contract):
    id: UUID
    project_id: UUID
    mode: Literal["synthetic", "analysis"] = "synthetic"
    status: str
    stage: str | None
    event_sequence: int
    completed_stages: list[str]
    result: dict[str, object] | None
    dataset_version_id: UUID | None = None


class RunPage(Contract):
    items: list[RunView]
    next_cursor: str | None


def view(run: Run) -> RunView:
    mode: Literal["synthetic", "analysis"] = (
        "analysis"
        if isinstance(run.config, dict) and run.config.get("mode") == "analysis"
        else "synthetic"
    )
    return RunView(
        id=UUID(run.id),
        project_id=UUID(run.project_id),
        mode=mode,
        status=run.status,
        stage=run.stage,
        event_sequence=run.event_sequence,
        completed_stages=list(run.checkpoint),
        result=run.result,
        dataset_version_id=UUID(run.dataset_version_id) if run.dataset_version_id else None,
    )


def owned_run(db: Session, run_id: str, owner_id: str, lock: bool = False) -> Run:
    query = (
        select(Run)
        .join(Project, Project.id == Run.project_id)
        .join(DatasetVersion, DatasetVersion.id == Run.dataset_version_id)
        .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
        .where(
            Run.id == run_id,
            Project.owner_id == owner_id,
            Project.deleted_at.is_(None),
            Dataset.deleted_at.is_(None),
        )
    )
    if lock:
        query = query.with_for_update(of=Run)
    run = db.scalar(query)
    if run is None:
        raise ApiError(404, "NOT_FOUND", "Run not found.")
    return run


@router.post("/projects/{project_id}/demo-runs", response_model=RunView, status_code=202)
def create_demo(
    project_id: UUID,
    body: DemoRunCreate,
    request: Request,
    principal: MUTATION,
    db: DB,
    idempotency_key: KEY,
) -> RunView:
    owned(db, str(project_id), principal.user.id)
    db.execute(select(User).where(User.id == principal.user.id).with_for_update()).scalar_one()
    route = f"POST /projects/{project_id}/demo-runs"
    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.owner_id == principal.user.id,
            IdempotencyRecord.route == route,
            IdempotencyRecord.key == idempotency_key,
            IdempotencyRecord.expires_at <= now(),
        )
    )
    fingerprint = digest(json.dumps(body.model_dump(), sort_keys=True))
    replay = db.get(IdempotencyRecord, (principal.user.id, route, idempotency_key))
    if replay:
        if replay.request_hash != fingerprint:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Key belongs to a different request.")
        return view(owned_run(db, replay.resource_id, principal.user.id))
    active = db.scalar(
        select(Run.id)
        .join(Project, Project.id == Run.project_id)
        .where(Project.owner_id == principal.user.id, Run.status.not_in(TERMINAL))
        .limit(1)
    )
    if active:
        raise ApiError(
            429, "RUN_LIMIT", "Finish or cancel your current run before starting another."
        )
    # Fixture references are not uploaded files and cannot select executable source.
    dataset = Dataset(
        project_id=str(project_id),
        format="csv",
        status="ready",
        raw_key="fixtures/sales-v1/" + new_id(),
        raw_sha256=digest("sales-v1:12800,9600,4800:80,64,32"),
    )
    db.add(dataset)
    db.flush()
    version = DatasetVersion(
        dataset_id=dataset.id, project_id=str(project_id), selection={"fixture": "sales-v1"}
    )
    db.add(version)
    db.flush()
    run = Run(
        project_id=str(project_id),
        dataset_version_id=version.id,
        config={"mode": "synthetic", "fixture": body.fixture},
    )
    db.add(run)
    db.flush()
    emit(db, run, "run_queued", {"mode": "synthetic", "fixture": body.fixture})
    db.add(Outbox(project_id=run.project_id, topic="run.requested", payload={"run_id": run.id}))
    db.add(
        IdempotencyRecord(
            owner_id=principal.user.id,
            route=route,
            key=idempotency_key,
            request_hash=fingerprint,
            resource_id=run.id,
            expires_at=now() + timedelta(hours=24),
        )
    )
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="run.created",
            resource_id=run.id,
            request_id=request.state.request_id,
        )
    )
    db.commit()
    return view(run)


@router.post("/projects/{project_id}/runs", response_model=RunView, status_code=202)
def create_analysis_run(
    project_id: UUID,
    body: AnalysisRunCreate,
    request: Request,
    principal: MUTATION,
    db: DB,
    idempotency_key: KEY,
) -> RunView:
    owned(db, str(project_id), principal.user.id)
    db.execute(select(User).where(User.id == principal.user.id).with_for_update()).scalar_one()
    route = f"POST /projects/{project_id}/runs"
    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.owner_id == principal.user.id,
            IdempotencyRecord.route == route,
            IdempotencyRecord.key == idempotency_key,
            IdempotencyRecord.expires_at <= now(),
        )
    )
    fingerprint = digest(json.dumps(body.model_dump(mode="json"), sort_keys=True))
    replay = db.get(IdempotencyRecord, (principal.user.id, route, idempotency_key))
    if replay:
        if replay.request_hash != fingerprint:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Key belongs to a different request.")
        return view(owned_run(db, replay.resource_id, principal.user.id))
    active = db.scalar(
        select(Run.id)
        .join(Project, Project.id == Run.project_id)
        .where(Project.owner_id == principal.user.id, Run.status.not_in(TERMINAL))
        .limit(1)
    )
    if active:
        raise ApiError(
            429, "RUN_LIMIT", "Finish or cancel your current run before starting another."
        )

    version_id = str(body.dataset_version_id)
    version = db.scalar(
        select(DatasetVersion).where(
            DatasetVersion.id == version_id, DatasetVersion.project_id == str(project_id)
        )
    )
    if version is None:
        raise ApiError(404, "NOT_FOUND", "Dataset version not found.")

    from dtd_api.models import Profile

    profile = db.get(Profile, version_id)
    if profile is None or profile.status != "ready":
        raise ApiError(409, "PROFILE_REQUIRED", "Dataset version must be profiled before analysis.")

    config: dict[str, object] = {"mode": "analysis", "dataset_version_id": version.id}
    if body.target_column:
        config["target_column"] = body.target_column
        config["task_type"] = body.task_type

    run = Run(
        project_id=str(project_id),
        dataset_version_id=version.id,
        config=config,
    )
    db.add(run)
    db.flush()
    emit(db, run, "run_queued", {"mode": "analysis", "dataset_version_id": version.id})
    db.add(Outbox(project_id=run.project_id, topic="run.requested", payload={"run_id": run.id}))
    db.add(
        IdempotencyRecord(
            owner_id=principal.user.id,
            route=route,
            key=idempotency_key,
            request_hash=fingerprint,
            resource_id=run.id,
            expires_at=now() + timedelta(hours=24),
        )
    )
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="run.created",
            resource_id=run.id,
            request_id=request.state.request_id,
        )
    )
    db.commit()
    return view(run)


@router.get("/projects/{project_id}/runs", response_model=RunPage)
def history(
    project_id: UUID,
    principal: AUTH,
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> RunPage:
    owned(db, str(project_id), principal.user.id)
    query = (
        select(Run)
        .join(DatasetVersion, DatasetVersion.id == Run.dataset_version_id)
        .join(Dataset, Dataset.id == DatasetVersion.dataset_id)
        .where(Run.project_id == str(project_id), Dataset.deleted_at.is_(None))
    )
    if cursor:
        boundary = owned_run(db, str(cursor), principal.user.id)
        if boundary.project_id != str(project_id):
            raise ApiError(404, "NOT_FOUND", "Run cursor not found.")
        query = query.where(Run.id > str(cursor))
    results = list(db.scalars(query.order_by(Run.id).limit(limit + 1)))
    return RunPage(
        items=[view(run) for run in results[:limit]],
        next_cursor=results[limit - 1].id if len(results) > limit else None,
    )


@router.get("/runs/{run_id}", response_model=RunView)
def detail(run_id: UUID, principal: AUTH, db: DB) -> RunView:
    return view(owned_run(db, str(run_id), principal.user.id))


@router.post("/runs/{run_id}/cancel", response_model=RunView)
def cancel(run_id: UUID, request: Request, principal: MUTATION, db: DB) -> RunView:
    run = owned_run(db, str(run_id), principal.user.id, lock=True)
    if run.status in TERMINAL or run.status == "cancelling":
        return view(run)
    run.cancellation_at = now()
    run.generation += 1
    job = db.get(WorkItem, run.id)
    if job and job.state == "leased" and job.lease_expires_at and utc(job.lease_expires_at) > now():
        run.status = "cancelling"
        emit(db, run, "cancellation_requested", {"status": "cancelling"})
    else:
        terminal(db, run, job, "cancelled", "Cancelled before active work")
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="run.cancelled",
            resource_id=run.id,
            request_id=request.state.request_id,
        )
    )
    db.commit()
    return view(run)


def event_batch(
    engine: Engine, run_id: str, owner_id: str, token: str, cursor: int
) -> tuple[list[dict[str, object]], bool]:
    with Session(engine) as db:
        valid = db.scalar(
            select(WebSession.user_id)
            .join(User, User.id == WebSession.user_id)
            .where(
                WebSession.token_hash == digest(token),
                WebSession.user_id == owner_id,
                WebSession.expires_at > now(),
                User.active.is_(True),
            )
        )
        if not valid:
            raise ApiError(401, "UNAUTHENTICATED", "Session expired or revoked.")
        run = owned_run(db, run_id, owner_id)
        if cursor > run.event_sequence:
            raise ApiError(409, "INVALID_CURSOR", "Event cursor is ahead of this run.")
        rows = list(
            db.scalars(
                select(RunEvent)
                .where(RunEvent.run_id == run_id, RunEvent.sequence > cursor)
                .order_by(RunEvent.sequence)
                .limit(100)
            )
        )
        if cursor < run.event_sequence and (not rows or rows[0].sequence != cursor + 1):
            return [
                {
                    "sequence": run.event_sequence,
                    "type": "snapshot",
                    "run_id": run_id,
                    "schema_version": "1",
                    "payload": view(run).model_dump(mode="json"),
                }
            ], run.status in TERMINAL
        events = [
            {
                "sequence": row.sequence,
                "type": row.type,
                "run_id": run_id,
                "schema_version": "1",
                "timestamp": utc(row.created_at).isoformat(),
                "payload": row.payload,
            }
            for row in rows
        ]
        return events, run.status in TERMINAL and (
            not rows or rows[-1].sequence == run.event_sequence
        )


@router.get(
    "/runs/{run_id}/events",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/event-stream": {"schema": {"type": "string"}}}}},
)
async def events(
    run_id: UUID,
    request: Request,
    principal: AUTH,
    db: DB,
    last_event_id: Annotated[str, Header(pattern=r"^[0-9]{1,10}$")] = "0",
    follow: bool = True,
) -> StreamingResponse:
    owner_id, token = principal.user.id, principal.token
    engine: Engine = request.app.state.engine
    # Never retain the request dependency transaction for the stream lifetime.
    db.close()
    first = await to_thread.run_sync(
        event_batch, engine, str(run_id), owner_id, token, int(last_event_id)
    )

    async def stream() -> AsyncIterator[str]:
        cursor = int(last_event_id)
        batch, finished = first
        for tick in range(50):
            for event in batch:
                cursor = int(str(event["sequence"]))
                yield f"id: {cursor}\nevent: {event['type']}\ndata: {json.dumps(event)}\n\n"
            if finished or not follow or await request.is_disconnected():
                return
            if tick % 10 == 0:
                yield ": keep-alive\nretry: 1000\n\n"
            await asyncio.sleep(0.5)
            try:
                batch, finished = await to_thread.run_sync(
                    event_batch, engine, str(run_id), owner_id, token, cursor
                )
            except ApiError:
                yield 'event: access_revoked\ndata: {"code":"ACCESS_REVOKED"}\n\n'
                return
            except SQLAlchemyError:
                yield 'event: reconnect\ndata: {"code":"TEMPORARILY_UNAVAILABLE"}\n\n'
                return

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"}
    )
