"""Durable control-plane workflow. Only the checked-in synthetic fixture is executable."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import Engine, and_, func, or_, select
from sqlalchemy.orm import Session

from dtd_api.artifacts import store_artifact
from dtd_api.baseline_generator import generate_baseline_workflow
from dtd_api.cleaning_generator import generate_cleaning_workflow
from dtd_api.dashboard_contracts import DashboardSpec
from dtd_api.dashboard_generator import generate_dashboard_spec
from dtd_api.inspection_contracts import ProfileReport
from dtd_api.models import (
    Dashboard,
    Dataset,
    DatasetVersion,
    Outbox,
    Profile,
    Project,
    RawUpload,
    Run,
    RunEvent,
    StageAttempt,
    User,
    WorkItem,
    new_id,
    now,
)
from dtd_api.react_generator import ReactSecurityError, generate_react_dashboard
from dtd_api.transformations import run_isolated_transform
from dtd_api.ui_compiler import CompilationResult, compile_dashboard_ui

TERMINAL = {"succeeded", "succeeded_with_warnings", "failed", "cancelled"}
STAGES = ("profile_fixture", "summarize_fixture", "publish_fixture")
ANALYSIS_STAGES = ("clean_dataset", "train_baseline",
                   "plan_dashboard", "compile_dashboard")
LEASE_SECONDS = 5
MAX_ATTEMPTS = 3
DEADLINE_SECONDS = 600


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def emit(db: Session, run: Run, kind: str, payload: dict[str, object]) -> None:
    """Caller holds the run row lock; sequence and state commit atomically."""
    run.event_sequence += 1
    db.add(RunEvent(run_id=run.id, sequence=run.event_sequence,
           type=kind, payload=payload))


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
                Dataset.status.in_(["ready", "validating"]),
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
        select(StageAttempt).where(StageAttempt.run_id ==
                                   run.id, StageAttempt.status == "running")
    ):
        attempt.status = "cancelled" if status == "cancelled" else "failed"
    emit(db, run, "run_finished", {
         "status": status, "reason": reason, "mode": "synthetic"})


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
    mode: str = "synthetic"


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
                    and_(WorkItem.state == "leased",
                         WorkItem.lease_expires_at <= timestamp),
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
            terminal(db, run, job, "cancelled",
                     "Cancellation or unavailable input")
            return None
        is_synthetic = run.config == {
            "mode": "synthetic", "fixture": "sales-v1"}
        is_analysis = isinstance(
            run.config, dict) and run.config.get("mode") == "analysis"
        if not (is_synthetic or is_analysis):
            terminal(db, run, job, "failed",
                     "Unsupported workflow; execution remains disabled")
            return None
        if run.started_at and (timestamp - utc(run.started_at)).total_seconds() >= DEADLINE_SECONDS:
            terminal(db, run, job, "failed", "Run deadline exceeded")
            return None
        stages = STAGES if is_synthetic else ANALYSIS_STAGES
        stage = next(
            (item for item in stages if item not in run.checkpoint), None)
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
            emit(db, run, "warning", {
                 "code": "LEASE_RECOVERED", "stage": stage})
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
        emit(db, run, "stage_started", {
             "stage": stage, "attempt": previous + 1})
        return Claim(
            run_id=run.id,
            token=job.token,
            generation=run.generation,
            stage=stage,
            attempt_id=attempt.id,
            mode="analysis" if is_analysis else "synthetic",
        )


def heartbeat(engine: Engine, claim: Claim) -> bool:
    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
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
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled",
                     "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None
        if not inputs_available(db, run):
            terminal(db, run, job, "cancelled",
                     "Input or owner no longer available")
            return False
        if run.started_at and (now() - utc(run.started_at)).total_seconds() >= DEADLINE_SECONDS:
            terminal(db, run, job, "failed", "Run deadline exceeded")
            return False
        is_synthetic = run.config == {
            "mode": "synthetic", "fixture": "sales-v1"}
        if is_synthetic and (
            len(json.dumps(output)) > 65536 or output != fixture_result(claim.stage)
        ):
            terminal(db, run, job, "failed",
                     "Synthetic stage output failed validation")
            return False
        stages = STAGES if is_synthetic else ANALYSIS_STAGES
        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"
        run.checkpoint = {**run.checkpoint, claim.stage: output}
        emit(db, run, "stage_completed", {"stage": claim.stage})
        job.token = None
        job.lease_expires_at = None
        if claim.stage == stages[-1]:
            run.result = output
            terminal(
                db,
                run,
                job,
                "succeeded",
                "Synthetic workflow completed; no model executed"
                if is_synthetic
                else "Dataset analysis completed.",
            )
        else:
            job.state = "pending"
        return True


def execute_clean_dataset(engine: Engine, claim: Claim, transformer_image: str | None) -> bool:
    if not transformer_image:
        with Session(engine) as db, db.begin():
            run = db.scalar(select(Run).where(
                Run.id == claim.run_id).with_for_update())
            job = db.get(WorkItem, claim.run_id)
            if run and job:
                terminal(db, run, job, "failed",
                         "The isolated transformer is not configured.")
        return True

    with Session(engine) as db:
        run = db.get(Run, claim.run_id)
        assert run is not None
        version = db.get(DatasetVersion, run.dataset_version_id)
        if version is None:
            with db.begin():
                run = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run and job:
                    terminal(db, run, job, "failed",
                             "Dataset version not found.")
            return True

        raw = db.get(RawUpload, version.dataset_id)
        profile = db.get(Profile, version.id)
        dataset = db.get(Dataset, version.dataset_id)
        if (
            raw is None
            or profile is None
            or profile.status != "ready"
            or profile.report is None
            or dataset is None
        ):
            with db.begin():
                run = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run and job:
                    terminal(db, run, job, "failed",
                             "Dataset or profile not ready.")
            return True

        profile_report = ProfileReport.model_validate(profile.report)
        sel = version.selection if isinstance(version.selection, dict) else {}
        delim_val = sel.get("delimiter")
        tbl_val = sel.get("table")
        delimiter = str(delim_val) if isinstance(delim_val, str) else None
        table_name = str(tbl_val) if isinstance(tbl_val, str) else None
        raw_bytes = raw.content
        file_format = dataset.format
        project_id = run.project_id

    try:
        script, _ = generate_cleaning_workflow(profile_report)
        cleaning_report, cleaned_csv = run_isolated_transform(
            data=raw_bytes,
            file_format=file_format,
            image=transformer_image,
            script=script,
            delimiter=delimiter,
            table_name=table_name,
        )
    except Exception as exc:
        with Session(engine) as db, db.begin():
            run = db.scalar(select(Run).where(
                Run.id == claim.run_id).with_for_update())
            job = db.get(WorkItem, claim.run_id)
            if run and job:
                terminal(db, run, job, "failed",
                         f"Transformation runtime error: {exc}")
        return True

    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled",
                     "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None

        if cleaning_report.status != "ready":
            terminal(db, run, job, "failed",
                     f"Cleaning rejected: {cleaning_report.error}")
            return False

        store_artifact(db, project_id, claim.run_id,
                       "cleaned_data", "cleaned.csv", cleaned_csv)
        store_artifact(
            db,
            project_id,
            claim.run_id,
            "cleaning_report",
            "cleaning_report.json",
            cleaning_report.model_dump_json().encode(),
        )
        store_artifact(
            db, project_id, claim.run_id, "generated_script", "clean_dataset.py", script.encode()
        )

        output = cleaning_report.model_dump()
        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"
        run.checkpoint = {**run.checkpoint, claim.stage: output}
        emit(db, run, "stage_completed", {"stage": claim.stage})
        job.token = None
        job.lease_expires_at = None
        run.result = output

        # We manually transition here because analysis stages are dynamic based on config
        if claim.stage == ANALYSIS_STAGES[-1] or run.config.get("target_column") is None:
            terminal(db, run, job, "succeeded",
                     "Dataset cleaning completed; artifacts stored.")
        else:
            job.state = "pending"
        return True


def execute_train_baseline(engine: Engine, claim: Claim, transformer_image: str | None) -> bool:
    if not transformer_image:
        with Session(engine) as db, db.begin():
            run = db.scalar(select(Run).where(
                Run.id == claim.run_id).with_for_update())
            job = db.get(WorkItem, claim.run_id)
            if run and job:
                terminal(db, run, job, "failed",
                         "The isolated transformer is not configured.")
        return True

    with Session(engine) as db:
        run = db.get(Run, claim.run_id)
        assert run is not None
        version = db.get(DatasetVersion, run.dataset_version_id)

        target_column = run.config.get("target_column")
        task_type = run.config.get("task_type")

        if not target_column or not task_type:
            # Complete the stage without doing anything if no target
            output: dict[str, object] = {
                "status": "skipped",
                "skip_reason": "No target column specified",
            }  # noqa: E501
            return complete(engine, claim, output)

        if version is None:
            with db.begin():
                run = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run and job:
                    terminal(db, run, job, "failed",
                             "Dataset version not found.")
            return True

        profile = db.get(Profile, version.id)
        if profile is None or profile.status != "ready" or profile.report is None:
            with db.begin():
                run = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run and job:
                    terminal(db, run, job, "failed",
                             "Dataset profile not ready.")
            return True

        profile_report = ProfileReport.model_validate(profile.report)

    with Session(engine) as db:
        run = db.get(Run, claim.run_id)
        assert run is not None
        project_id = run.project_id
        # Fetch the cleaned data artifact from the previous stage
        cleaning_output = run.checkpoint.get("clean_dataset", {})
        if not isinstance(cleaning_output, dict):
            cleaning_output = {}

    from dtd_api.artifacts import ARTIFACTS_DIR

    # Locate cleaned CSV
    cleaned_csv_bytes = None
    artifacts_path = ARTIFACTS_DIR / \
        f"projects/{project_id}/runs/{claim.run_id}/artifacts"
    for attempt_folder in artifacts_path.glob("*"):
        candidate = attempt_folder / "cleaned.csv"
        if candidate.exists():
            cleaned_csv_bytes = candidate.read_bytes()
            break

    if not cleaned_csv_bytes:
        with Session(engine) as db, db.begin():
            run = db.scalar(select(Run).where(
                Run.id == claim.run_id).with_for_update())
            job = db.get(WorkItem, claim.run_id)
            if run and job:
                terminal(db, run, job, "failed",
                         "Cleaned dataset CSV not found.")
        return True

    clean_columns = [
        str(col["clean_name"])
        for col in cleaning_output.get("lineage", [])
        if isinstance(col, dict)
    ]  # noqa: E501

    from typing import Literal, cast

    try:
        task_type_lit = cast(
            Literal["classification", "regression"], str(task_type))
        script, _ = generate_baseline_workflow(
            profile_report, str(target_column), task_type_lit, clean_columns
        )
        baseline_report, _ = run_isolated_transform(
            data=cleaned_csv_bytes,
            file_format="csv",
            image=transformer_image,
            script=script,
            mode="baseline",
        )
    except Exception as exc:
        with Session(engine) as db, db.begin():
            run = db.scalar(select(Run).where(
                Run.id == claim.run_id).with_for_update())
            job = db.get(WorkItem, claim.run_id)
            if run and job:
                terminal(db, run, job, "failed",
                         f"Baseline execution error: {exc}")
        return True

    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled",
                     "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None

        if baseline_report.status == "failed":
            terminal(db, run, job, "failed",
                     f"Baseline modeling failed: {baseline_report.error}")
            return False

        store_artifact(
            db,
            project_id,
            claim.run_id,
            "baseline_report",
            "baseline_report.json",
            baseline_report.model_dump_json().encode(),
        )
        store_artifact(
            db, project_id, claim.run_id, "baseline_script", "train_baseline.py", script.encode()
        )

        output = baseline_report.model_dump()
        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"
        run.checkpoint = {**run.checkpoint, claim.stage: output}
        emit(db, run, "stage_completed", {"stage": claim.stage})
        job.token = None
        job.lease_expires_at = None

        if claim.stage == ANALYSIS_STAGES[-1]:
            run.result = output
            terminal(
                db,
                run,
                job,
                "succeeded",
                "Dataset analysis completed.",
            )
        else:
            job.state = "pending"

        return True


def execute_plan_dashboard(engine: Engine, claim: Claim) -> bool:
    with Session(engine) as db:
        run = db.get(Run, claim.run_id)
        if run is None:
            return False
        project_id = run.project_id
        dataset_version_id = run.dataset_version_id
        target_column = run.config.get("target_column")
        checkpoint = run.checkpoint or {}

        version = db.get(DatasetVersion, dataset_version_id)
        if version is None:
            with db.begin():
                run_up = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run_up and job:
                    terminal(db, run_up, job, "failed",
                             "Dataset version not found.")
            return True

        profile = db.get(Profile, version.id)
        if profile is None or profile.status != "ready" or profile.report is None:
            with db.begin():
                run_up = db.scalar(select(Run).where(
                    Run.id == claim.run_id).with_for_update())
                job = db.get(WorkItem, claim.run_id)
                if run_up and job:
                    terminal(db, run_up, job, "failed", "Profile not ready.")
            return True

        profile_report = ProfileReport.model_validate(profile.report)
        cleaning_report_dict = cast(
            dict[str, Any], checkpoint.get("clean_dataset", {}))
        baseline_report_dict = cast(
            dict[str, Any] | None, checkpoint.get("train_baseline"))

    # Generate dashboard spec
    spec = generate_dashboard_spec(
        dataset_version_id=str(dataset_version_id),
        profile_report=profile_report,
        cleaning_report=cleaning_report_dict,
        baseline_report=baseline_report_dict,
        target_column=str(target_column) if target_column else None,
    )

    spec_bytes = spec.model_dump_json().encode("utf-8")

    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled",
                     "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None

        # Store dashboard spec artifact
        spec_artifact = store_artifact(
            db,
            project_id,
            claim.run_id,
            "dashboard_spec",
            "dashboard_spec.json",
            spec_bytes,
        )

        # Upsert Dashboard model record
        dash = db.scalar(select(Dashboard).where(
            Dashboard.run_id == claim.run_id))
        if dash is None:
            dash = Dashboard(
                id=new_id(),
                run_id=claim.run_id,
                spec_artifact_id=spec_artifact.id,
                render_mode="fallback",
            )
            db.add(dash)
        else:
            dash.spec_artifact_id = spec_artifact.id
            dash.render_mode = "fallback"

        output = spec.model_dump()
        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"
        run.checkpoint = {**run.checkpoint, claim.stage: output}
        emit(db, run, "stage_completed", {"stage": claim.stage})
        job.token = None
        job.lease_expires_at = None

        if claim.stage == ANALYSIS_STAGES[-1]:
            run.result = output
            terminal(
                db,
                run,
                job,
                "succeeded",
                "Dataset analysis completed.",
            )
        else:
            job.state = "pending"

        return True


def execute_compile_dashboard(engine: Engine, claim: Claim) -> bool:
    with Session(engine) as db:
        run = db.get(Run, claim.run_id)
        if run is None:
            return False
        project_id = run.project_id
        checkpoint = run.checkpoint or {}
        spec_dict = checkpoint.get("plan_dashboard")
        if not spec_dict or not isinstance(spec_dict, dict):
            with db.begin():
                run_up = db.scalar(
                    select(Run).where(Run.id == claim.run_id).with_for_update()
                )
                job = db.get(WorkItem, claim.run_id)
                if run_up and job:
                    terminal(
                        db, run_up, job, "failed", "Dashboard spec missing in checkpoint."
                    )
            return True

        spec = DashboardSpec.model_validate(spec_dict)

    # Compile outside database transaction
    try:
        tsx_source = generate_react_dashboard(spec)
        comp_res = compile_dashboard_ui(tsx_source, claim.run_id)
    except ReactSecurityError as exc:
        comp_res = CompilationResult(
            status="error", error=f"Security violation: {exc}")
    except Exception as exc:
        comp_res = CompilationResult(
            status="error", error=f"Generation failed: {exc}")

    with Session(engine) as db, db.begin():
        run = db.scalar(select(Run).where(
            Run.id == claim.run_id).with_for_update())
        job = db.get(WorkItem, claim.run_id)
        if run and job and run.status == "cancelling" and job.token == claim.token:
            terminal(db, run, job, "cancelled",
                     "Worker acknowledged cancellation")
            return False
        if not valid_claim(run, job, claim):
            return False
        assert run is not None and job is not None

        attempt = db.get(StageAttempt, claim.attempt_id)
        assert attempt is not None
        attempt.status = "succeeded"

        dash = db.scalar(select(Dashboard).where(
            Dashboard.run_id == claim.run_id))
        assert dash is not None

        if comp_res.status == "ready" and comp_res.bundle:
            store_artifact(
                db,
                project_id,
                claim.run_id,
                "dashboard_script",
                "dashboard_component.tsx",
                tsx_source.encode("utf-8"),
            )
            bundle_artifact = store_artifact(
                db,
                project_id,
                claim.run_id,
                "dashboard_bundle",
                "dashboard_bundle.js",
                comp_res.bundle.encode("utf-8"),
            )
            dash.bundle_artifact_id = bundle_artifact.id
            dash.render_mode = "generated"

            output = {
                "status": "ready",
                "sha256": comp_res.sha256,
                "size_bytes": comp_res.size_bytes,
            }
            run.checkpoint = {**run.checkpoint, claim.stage: output}
            emit(
                db,
                run,
                "stage_completed",
                {"stage": claim.stage, "render_mode": "generated"},
            )
            job.token = None
            job.lease_expires_at = None
            run.result = spec.model_dump()
            terminal(
                db,
                run,
                job,
                "succeeded",
                "Dataset analysis and React dashboard generation completed.",
            )
        else:
            dash.render_mode = "fallback"
            warning_msg = (
                f"React compilation fallback: {comp_res.error or 'Unknown error'}"
            )
            output = {"status": "fallback", "warning": warning_msg}
            run.checkpoint = {**run.checkpoint, claim.stage: output}
            emit(db, run, "warning", {"message": warning_msg})
            emit(
                db,
                run,
                "stage_completed",
                {"stage": claim.stage, "render_mode": "fallback"},
            )
            job.token = None
            job.lease_expires_at = None
            run.result = spec.model_dump()
            terminal(
                db,
                run,
                job,
                "succeeded_with_warnings",
                f"Dataset analysis completed with fallback dashboard: {warning_msg}",
            )

        return True


def work_once(engine: Engine, transformer_image: str | None = None) -> bool:
    dispatched = dispatch_one(engine)
    claim = claim_one(engine)
    if claim is None:
        return dispatched
    if claim.mode == "synthetic":
        complete(engine, claim, fixture_result(claim.stage))
    elif claim.mode == "analysis":
        if claim.stage == "clean_dataset":
            execute_clean_dataset(engine, claim, transformer_image)
        elif claim.stage == "train_baseline":
            execute_train_baseline(engine, claim, transformer_image)
        elif claim.stage == "plan_dashboard":
            execute_plan_dashboard(engine, claim)
        elif claim.stage == "compile_dashboard":
            execute_compile_dashboard(engine, claim)
    return True
