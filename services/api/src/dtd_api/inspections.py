import hashlib
import subprocess
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import ValidationError
from sqlalchemy import Engine, and_, or_, select
from sqlalchemy.orm import Session

from dtd_api.auth import AUTH, DB, MUTATION
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.inspection_contracts import InspectionReport
from dtd_api.models import AuditEvent, Dataset, Inspection, Project, RawUpload, User, new_id, now
from dtd_api.uploads import metadata

router = APIRouter(prefix="/api/v1/datasets", tags=["Isolated inspection"])


class InspectionView(Contract):
    dataset_id: str
    status: str
    attempts: int
    report: InspectionReport | None
    error: str | None


def view(item: Inspection) -> InspectionView:
    return InspectionView(
        dataset_id=item.dataset_id,
        status=item.status,
        attempts=item.attempts,
        report=InspectionReport.model_validate(item.report) if item.report else None,
        error=item.error,
    )


@router.post("/{dataset_id}/inspection", response_model=InspectionView, status_code=202)
def request_inspection(
    dataset_id: UUID, request: Request, principal: MUTATION, db: DB
) -> InspectionView:
    metadata(db, str(dataset_id), principal.user.id)
    image = request.app.state.settings.inspection_image
    if image is None:
        raise ApiError(503, "INSPECTION_UNAVAILABLE", "The isolated inspector is not configured.")
    db.scalar(select(User).where(User.id == principal.user.id).with_for_update())
    db.scalar(select(Dataset).where(Dataset.id == str(dataset_id)).with_for_update())
    item = db.get(Inspection, str(dataset_id))
    if item:
        return view(item)
    pending = db.scalar(
        select(Inspection.dataset_id)
        .join(Dataset)
        .join(Project)
        .where(Project.owner_id == principal.user.id, Inspection.status.in_(["queued", "running"]))
    )
    if pending:
        raise ApiError(429, "INSPECTION_LIMIT", "Wait for your current inspection to finish.")
    item = Inspection(dataset_id=str(dataset_id), image=image)
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


def run_isolated(data: bytes, file_format: str, image: str) -> bytes:
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
        dataset_id, token, image = item.dataset_id, item.token, item.image
    report = None
    error = None
    try:
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("Input integrity mismatch")
        report = InspectionReport.model_validate_json(run_isolated(data, file_format, image))
        if report.sha256 != sha or report.format != file_format:
            raise ValueError("Result lineage mismatch")
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
