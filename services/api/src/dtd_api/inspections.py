import hashlib
import json
import subprocess
from datetime import timedelta
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import Field, ValidationError
from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session

from dtd_api.auth import AUTH, DB, MUTATION
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.inspection_contracts import InspectionReport
from dtd_api.models import (
    AuditEvent,
    Dataset,
    DatasetVersion,
    Inspection,
    Project,
    RawUpload,
    User,
    new_id,
    now,
)
from dtd_api.uploads import metadata

router = APIRouter(prefix="/api/v1/datasets", tags=["Isolated inspection"])


class InspectionView(Contract):
    dataset_id: str
    status: str
    attempts: int
    report: InspectionReport | None
    error: str | None
    delimiter_override: str | None
    selected_table: str | None
    dataset_version_id: str | None
    revisions: int


class InspectionOptions(Contract):
    delimiter: Literal[",", ";", "\t", "|"] | None = None


class TableChoice(Contract):
    table: str = Field(min_length=1, max_length=128)


def view(item: Inspection) -> InspectionView:
    return InspectionView(
        dataset_id=item.dataset_id,
        status=item.status,
        attempts=item.attempts,
        report=InspectionReport.model_validate(item.report) if item.report else None,
        error=item.error,
        delimiter_override=item.delimiter_override,
        selected_table=item.selected_table,
        dataset_version_id=item.selected_version_id,
        revisions=item.revisions,
    )


@router.post("/{dataset_id}/inspection", response_model=InspectionView, status_code=202)
def request_inspection(
    dataset_id: UUID,
    request: Request,
    principal: MUTATION,
    db: DB,
    options: InspectionOptions | None = None,
) -> InspectionView:
    metadata(db, str(dataset_id), principal.user.id)
    image = request.app.state.settings.inspection_image
    if image is None:
        raise ApiError(503, "INSPECTION_UNAVAILABLE", "The isolated inspector is not configured.")
    db.scalar(select(User).where(User.id == principal.user.id).with_for_update())
    dataset = db.scalar(select(Dataset).where(Dataset.id == str(dataset_id)).with_for_update())
    if dataset is None:
        raise ApiError(404, "NOT_FOUND", "Stored dataset not found.")
    delimiter = options.delimiter if options else None
    if dataset.format != "csv" and delimiter:
        raise ApiError(422, "INVALID_DELIMITER", "Choose a supported CSV delimiter.")
    item = db.get(Inspection, str(dataset_id))
    if item and item.delimiter_override == delimiter:
        return view(item)
    if item and item.status in {"queued", "running"}:
        raise ApiError(409, "INSPECTION_PENDING", "Wait for inspection to finish.")
    if item and item.revisions >= 3:
        raise ApiError(409, "INSPECTION_REVISION_LIMIT", "Upload again to try more options.")
    pending = db.scalar(
        select(Inspection.dataset_id)
        .join(Dataset)
        .join(Project)
        .where(Project.owner_id == principal.user.id, Inspection.status.in_(["queued", "running"]))
    )
    if pending:
        raise ApiError(429, "INSPECTION_LIMIT", "Wait for your current inspection to finish.")
    if item:
        item.status, item.token, item.lease_until = "queued", None, None
        item.attempts, item.image, item.report, item.error = 0, image, None, None
        item.delimiter_override = delimiter
        item.selected_table = None
        item.selected_version_id = None
        item.revisions += 1
    else:
        item = Inspection(dataset_id=str(dataset_id), image=image, delimiter_override=delimiter)
        db.add(item)
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="inspection.requested",
            resource_id=str(dataset_id),
            request_id=request.state.request_id,
        )
    )
    db.commit()
    return view(item)


