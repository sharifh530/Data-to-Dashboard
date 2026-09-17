from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from dtd_api.auth import issue_ticket
from dtd_api.main import Settings, create_app
from dtd_api.models import Project, WebSession
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

ORIGIN = "https://127.0.0.1:8000"


def test_parallel_ticket_exchange_has_exactly_one_winner(postgres_engine: Engine) -> None:
    with Session(postgres_engine) as db:
        ticket = issue_ticket(db, "alice")
    barrier = Barrier(2)

    def exchange() -> int:
        app = create_app(Settings(database_url=None, app_origin=ORIGIN), engine=postgres_engine)
        with TestClient(app, base_url=ORIGIN) as client:
            barrier.wait(timeout=10)
            return client.post(
                "/api/v1/auth/exchange", json={"token": ticket}, headers={"Origin": ORIGIN}
            ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(exchange) for _ in range(2)]
        assert sorted(future.result(timeout=15) for future in futures) == [200, 401]
    with Session(postgres_engine) as db:
        assert db.scalar(select(func.count()).select_from(WebSession)) == 1


def test_parallel_idempotent_creates_publish_one_project(postgres_engine: Engine) -> None:
    app = create_app(Settings(database_url=None, app_origin=ORIGIN), engine=postgres_engine)
    with TestClient(app, base_url=ORIGIN) as first, TestClient(app, base_url=ORIGIN) as second:
        headers = []
        for client in (first, second):
            with Session(postgres_engine) as db:
                token = issue_ticket(db, "alice")
            result = client.post(
                "/api/v1/auth/exchange", json={"token": token}, headers={"Origin": ORIGIN}
            )
            assert result.status_code == 200
            headers.append(
                {
                    "Origin": ORIGIN,
                    "X-CSRF-Token": result.json()["csrf_token"],
                    "Idempotency-Key": "same-key",
                }
            )
        barrier = Barrier(2)

        def submit(client, header):
            barrier.wait(timeout=10)
            result = client.post("/api/v1/projects", json={"name": "Sales"}, headers=header)
            assert result.status_code == 201, result.text
            return result.json()["id"]

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(submit, first, headers[0]),
                executor.submit(submit, second, headers[1]),
            ]
            assert len({future.result(timeout=15) for future in futures}) == 1
    with Session(postgres_engine) as db:
        assert db.scalar(select(func.count()).select_from(Project)) == 1
