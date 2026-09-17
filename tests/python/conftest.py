import os
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

import pytest
from dtd_api.database import make_engine, migrate
from sqlalchemy import Engine, create_engine, text


@pytest.fixture(params=["sqlite", "postgres"])
def db_engine(request: pytest.FixtureRequest) -> Iterator[Engine]:
    if request.param == "sqlite":
        engine = make_engine("sqlite://")
        migrate(engine)
        yield engine
        engine.dispose()
        return
    with postgres_database() as engine:
        yield engine


@pytest.fixture
def postgres_engine() -> Iterator[Engine]:
    with postgres_database() as engine:
        yield engine


@contextmanager
def postgres_database() -> Iterator[Engine]:
    url = os.environ.get("DTD_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "PostgreSQL parity suite: run npm run test:postgres or set DTD_TEST_DATABASE_URL"
        )
    schema = "dtd_test_" + uuid4().hex
    admin = create_engine(url, hide_parameters=True, connect_args={"connect_timeout": 5})
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(
        url,
        hide_parameters=True,
        connect_args={"options": f"-csearch_path={schema}", "connect_timeout": 5},
    )
    try:
        migrate(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            # Only this test's generated schema is removed, never a database or existing schema.
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()
