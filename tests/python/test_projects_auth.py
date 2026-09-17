from datetime import timedelta
from uuid import uuid4

import pytest
from dtd_api.auth import digest, issue_ticket
from dtd_api.main import Settings, create_app
from dtd_api.models import AuditEvent, LoginTicket, Project, User, WebSession, now
from fastapi.testclient import TestClient
from sqlalchemy import Engine, func, select, update
from sqlalchemy.orm import Session

ORIGIN = "https://127.0.0.1:8000"


def client_for(engine: Engine) -> TestClient:
    return TestClient(
        create_app(Settings(database_url=None, app_origin=ORIGIN), engine=engine), base_url=ORIGIN
    )


def login(client: TestClient, engine: Engine, subject: str) -> dict[str, str]:
    with Session(engine) as db:
        ticket = issue_ticket(db, subject)
    result = client.post(
        "/api/v1/auth/exchange", json={"token": ticket}, headers={"Origin": ORIGIN}
    )
    assert result.status_code == 200, result.text
    return {"Origin": ORIGIN, "X-CSRF-Token": result.json()["csrf_token"]}


def create(client: TestClient, headers: dict[str, str], name: str = "Sales", key: str = "one"):
    return client.post(
        "/api/v1/projects", json={"name": name}, headers={**headers, "Idempotency-Key": key}
    )


def test_two_users_cannot_read_or_list_each_others_projects(db_engine: Engine) -> None:
    with client_for(db_engine) as alice, client_for(db_engine) as bob:
        alice_headers = login(alice, db_engine, "alice")
        bob_headers = login(bob, db_engine, "bob")
        own = create(alice, alice_headers)
        assert own.status_code == 201
        project_id = own.json()["id"]
        assert alice.get(f"/api/v1/projects/{project_id}").status_code == 200
        assert bob.get(f"/api/v1/projects/{project_id}").status_code == 404
        assert bob.get("/api/v1/projects").json()["items"] == []
        assert bob.get(f"/api/v1/projects?cursor={project_id}").status_code == 404
        # The same key belongs to a different user, so it cannot replay Alice's result.
        assert create(bob, bob_headers).json()["id"] != project_id


def test_authentication_csrf_origin_and_no_identity_header_bypass(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        assert (
            client.get("/api/v1/projects", headers={"X-User-ID": str(uuid4())}).status_code == 401
        )
        headers = login(client, db_engine, "alice")
        assert create(client, {"Origin": ORIGIN}).status_code == 403
        assert create(client, {**headers, "Origin": "https://attacker.example"}).status_code == 403
        assert create(client, {"X-CSRF-Token": headers["X-CSRF-Token"]}).status_code == 403
        assert create(client, headers).status_code == 201


def test_ticket_is_single_use_cookie_is_secure_and_logout_revokes(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        with Session(db_engine) as db:
            ticket = issue_ticket(db, "alice")
        response = client.post(
            "/api/v1/auth/exchange", json={"token": ticket}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        for value in ("__Host-dtd_session=", "HttpOnly", "Secure", "SameSite=strict", "Path=/"):
            assert value in cookie
        assert "Domain=" not in cookie
        raw_session = client.cookies.get("__Host-dtd_session")
        assert (
            client.post(
                "/api/v1/auth/exchange", json={"token": ticket}, headers={"Origin": ORIGIN}
            ).status_code
            == 401
        )
        with Session(db_engine) as db:
            assert db.get(WebSession, raw_session) is None
            assert db.get(WebSession, digest(raw_session)) is not None
        headers = {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf_token"]}
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        assert client.get("/api/v1/auth/session").status_code == 401
        client.cookies.set("__Host-dtd_session", raw_session)
        assert client.get("/api/v1/auth/session").status_code == 401


def test_login_origin_expiry_rotation_and_disabled_users(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        with Session(db_engine) as db:
            ticket = issue_ticket(db, "alice")
        assert client.post("/api/v1/auth/exchange", json={"token": ticket}).status_code == 403
        first = client.post(
            "/api/v1/auth/exchange", json={"token": ticket}, headers={"Origin": ORIGIN}
        )
        assert first.status_code == 200
        old_session = client.cookies.get("__Host-dtd_session")
        login(client, db_engine, "alice")
        with Session(db_engine) as db:
            assert db.get(WebSession, digest(old_session)) is None
            db.execute(update(WebSession).values(expires_at=now() - timedelta(seconds=1)))
            db.commit()
        assert client.get("/api/v1/auth/session").status_code == 401
        login(client, db_engine, "alice")
        with Session(db_engine) as db:
            db.execute(update(User).values(active=False))
            db.commit()
        assert client.get("/api/v1/auth/session").status_code == 401


def test_expired_ticket_and_validation_never_echo_tokens(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        with Session(db_engine) as db:
            token = issue_ticket(db, "alice")
            db.execute(update(LoginTicket).values(expires_at=now() - timedelta(seconds=1)))
            db.commit()
        response = client.post(
            "/api/v1/auth/exchange", json={"token": token}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 401
        assert token not in response.text
        response = client.post("/api/v1/auth/exchange", json={"token": "private-invalid-token"})
        assert response.status_code == 422
        assert "private-invalid-token" not in response.text
        assert response.json()["error"]["request_id"] == response.headers["x-request-id"]


def test_idempotency_is_atomic_conflicts_and_validation_are_explicit(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        headers = login(client, db_engine, "alice")
        first = create(client, headers)
        assert first.status_code == 201
        assert create(client, headers).json() == first.json()
        assert create(client, headers, name="Changed").status_code == 409
        assert create(client, headers, name=" ").status_code == 422
        assert (
            client.post("/api/v1/projects", json={"name": "Valid"}, headers=headers).status_code
            == 422
        )
        with Session(db_engine) as db:
            assert db.scalar(select(func.count()).select_from(Project)) == 1
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(AuditEvent)
                    .where(AuditEvent.action == "project.created")
                )
                == 1
            )


def test_pagination_and_tombstones(db_engine: Engine) -> None:
    with client_for(db_engine) as client:
        headers = login(client, db_engine, "alice")
        ids = {create(client, headers, key=str(index)).json()["id"] for index in range(3)}
        page = client.get("/api/v1/projects?limit=2").json()
        assert len(page["items"]) == 2
        next_page = client.get(f"/api/v1/projects?limit=2&cursor={page['next_cursor']}").json()
        assert {value["id"] for value in page["items"] + next_page["items"]} == ids
        assert next_page["next_cursor"] is None
        deleted_id = next(iter(ids))
        with Session(db_engine) as db:
            db.execute(update(Project).where(Project.id == deleted_id).values(deleted_at=now()))
            db.commit()
        assert client.get(f"/api/v1/projects/{deleted_id}").status_code == 404
        assert len(client.get("/api/v1/projects").json()["items"]) == 2
        assert client.get("/api/v1/projects?limit=101").status_code == 422


def test_schema_readiness_missing_database_and_real_persistence(db_engine: Engine) -> None:
    with client_for(db_engine) as first:
        headers = login(first, db_engine, "alice")
        project_id = create(first, headers).json()["id"]
    with client_for(db_engine) as second:
        login(second, db_engine, "alice")
        assert second.get(f"/api/v1/projects/{project_id}").status_code == 200
        flags = second.get("/api/v1/capabilities").json()
        assert flags["persistence_enabled"] is True
        assert flags["execution_enabled"] is False


def test_unmigrated_database_rejected() -> None:
    from dtd_api.database import make_engine

    engine = make_engine("sqlite://")
    with pytest.raises(RuntimeError, match="schema is not current"):
        with client_for(engine):
            pass
    engine.dispose()
