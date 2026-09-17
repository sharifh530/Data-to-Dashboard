from collections.abc import Iterator
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from fastapi import Request
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from dtd_api.settings import ROOT


def make_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)

        @event.listens_for(engine, "connect")
        def sqlite_constraints(connection: Any, _: Any) -> None:
            connection.execute("PRAGMA foreign_keys=ON")

        return engine
    return create_engine(
        url, pool_pre_ping=True, hide_parameters=True, connect_args={"connect_timeout": 5}
    )


def migration_config() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "services/api/migrations"))
    return config


def migrate(engine: Engine, revision: str = "head") -> None:
    with engine.begin() as connection:
        config = migration_config()
        config.attributes["connection"] = connection
        command.upgrade(config, revision)


def check_schema(engine: Engine) -> None:
    try:
        with engine.connect() as connection:
            current = set(MigrationContext.configure(connection).get_current_heads())
        expected = set(ScriptDirectory.from_config(migration_config()).get_heads())
        if not expected or current != expected:
            raise RuntimeError("Database schema is not current; run npm run db:migrate")
    except RuntimeError:
        raise
    except Exception:
        raise RuntimeError(
            "Cannot verify database schema; check local database configuration"
        ) from None


def database(request: Request) -> Iterator[Session]:
    from dtd_api.errors import ApiError

    engine = request.app.state.engine
    if engine is None:
        raise ApiError(503, "DATABASE_UNAVAILABLE", "Configure and migrate the database first.")
    with Session(engine) as session:
        yield session
