"""Bounded local raw storage. Uploaded bytes are never decoded or executed here."""

import asyncio
import hashlib
from datetime import timedelta
from typing import Annotated, Literal
from uuid import UUID

from anyio import to_thread
from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from starlette.requests import ClientDisconnect

from dtd_api.auth import AUTH, DB, MUTATION, authenticated, digest
from dtd_api.contracts import Contract
from dtd_api.errors import ApiError
from dtd_api.models import AuditEvent, Dataset, IdempotencyRecord, Project, RawUpload, User, now
from dtd_api.projects import KEY, owned

router = APIRouter(prefix="/api/v1", tags=["Raw upload storage"])
MAX_BYTES = 10 * 1024 * 1024
OWNER_BYTES = 50 * 1024 * 1024
UPLOAD_SECONDS = 30


class StoredDataset(Contract):
    id: UUID
    project_id: UUID
    format: str
    size_bytes: int
    sha256: str
    status: Literal["awaiting_isolated_inspection"] = "awaiting_isolated_inspection"
    analysis_ready: Literal[False] = False


class DatasetPage(Contract):
    items: list[StoredDataset]
    next_cursor: str | None


@router.get("/projects/{project_id}/datasets", response_model=DatasetPage)
def listing(
    project_id: UUID,
    principal: AUTH,
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: UUID | None = None,
) -> DatasetPage:
    owned(db, str(project_id), principal.user.id)
    query = (
        select(Dataset.id)
        .join(RawUpload)
        .where(Dataset.project_id == str(project_id), Dataset.deleted_at.is_(None))
    )
    if cursor:
        boundary = metadata(db, str(cursor), principal.user.id)
        if boundary.project_id != project_id:
            raise ApiError(404, "NOT_FOUND", "Dataset cursor not found.")
        query = query.where(Dataset.id > str(cursor))
    ids = list(db.scalars(query.order_by(Dataset.id).limit(limit + 1)))
    return DatasetPage(
        items=[metadata(db, value, principal.user.id) for value in ids[:limit]],
        next_cursor=ids[limit - 1] if len(ids) > limit else None,
    )


def metadata(db: Session, dataset_id: str, owner: str) -> StoredDataset:
    row = db.execute(
        select(Dataset, RawUpload.size_bytes)
        .join(RawUpload, RawUpload.dataset_id == Dataset.id)
        .join(Project, Project.id == Dataset.project_id)
        .where(
            Dataset.id == dataset_id,
            Project.owner_id == owner,
            Project.deleted_at.is_(None),
            Dataset.deleted_at.is_(None),
        )
    ).one_or_none()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Stored dataset not found.")
    dataset, size = row
    return StoredDataset(
        id=UUID(dataset.id),
        project_id=UUID(dataset.project_id),
        format=dataset.format,
        size_bytes=size,
        sha256=dataset.raw_sha256,
    )