@router.post("/{dataset_id}/inspection/selection", response_model=InspectionView)
def select_table(
    dataset_id: UUID, choice: TableChoice, principal: MUTATION, db: DB
) -> InspectionView:
    stored = metadata(db, str(dataset_id), principal.user.id)
    item = db.scalar(
        select(Inspection).where(Inspection.dataset_id == str(dataset_id)).with_for_update()
    )
    if item is None or item.status != "ready" or item.report is None:
        raise ApiError(409, "INSPECTION_NOT_READY", "Inspect the dataset first.")
    report = InspectionReport.model_validate(item.report)
    table = next((table for table in report.tables if table.name == choice.table), None)
    if table is None:
        raise ApiError(422, "UNKNOWN_TABLE", "Choose a table from the inspection result.")
    if item.selected_table == choice.table and item.selected_version_id:
        return view(item)
    selection = {
        "schema_version": "1",
        "table": choice.table,
        "delimiter": report.delimiter,
        "raw_sha256": report.sha256,
    }
    schema = {**selection, "columns": table.columns}
    schema_hash = hashlib.sha256(
        json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    version = DatasetVersion(
        dataset_id=str(dataset_id),
        project_id=str(stored.project_id),
        selection=selection,
        schema_hash=schema_hash,
    )
    db.add(version)
    db.flush()
    item.selected_table = choice.table
    item.selected_version_id = version.id
    db.commit()
    return view(item)


@router.get("/{dataset_id}/inspection", response_model=InspectionView)
def detail(dataset_id: UUID, principal: AUTH, db: DB) -> InspectionView:
    metadata(db, str(dataset_id), principal.user.id)
    item = db.get(Inspection, str(dataset_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "No inspection requested yet.")
    return view(item)


@router.post("/{dataset_id}/inspection/cancel", response_model=InspectionView)
def cancel(dataset_id: UUID, principal: MUTATION, db: DB) -> InspectionView:
    metadata(db, str(dataset_id), principal.user.id)
    item = db.scalar(
        select(Inspection).where(Inspection.dataset_id == str(dataset_id)).with_for_update()
    )
    if item is None:
        raise ApiError(404, "NOT_FOUND", "No inspection requested yet.")
    if item.status == "running":
        raise ApiError(
            409, "INSPECTION_RUNNING", "Inspection is bounded to 30 seconds; wait for it to finish."
        )
    if item.status == "queued":
        item.status = "cancelled"
        item.token = None
    db.commit()
    return view(item)


def run_isolated(data: bytes, file_format: str, image: str, delimiter: str | None = None) -> bytes:
    command = [
        "wsl",
        "-d",
        "dtd-sandbox",
        "-u",
        "root",
        "--cd",
        "/opt/dtd",
        "--",
        "env",
        "PYTHONPATH=/opt/dtd/services/execution-broker/src",
        "python3",
        "scripts/sandbox-inspect.py",
        "--image",
        image,
        "--format",
        file_format,
    ]
    if delimiter:
        names = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}
        command.extend(["--delimiter", names[delimiter]])
    # Linux broker caps output and removes the container before returning this bounded report.
    result = subprocess.run(command, input=data, capture_output=True, timeout=60, check=False)
    if result.returncode != 0 or len(result.stdout) > 524288:
        raise RuntimeError("Isolated inspector unavailable or failed")
    return result.stdout


def inspection_once(engine: Engine) -> bool:
    with Session(engine) as db, db.begin():
        item = db.scalar(
            select(Inspection)
            .where(
                or_(
                    Inspection.status == "queued",
                    and_(Inspection.status == "running", Inspection.lease_until < now()),
                )
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if item is None:
            return False
        if item.attempts >= 3:
            item.status, item.error = "failed", "RETRY_LIMIT"
            return True
        dataset = db.get(Dataset, item.dataset_id)
        assert dataset is not None
        raw = db.get(RawUpload, item.dataset_id)
        project = db.get(Project, dataset.project_id)
        owner = db.get(User, project.owner_id) if project else None
        if (
            not raw
            or dataset.deleted_at
            or not project
            or project.deleted_at
            or not owner
            or not owner.active
        ):
            item.status = "cancelled"
            return True
        data, sha, file_format = raw.content, dataset.raw_sha256, dataset.format
        item.attempts += 1
        item.status, item.token = "running", new_id()
        item.lease_until = now() + timedelta(seconds=90)
        dataset_id, token, image, delimiter = (
            item.dataset_id,
            item.token,
            item.image,
            item.delimiter_override,
        )
    report = None
    error = None
    try:
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("Input integrity mismatch")
        report = InspectionReport.model_validate_json(
            run_isolated(data, file_format, image, delimiter)
        )
        if report.sha256 != sha or report.format != file_format:
            raise ValueError("Result lineage mismatch")
        if delimiter and report.status == "ready" and report.delimiter != delimiter:
            raise ValueError("Delimiter mismatch")
    except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError, ValidationError):
        report = None
        error = "INSPECTOR_FAILED"
    with Session(engine) as db, db.begin():
        item = db.scalar(
            select(Inspection).where(Inspection.dataset_id == dataset_id).with_for_update()
        )
        assert item is not None
        from dtd_api.run_engine import utc

        if (
            item.status != "running"
            or item.token != token
            or item.lease_until is None
            or utc(item.lease_until) <= now()
        ):
            return True
        dataset = db.get(Dataset, dataset_id)
        assert dataset is not None
        project = db.get(Project, dataset.project_id)
        owner = db.get(User, project.owner_id) if project else None
        if dataset.deleted_at or not project or project.deleted_at or not owner or not owner.active:
            item.status = "cancelled"
        elif report:
            item.status = report.status
            item.report = report.model_dump(mode="json")
            item.error = report.error
        else:
            item.status, item.error = "failed", error
        item.token = None
        item.lease_until = None
    return True
