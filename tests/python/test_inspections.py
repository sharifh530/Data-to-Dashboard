import hashlib
from datetime import timedelta

import pytest
from dtd_api.inspection_contracts import InspectionReport
from dtd_api.inspections import inspection_once
from dtd_api.models import Dataset, DatasetVersion, Inspection, now
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session
from test_projects_auth import client_for, create, login
from test_uploads import send

IMAGE = "sha256:" + "a" * 64


def fixture_report(data, file_format, _image, delimiter=None):
    return (
        InspectionReport(
            schema_version="1",
            sha256=hashlib.sha256(data).hexdigest(),
            format=file_format,
            status="ready",
            warnings=[],
            error=None,
            delimiter=delimiter or ",",
            tables=[
                {
                    "name": "CSV",
                    "columns": ["a", "b"],
                    "row_count": 1,
                    "missing": [0, 0],
                    "preview": [["1", "2"]],
                }
            ],
        )
        .model_dump_json()
        .encode()
    )


def setup(client, engine):
    client.app.state.settings.inspection_image = IMAGE
    headers = login(client, engine, "alice")
    project = create(client, headers).json()["id"]
    dataset = send(client, headers, project).json()["id"]
    return headers, project, dataset


def test_inspection_ownership_replay_and_result(db_engine, monkeypatch):
    monkeypatch.setattr("dtd_api.inspections.run_isolated", fixture_report)
    with client_for(db_engine) as client, client_for(db_engine) as bob:
        headers, project, dataset = setup(client, db_engine)
        url = f"/api/v1/datasets/{dataset}/inspection"
        assert client.post(url, headers=headers).status_code == 202
        assert client.post(url, headers=headers).json()["attempts"] == 0
        bob_headers = login(bob, db_engine, "bob")
        assert bob.get(url).status_code == 404
        assert bob.post(url, headers=bob_headers).status_code == 404
        assert client.post(url).status_code == 403
        assert inspection_once(db_engine)
        result = client.get(url).json()
        assert result["status"] == "ready" and result["report"]["tables"][0]["preview"] == [
            ["1", "2"]
        ]
        assert (
            client.get(f"/api/v1/projects/{project}/datasets").json()["items"][0][
                "inspection_status"
            ]
            == "ready"
        )
        assert not inspection_once(db_engine)


@pytest.mark.parametrize("failure", ["hash", "shape", "runtime", "deleted", "stale", "expired"])
def test_inspection_rejects_invalid_and_stale_publication(db_engine, monkeypatch, failure):
    with client_for(db_engine) as client:
        headers, _, dataset = setup(client, db_engine)
        url = f"/api/v1/datasets/{dataset}/inspection"
        client.post(url, headers=headers)

        def inspect(data, fmt, image, delimiter=None):
            if failure == "runtime":
                raise RuntimeError("raw private error")
            report = InspectionReport.model_validate_json(
                fixture_report(data, fmt, image, delimiter)
            )
            if failure == "hash":
                report.sha256 = "0" * 64
            if failure == "shape":
                report.tables[0].missing = []
            with Session(db_engine) as db, db.begin():
                if failure == "deleted":
                    db.execute(update(Dataset).values(deleted_at=now()))
                if failure == "stale":
                    db.execute(update(Inspection).values(token="another-token"))
                if failure == "expired":
                    db.execute(update(Inspection).values(lease_until=now() - timedelta(seconds=1)))
            return report.model_dump_json().encode()

        monkeypatch.setattr("dtd_api.inspections.run_isolated", inspect)
        inspection_once(db_engine)
        with Session(db_engine) as db:
            item = db.get(Inspection, dataset)
            assert item.report is None
            assert item.status != "ready"


def test_queued_cancel_retry_budget_and_disabled_config(db_engine):
    with client_for(db_engine) as client:
        headers, _, dataset = setup(client, db_engine)
        url = f"/api/v1/datasets/{dataset}/inspection"
        client.app.state.settings.inspection_image = None
        assert client.post(url, headers=headers).status_code == 503
        client.app.state.settings.inspection_image = IMAGE
        client.post(url, headers=headers)
        assert client.post(url + "/cancel", headers=headers).json()["status"] == "cancelled"
        assert not inspection_once(db_engine)
        with Session(db_engine) as db, db.begin():
            db.execute(
                update(Inspection).values(
                    status="running", attempts=3, lease_until=now() - timedelta(seconds=1)
                )
            )
        assert inspection_once(db_engine)
        assert client.get(url).json()["error"] == "RETRY_LIMIT"


def test_report_schema_is_strict():
    report = InspectionReport.model_validate_json(fixture_report(b"a,b\n1,2\n", "csv", IMAGE))
    raw = report.model_dump()
    raw["tables"][0]["row_count"] = True
    with pytest.raises(ValidationError):
        InspectionReport.model_validate(raw)


def test_delimiter_revision_and_persisted_selection(db_engine, monkeypatch):
    monkeypatch.setattr("dtd_api.inspections.run_isolated", fixture_report)
    with client_for(db_engine) as client, client_for(db_engine) as bob:
        headers, _, dataset = setup(client, db_engine)
        url = f"/api/v1/datasets/{dataset}/inspection"
        assert client.post(url, headers=headers).status_code == 202
        assert inspection_once(db_engine)
        selection = url + "/selection"
        assert client.post(selection, headers=headers, json={"table": "missing"}).status_code == 422
        bob_headers = login(bob, db_engine, "bob")
        assert bob.post(selection, headers=bob_headers, json={"table": "CSV"}).status_code == 404
        saved = client.post(selection, headers=headers, json={"table": "CSV"}).json()
        assert saved["selected_table"] == "CSV" and saved["dataset_version_id"]
        with Session(db_engine) as db:
            version = db.get(DatasetVersion, saved["dataset_version_id"])
            assert version.dataset_id == dataset and version.selection["table"] == "CSV"
            assert len(version.schema_hash) == 64
        assert client.get(url).json()["dataset_version_id"] == saved["dataset_version_id"]
        assert client.post(url, headers=headers, json={"delimiter": "&"}).status_code == 422
        changed = client.post(url, headers=headers, json={"delimiter": ";"}).json()
        assert changed["status"] == "queued" and changed["selected_table"] is None
        assert changed["dataset_version_id"] is None
        assert changed["revisions"] == 1 and changed["report"] is None
        assert client.post(url, headers=headers, json={"delimiter": "|"}).status_code == 409
        assert inspection_once(db_engine)
        report = client.get(url).json()
        assert report["report"]["delimiter"] == ";"
        assert client.post(url, headers=headers, json={"delimiter": ";"}).json()["revisions"] == 1
