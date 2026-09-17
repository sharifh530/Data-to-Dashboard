import asyncio
import hashlib
from concurrent.futures import ThreadPoolExecutor

import pytest
from dtd_api.errors import ApiError
from dtd_api.models import Dataset, Project, RawUpload, WebSession, now
from dtd_api.uploads import receive_bytes
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session
from starlette.requests import Request
from test_projects_auth import client_for, create, login


def send(client, headers, project, data=b"a,b\n1,2\n", key="upload", **extra):
    return client.post(
        f"/api/v1/projects/{project}/raw-datasets?file_format=csv",
        content=data,
        headers={
            **headers,
            "Idempotency-Key": key,
            "Content-Type": "application/octet-stream",
            **extra,
        },
    )


def test_raw_roundtrip_idempotency_and_ownership(db_engine):
    with client_for(db_engine) as client, client_for(db_engine) as bob:
        headers = login(client, db_engine, "alice")
        project = create(client, headers).json()["id"]
        data = b"\xff<script>not parsed</script>\x00"
        response = send(client, headers, project, data)
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["analysis_ready"] is False
        assert result["sha256"] == hashlib.sha256(data).hexdigest()
        assert send(client, headers, project, data).json() == result
        assert send(client, headers, project, b"different").status_code == 409
        url = f"/api/v1/datasets/{result['id']}"
        raw = client.get(url + "/raw")
        assert raw.content == data
        assert raw.headers["content-disposition"].startswith("attachment;")
        assert raw.headers["x-content-type-options"] == "nosniff"
        assert client.get(url).json() == result
        bob_headers = login(bob, db_engine, "bob")
        assert bob.get(url).status_code == 404
        assert bob.get(url + "/raw").status_code == 404
        assert send(bob, bob_headers, project).status_code == 404
        assert send(client, {}, project).status_code == 403
        with Session(db_engine) as db, db.begin():
            assert db.scalar(select(func.count()).select_from(RawUpload)) == 1
            assert db.scalar(select(Dataset.status)) == "validating"
            db.execute(update(Project).values(deleted_at=now()))
        assert client.get(url).status_code == 404


def test_upload_limits_and_integrity(db_engine, monkeypatch):
    with client_for(db_engine) as client:
        headers = login(client, db_engine, "alice")
        project = create(client, headers).json()["id"]
        for extra, expected in [
            ({"Content-Length": "10485761"}, 413),
            ({"Content-Length": "0"}, 413),
            ({"Content-Length": "bad"}, 411),
            ({"Content-Length": "1"}, 413),
            ({"Content-Length": "20"}, 400),
            ({"Content-Type": "text/csv"}, 415),
        ]:
            assert send(client, headers, project, **extra).status_code == expected
        monkeypatch.setattr("dtd_api.uploads.OWNER_BYTES", 8)
        result = send(client, headers, project).json()
        assert send(client, headers, project, key="second").status_code == 429
        with Session(db_engine) as db, db.begin():
            assert db.scalar(select(func.count()).select_from(RawUpload)) == 1
            db.execute(update(RawUpload).values(content=b"corrupt"))
        response = client.get(f"/api/v1/datasets/{result['id']}/raw")
        assert response.status_code == 503
        assert "corrupt" not in response.text


def test_revoked_session_during_upload(db_engine):
    with client_for(db_engine) as client:
        headers = login(client, db_engine, "alice")
        project = create(client, headers).json()["id"]

        def chunks():
            with Session(db_engine) as db, db.begin():
                db.execute(delete(WebSession))
            yield b"test"

        assert (
            send(client, headers, project, chunks(), **{"Content-Length": "4"}).status_code == 401
        )
        with Session(db_engine) as db:
            assert db.scalar(select(func.count()).select_from(RawUpload)) == 0


def test_receive_timeout_and_disconnect(monkeypatch):
    monkeypatch.setattr("dtd_api.uploads.UPLOAD_SECONDS", 0.01)

    async def exercise():
        for disconnect in (False, True):

            async def receive(disconnect=disconnect):
                if disconnect:
                    return {"type": "http.disconnect"}
                await asyncio.sleep(1)
                return {"type": "http.request", "body": b"a", "more_body": False}

            request = Request(
                {
                    "type": "http",
                    "headers": [
                        (b"content-type", b"application/octet-stream"),
                        (b"content-length", b"1"),
                    ],
                },
                receive,
            )
            with pytest.raises(ApiError) as error:
                await receive_bytes(request)
            assert error.value.status == (400 if disconnect else 408)

    asyncio.run(exercise())


def test_postgres_concurrent_storage_quota(postgres_engine, monkeypatch):
    monkeypatch.setattr("dtd_api.uploads.OWNER_BYTES", 8)
    with client_for(postgres_engine) as client:
        headers = login(client, postgres_engine, "alice")
        project = create(client, headers).json()["id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(
                pool.map(lambda key: send(client, headers, project, key=key), ["one", "two"])
            )
        assert sorted(response.status_code for response in responses) == [201, 429]
        with Session(postgres_engine) as db:
            assert db.scalar(select(func.sum(RawUpload.size_bytes))) == 8
