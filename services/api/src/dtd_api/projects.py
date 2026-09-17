import json
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request
from pydantic import Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from dtd_api.auth import AUTH, DB, MUTATION, digest
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.models import AuditEvent, IdempotencyRecord, Project, now

router = APIRouter(prefix="/api/v1/projects", tags=["Projects"])


class ProjectWrite(Contract):
    name: str = Field(min_length=1, max_length=120)


class ProjectView(Contract):
    id: UUID
    name: str
    created_at: datetime


class ProjectPage(Contract):
    items: list[ProjectView]
    next_cursor: str | None


def view(project: Project) -> ProjectView:
    # SQLite strips timezone metadata; PostgreSQL preserves it. Both responses use UTC.
    from datetime import UTC

    return ProjectView(
        id=UUID(project.id), name=project.name, created_at=project.created_at.replace(tzinfo=UTC)
    )


def owned(db: DB, project_id: str, owner_id: str) -> Project:
    project = db.scalar(
        select(Project).where(
            Project.id == project_id, Project.owner_id == owner_id, Project.deleted_at.is_(None)
        )
    )
    if project is None:
        raise ApiError(404, "NOT_FOUND", "Project not found.")
    return project


KEY = Annotated[
    str,
    Header(alias="Idempotency-Key", min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$"),
]


@router.post("", response_model=ProjectView, status_code=201)
def create_project(
    body: ProjectWrite, request: Request, principal: MUTATION, db: DB, idempotency_key: KEY
) -> ProjectView:
    route = "POST /projects"
    scope = (principal.user.id, route, idempotency_key)
    request_hash = digest(json.dumps(body.model_dump(), sort_keys=True))

    def existing_result() -> ProjectView | None:
        record = db.get(IdempotencyRecord, scope)
        if record is None:
            return None
        if record.request_hash != request_hash:
            raise ApiError(
                409, "IDEMPOTENCY_CONFLICT", "This key was used with a different request."
            )
        return view(owned(db, record.resource_id, principal.user.id))

    db.execute(
        delete(IdempotencyRecord).where(
            IdempotencyRecord.owner_id == principal.user.id,
            IdempotencyRecord.route == route,
            IdempotencyRecord.key == idempotency_key,
            IdempotencyRecord.expires_at <= now(),
        )
    )
    existing = existing_result()
    if existing:
        return existing
    project = Project(owner_id=principal.user.id, name=body.name)
    db.add(project)
    db.flush()
    db.add(
        IdempotencyRecord(
            owner_id=principal.user.id,
            route=route,
            key=idempotency_key,
            request_hash=request_hash,
            resource_id=project.id,
            expires_at=now() + timedelta(hours=24),
        )
    )
    db.add(
        AuditEvent(
            actor_id=principal.user.id,
            action="project.created",
            resource_id=project.id,
            request_id=request.state.request_id,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # A concurrent identical submission can win the key. Roll back the entire losing project.
        db.rollback()
        existing = existing_result()
        if existing:
            return existing
        raise ApiError(409, "WRITE_CONFLICT", "Retry with the same idempotency key.") from None
    return view(project)


@router.get("", response_model=ProjectPage)
def list_projects(
    principal: AUTH,
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> ProjectPage:
    query = select(Project).where(
        Project.owner_id == principal.user.id, Project.deleted_at.is_(None)
    )
    if cursor is not None:
        owned(db, str(cursor), principal.user.id)
        query = query.where(Project.id > str(cursor))
    results = list(db.scalars(query.order_by(Project.id).limit(limit + 1)))
    return ProjectPage(
        items=[view(project) for project in results[:limit]],
        next_cursor=results[limit - 1].id if len(results) > limit else None,
    )


@router.get("/{project_id}", response_model=ProjectView)
def get_project(project_id: UUID, principal: AUTH, db: DB) -> ProjectView:
    return view(owned(db, str(project_id), principal.user.id))