def store(
    request: Request, project_id: str, file_format: str, key: str, data: bytes
) -> StoredDataset:
    with Session(request.app.state.engine) as db, db.begin():
        principal = authenticated(request, db)  # Recheck after receiving the body.
        db.execute(select(User).where(User.id == principal.user.id).with_for_update()).scalar_one()
        project = db.scalar(
            select(Project)
            .where(
                Project.id == project_id,
                Project.owner_id == principal.user.id,
                Project.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if project is None:
            raise ApiError(404, "NOT_FOUND", "Project not found.")
        route = f"POST /projects/{project_id}/raw-datasets"
        sha = hashlib.sha256(data).hexdigest()
        fingerprint = digest(file_format + ":" + sha)
        db.execute(
            delete(IdempotencyRecord).where(
                IdempotencyRecord.owner_id == principal.user.id,
                IdempotencyRecord.route == route,
                IdempotencyRecord.key == key,
                IdempotencyRecord.expires_at <= now(),
            )
        )
        previous = db.get(IdempotencyRecord, (principal.user.id, route, key))
        if previous:
            if previous.request_hash != fingerprint:
                raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Key belongs to different content.")
            return metadata(db, previous.resource_id, principal.user.id)
        used = (
            db.scalar(
                select(func.sum(RawUpload.size_bytes))
                .join(Dataset, Dataset.id == RawUpload.dataset_id)
                .join(Project, Project.id == Dataset.project_id)
                .where(Project.owner_id == principal.user.id)
            )
            or 0
        )
        if used + len(data) > OWNER_BYTES:
            raise ApiError(429, "STORAGE_LIMIT", "Local raw storage allowance is exhausted.")
        dataset = Dataset(
            project_id=project_id,
            format=file_format,
            status="validating",
            raw_key="postgres:" + request.state.request_id,
            raw_sha256=sha,
        )
        db.add(dataset)
        db.flush()
        db.add(RawUpload(dataset_id=dataset.id, size_bytes=len(data), content=data))
        db.add(
            IdempotencyRecord(
                owner_id=principal.user.id,
                route=route,
                key=key,
                request_hash=fingerprint,
                resource_id=dataset.id,
                expires_at=now() + timedelta(hours=24),
            )
        )
        db.add(
            AuditEvent(
                actor_id=principal.user.id,
                action="dataset.stored",
                resource_id=dataset.id,
                request_id=request.state.request_id,
            )
        )
        db.flush()
        return metadata(db, dataset.id, principal.user.id)


@router.post(
    "/projects/{project_id}/raw-datasets",
    response_model=StoredDataset,
    status_code=201,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/octet-stream": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def upload(
    project_id: UUID,
    file_format: Literal["csv", "sqlite"],
    request: Request,
    principal: MUTATION,
    db: DB,
    idempotency_key: KEY,
) -> StoredDataset:
    owned(db, str(project_id), principal.user.id)
    db.close()
    slots: asyncio.Semaphore = request.app.state.upload_slots
    if slots.locked():
        raise ApiError(429, "UPLOAD_BUSY", "Local upload slots are busy. Retry later.")
    async with slots:
        data = await receive_bytes(request)
        return await to_thread.run_sync(
            store, request, str(project_id), file_format, idempotency_key, data
        )


async def receive_bytes(request: Request) -> bytes:
    if request.headers.get("content-type") != "application/octet-stream":
        raise ApiError(415, "CONTENT_TYPE", "Send raw bytes as application/octet-stream.")
    declared = request.headers.get("content-length", "")
    if not declared.isascii() or not declared.isdigit() or len(declared) > 10:
        raise ApiError(411, "LENGTH_REQUIRED", "A valid Content-Length is required.")
    expected = int(declared)
    if expected < 1 or expected > MAX_BYTES:
        raise ApiError(413, "UPLOAD_SIZE", "Upload must contain 1 byte to 10 MiB.")
    data = bytearray()
    try:
        async with asyncio.timeout(UPLOAD_SECONDS):
            async for chunk in request.stream():
                if len(data) + len(chunk) > min(expected, MAX_BYTES):
                    raise ApiError(413, "UPLOAD_SIZE", "Upload exceeded its byte limit.")
                data.extend(chunk)
    except TimeoutError as error:
        raise ApiError(408, "UPLOAD_TIMEOUT", "Upload timed out.") from error
    except ClientDisconnect as error:
        raise ApiError(400, "UPLOAD_INTERRUPTED", "Upload was interrupted.") from error
    if len(data) != expected:
        raise ApiError(400, "LENGTH_MISMATCH", "Upload length did not match Content-Length.")
    return bytes(data)


@router.get("/datasets/{dataset_id}", response_model=StoredDataset)
def detail(dataset_id: UUID, principal: AUTH, db: DB) -> StoredDataset:
    return metadata(db, str(dataset_id), principal.user.id)


@router.get("/datasets/{dataset_id}/raw", response_class=Response)
def download(dataset_id: UUID, principal: AUTH, db: DB) -> Response:
    info = metadata(db, str(dataset_id), principal.user.id)
    content = db.scalar(select(RawUpload.content).where(RawUpload.dataset_id == str(dataset_id)))
    if content is None or hashlib.sha256(content).hexdigest() != info.sha256:
        raise ApiError(503, "INTEGRITY_FAILURE", "Raw dataset integrity check failed.")
    return Response(
        content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{dataset_id}.{info.format}"',
            "X-Content-SHA256": info.sha256,
        },
    )
