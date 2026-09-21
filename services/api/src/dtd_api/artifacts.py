"""Artifact management and secure owner-scoped retrieval."""

import hashlib
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from dtd_api.auth import AUTH, DB
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.models import Artifact, Project, Run, new_id, now
from dtd_api.projects import owned
from dtd_api.settings import ROOT

router = APIRouter(prefix="/api/v1/projects", tags=["Run artifacts"])
ARTIFACTS_DIR = ROOT / ".local" / "artifacts"


class ArtifactView(Contract):
    id: UUID
    project_id: UUID
    run_id: UUID
    kind: str
    sha256: str
    size_bytes: int
    schema_version: str


def view(artifact: Artifact) -> ArtifactView:
    return ArtifactView(
        id=UUID(artifact.id),
        project_id=UUID(artifact.project_id),
        run_id=UUID(artifact.run_id),
        kind=artifact.kind,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        schema_version=artifact.schema_version,
    )


def store_artifact(
    db: Session,
    project_id: str,
    run_id: str,
    kind: str,
    filename: str,
    content: bytes,
    schema_version: str = "1",
) -> Artifact:
    """Store an immutable derived run artifact with integrity verification."""
    artifact_id = new_id()
    private_key = f"projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}/{filename}"
    file_path = ARTIFACTS_DIR / private_key
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)

    content_sha = hashlib.sha256(content).hexdigest()
    artifact = Artifact(
        id=artifact_id,
        project_id=project_id,
        run_id=run_id,
        kind=kind,
        private_key=private_key,
        sha256=content_sha,
        size_bytes=len(content),
        schema_version=schema_version,
        validated_at=now(),
        deletion_state="active",
    )
    db.add(artifact)
    return artifact


def _owned_run(db: Session, project_id: str, run_id: str, owner_id: str) -> Run:
    run = db.scalar(
        select(Run)
        .join(Project, Project.id == Run.project_id)
        .where(
            Run.id == run_id,
            Run.project_id == project_id,
            Project.owner_id == owner_id,
            Project.deleted_at.is_(None),
        )
    )
    if run is None:
        raise ApiError(404, "NOT_FOUND", "Run not found.")
    return run


def owned_artifact(
    db: Session, project_id: str, run_id: str, artifact_id: str, owner_id: str
) -> Artifact:
    """Ensure run and artifact are actively owned and not deleted."""
    owned(db, project_id, owner_id)
    _owned_run(db, project_id, run_id, owner_id)
    artifact = db.scalar(
        select(Artifact).where(
            Artifact.id == artifact_id,
            Artifact.run_id == run_id,
            Artifact.project_id == project_id,
            Artifact.deletion_state == "active",
        )
    )
    if artifact is None:
        raise ApiError(404, "NOT_FOUND", "Artifact not found.")
    return artifact


@router.get("/{project_id}/runs/{run_id}/artifacts", response_model=list[ArtifactView])
def list_artifacts(
    project_id: UUID,
    run_id: UUID,
    principal: AUTH,
    db: DB,
) -> list[ArtifactView]:
    owned(db, str(project_id), principal.user.id)
    _owned_run(db, str(project_id), str(run_id), principal.user.id)
    items = db.scalars(
        select(Artifact)
        .where(
            Artifact.project_id == str(project_id),
            Artifact.run_id == str(run_id),
            Artifact.deletion_state == "active",
        )
        .order_by(Artifact.created_at)
    ).all()
    return [view(a) for a in items]


@router.get("/{project_id}/runs/{run_id}/artifacts/{artifact_id}/download")
def download_artifact(
    project_id: UUID,
    run_id: UUID,
    artifact_id: UUID,
    principal: AUTH,
    db: DB,
) -> Response:
    artifact = owned_artifact(db, str(project_id), str(run_id), str(artifact_id), principal.user.id)
    file_path = ARTIFACTS_DIR / artifact.private_key
    if not file_path.exists():
        raise ApiError(404, "NOT_FOUND", "Artifact content missing.")
    data = file_path.read_bytes()
    if hashlib.sha256(data).hexdigest() != artifact.sha256:
        raise ApiError(500, "CORRUPT_ARTIFACT", "Artifact failed checksum integrity check.")

    media_type = "text/csv" if artifact.kind == "cleaned_data" else "application/octet-stream"
    if artifact.kind in {"cleaning_report", "baseline_report"}:
        media_type = "application/json"
    elif artifact.kind in {"generated_script", "baseline_script"}:
        media_type = "text/x-python"

    filename = Path(artifact.private_key).name
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
