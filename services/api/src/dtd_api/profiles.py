"""Durable fixed profiling of a selected dataset version."""

import hashlib
import json
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
from dtd_api.inspection_contracts import InspectionReport, ProfileReport
from dtd_api.inspections import run_isolated
from dtd_api.models import (
    AuditEvent,
    Dataset,
    DatasetVersion,
    Inspection,
    Profile,
    Project,
    RawUpload,
    User,
    new_id,
    now,
)
from dtd_api.run_engine import utc
from dtd_api.uploads import metadata

router = APIRouter(prefix="/api/v1/dataset-versions", tags=["Isolated profiling"])


class ProfileView(Contract):
    dataset_version_id: str
    status: str
    attempts: int
    report: ProfileReport | None
    report_sha256: str | None
    error: str | None


def view(item: Profile) -> ProfileView:
    return ProfileView(
        dataset_version_id=item.dataset_version_id,
        status=item.status,
        attempts=item.attempts,
        report=ProfileReport.model_validate(item.report) if item.report else None,
        report_sha256=item.report_sha256,
        error=item.error,
    )


def current(db: Session, version_id: str, owner_id: str) -> tuple[DatasetVersion, Inspection]:
    version = db.get(DatasetVersion, version_id)
    if version is None:
        raise ApiError(404, "NOT_FOUND", "Dataset version not found.")
    metadata(db, version.dataset_id, owner_id)
    inspection = db.get(Inspection, version.dataset_id)
    if (
        inspection is None
        or inspection.selected_version_id != version_id
        or inspection.status != "ready"
    ):
        raise ApiError(404, "NOT_FOUND", "Current dataset version not found.")
    return version, inspection


@router.post("/{version_id}/profile", response_model=ProfileView, status_code=202)
def request_profile(version_id: UUID, request: Request, principal: MUTATION, db: DB) -> ProfileView:
    version, _ = current(db, str(version_id), principal.user.id)
    image = request.app.state.settings.inspection_image
    if image is None:
        raise ApiError(503, "PROFILE_UNAVAILABLE", "The isolated profiler is not configured.")
    db.scalar(select(User).where(User.id == principal.user.id).with_for_update())
    db.scalar(
        select(Inspection).where(Inspection.dataset_id == version.dataset_id).with_for_update()
    )
    current(db, str(version_id), principal.user.id)
    item = db.get(Profile, str(version_id))
    if item:
        return view(item)
    pending = db.scalar(
        select(Profile.dataset_version_id)
        .join(DatasetVersion, DatasetVersion.id == Profile.dataset_version_id)
        .join(Project, Project.id == DatasetVersion.project_id)
        .where(Project.owner_id == principal.user.id, Profile.status.in_(["queued", "running"]))
    )
    if pending:
        raise ApiError(429, "PROFILE_LIMIT", "Wait for your current profile to finish.")
    item = Profile(dataset_version_id=str(version_id), image=image)
    db.add(item)
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="profile.requested",
            resource_id=str(version_id),
            request_id=request.state.request_id,
        )
    )
    db.commit()
    return view(item)


@router.get("/{version_id}/profile", response_model=ProfileView)
def detail(version_id: UUID, principal: AUTH, db: DB) -> ProfileView:
    current(db, str(version_id), principal.user.id)
    item = db.get(Profile, str(version_id))
    if item is None:
        raise ApiError(404, "NOT_FOUND", "No profile requested yet.")
    return view(item)


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def profile_once(engine: Engine) -> bool:
    with Session(engine) as db, db.begin():
        item = db.scalar(
            select(Profile)
            .where(
                or_(
                    Profile.status == "queued",
                    and_(Profile.status == "running", Profile.lease_until < now()),
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
        version = db.get(DatasetVersion, item.dataset_version_id)
        assert version is not None
        dataset = db.get(Dataset, version.dataset_id)
        assert dataset is not None
        raw = db.get(RawUpload, dataset.id)
        inspection = db.get(Inspection, dataset.id)
        project = db.get(Project, dataset.project_id)
        owner = db.get(User, project.owner_id) if project else None
        if (
            not raw
            or not inspection
            or inspection.status != "ready"
            or inspection.selected_version_id != version.id
            or dataset.deleted_at
            or not project
            or project.deleted_at
            or not owner
            or not owner.active
        ):
            item.status = "cancelled"
            return True
        inspected = InspectionReport.model_validate(inspection.report)
        names = [table.name for table in inspected.tables]
        table_name = version.selection.get("table")
        if table_name not in names:
            item.status, item.error = "failed", "SELECTION_INVALID"
            return True
        index = names.index(table_name)
        selection = dict(version.selection)
        schema_hash = version.schema_hash
        data, sha, file_format = raw.content, dataset.raw_sha256, dataset.format
        delimiter = inspected.delimiter if file_format == "csv" else None
        image = item.image
        item.attempts += 1
        item.status, item.token = "running", new_id()
        item.lease_until = now() + timedelta(seconds=90)
        version_id, token = version.id, item.token
    report = None
    error = None
    try:
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError("Raw integrity mismatch")
        report = ProfileReport.model_validate_json(
            run_isolated(data, file_format, image, delimiter, index)
        )
        if (
            report.sha256 != sha
            or report.format != file_format
            or report.status != "ready"
            or report.tables[0].name != table_name
            or report.delimiter != inspected.delimiter
        ):
            raise ValueError("Profile lineage mismatch")
        schema = {**selection, "columns": report.tables[0].columns}
        if hashlib.sha256(canonical(schema)).hexdigest() != schema_hash:
            raise ValueError("Schema mismatch")
    except (
        OSError,
        subprocess.TimeoutExpired,
        RuntimeError,
        ValueError,
        ValidationError,
        IndexError,
    ):
        report = None
        error = "PROFILER_FAILED"
    with Session(engine) as db, db.begin():
        item = db.scalar(
            select(Profile).where(Profile.dataset_version_id == version_id).with_for_update()
        )
        assert item is not None
        if (
            item.status != "running"
            or item.token != token
            or item.lease_until is None
            or utc(item.lease_until) <= now()
        ):
            return True
        version = db.get(DatasetVersion, version_id)
        assert version is not None
        dataset = db.get(Dataset, version.dataset_id)
        assert dataset is not None
        inspection = db.get(Inspection, dataset.id)
        project = db.get(Project, dataset.project_id)
        owner = db.get(User, project.owner_id) if project else None
        if (
            dataset.deleted_at
            or not inspection
            or inspection.status != "ready"
            or inspection.selected_version_id != version_id
            or not project
            or project.deleted_at
            or not owner
            or not owner.active
        ):
            item.status = "cancelled"
        elif report:
            document = report.model_dump(mode="json")
            item.status = "ready"
            item.report = document
            item.report_sha256 = hashlib.sha256(canonical(document)).hexdigest()
        else:
            item.status, item.error = "failed", error
        item.token = None
        item.lease_until = None
    return True
