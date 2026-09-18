from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    LargeBinary,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class Identity:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(Identity, Base):
    __tablename__ = "users"
    auth_subject: Mapped[str] = mapped_column(String(200), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoginTicket(Base):
    __tablename__ = "login_tickets"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class WebSession(Base):
    __tablename__ = "web_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Project(Identity, Base):
    __tablename__ = "projects"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="nonempty_name"),)


class Dataset(Identity, Base):
    __tablename__ = "datasets"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    raw_key: Mapped[str] = mapped_column(String(500), unique=True)
    raw_sha256: Mapped[str] = mapped_column(String(64))
    format: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default="uploading")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("id", "project_id"),
        CheckConstraint("format IN ('csv','sqlite')", name="format"),
        CheckConstraint(
            "status IN ('uploading','validating','ready','rejected','deleting','deleted')",
            name="status",
        ),
    )


class RawUpload(Base):
    __tablename__ = "raw_uploads"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), primary_key=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    __table_args__ = (CheckConstraint("size_bytes > 0 AND size_bytes <= 10485760", name="size"),)


class Inspection(Base):
    __tablename__ = "inspections"
    dataset_id: Mapped[str] = mapped_column(ForeignKey("datasets.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")
    token: Mapped[str | None] = mapped_column(String(36))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    image: Mapped[str] = mapped_column(String(150))
    report: Mapped[dict[str, object] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','ready','rejected','failed','cancelled')", name="status"
        ),
    )


class DatasetVersion(Identity, Base):
    __tablename__ = "dataset_versions"
    dataset_id: Mapped[str] = mapped_column(String(36))
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    selection: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    schema_hash: Mapped[str | None] = mapped_column(String(64))
    __table_args__ = (
        UniqueConstraint("id", "project_id"),
        ForeignKeyConstraint(["dataset_id", "project_id"], ["datasets.id", "datasets.project_id"]),
    )


class Run(Identity, Base):
    __tablename__ = "runs"
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    dataset_version_id: Mapped[str] = mapped_column(String(36))
    config: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    budget: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    stage: Mapped[str | None] = mapped_column(String(40))
    generation: Mapped[int] = mapped_column(Integer, default=1)
    cancellation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    event_sequence: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    checkpoint: Mapped[dict[str, object]] = mapped_column(JSON, default=dict, server_default="{}")
    result: Mapped[dict[str, object] | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint("id", "project_id"),
        ForeignKeyConstraint(
            ["dataset_version_id", "project_id"],
            ["dataset_versions.id", "dataset_versions.project_id"],
        ),
        CheckConstraint(
            "status IN ('queued','running','awaiting_input','succeeded',"
            "'succeeded_with_warnings','failed','cancelling','cancelled')",
            name="status",
        ),
        CheckConstraint("generation > 0", name="positive_generation"),
    )


class StageAttempt(Identity, Base):
    __tablename__ = "stage_attempts"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40))
    attempt_number: Mapped[int] = mapped_column(Integer)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    runtime_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    __table_args__ = (
        UniqueConstraint("run_id", "stage", "attempt_number"),
        CheckConstraint("attempt_number > 0", name="positive_attempt"),
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed','cancelled')", name="status"
        ),
    )


class WorkItem(Base):
    __tablename__ = "work_items"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    token: Mapped[str | None] = mapped_column(String(36))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    __table_args__ = (CheckConstraint("state IN ('pending','leased','done')", name="state"),)


class Artifact(Identity, Base):
    __tablename__ = "artifacts"
    project_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(40))
    private_key: Mapped[str] = mapped_column(String(500), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[str] = mapped_column(String(20), default="1")
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_state: Mapped[str] = mapped_column(String(20), default="active")
    __table_args__ = (
        UniqueConstraint("id", "run_id"),
        ForeignKeyConstraint(["run_id", "project_id"], ["runs.id", "runs.project_id"]),
        CheckConstraint("size_bytes >= 0", name="nonnegative_size"),
        CheckConstraint("deletion_state IN ('active','deleting','deleted')", name="deletion_state"),
    )


class Dashboard(Identity, Base):
    __tablename__ = "dashboards"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), unique=True)
    spec_artifact_id: Mapped[str] = mapped_column(String(36))
    bundle_artifact_id: Mapped[str | None] = mapped_column(String(36))
    render_mode: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        ForeignKeyConstraint(["spec_artifact_id", "run_id"], ["artifacts.id", "artifacts.run_id"]),
        ForeignKeyConstraint(
            ["bundle_artifact_id", "run_id"], ["artifacts.id", "artifacts.run_id"]
        ),
        CheckConstraint("render_mode IN ('generated','fallback')", name="render_mode"),
    )


class RunEvent(Base):
    __tablename__ = "run_events"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (CheckConstraint("sequence > 0", name="positive_sequence"),)


class PendingQuestion(Identity, Base):
    __tablename__ = "pending_questions"
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Outbox(Identity, Base):
    __tablename__ = "outbox"
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    topic: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (CheckConstraint("retry_count >= 0", name="nonnegative_retries"),)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    route: Mapped[str] = mapped_column(String(120), primary_key=True)
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str] = mapped_column(String(36))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class AuditEvent(Identity, Base):
    __tablename__ = "audit_events"
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    resource_id: Mapped[str] = mapped_column(String(36))
    request_id: Mapped[str] = mapped_column(String(36))
