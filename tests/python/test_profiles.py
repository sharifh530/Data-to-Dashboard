"""Profile publication is bounded, owned and tied to the current selection."""

import hashlib

from dtd_api.inspection_contracts import InspectionReport, ProfileReport
from dtd_api.inspections import inspection_once
from dtd_api.profiles import canonical, profile_once
from test_inspections import fixture_report, setup
from test_projects_auth import client_for, login


def fixed_profile(data, file_format, image, delimiter, index):
    inspected = InspectionReport.model_validate_json(
        fixture_report(data, file_format, image, delimiter)
    )
    table = inspected.tables[0].model_dump()
    table["profile"] = [
        {
            "name": name,
            "distinct": 1,
            "numeric_count": 1,
            "nonnumeric_count": 0,
            "numeric_min": value,
            "numeric_max": value,
            "top_values": [{"value": value, "count": 1}],
        }
        for name, value in zip(table["columns"], table["preview"][0], strict=True)
    ]
    return (
        ProfileReport(
            schema_version="1",
            sha256=hashlib.sha256(data).hexdigest(),
            format=file_format,
            status="ready",
            tables=[table],
            warnings=[],
            delimiter=delimiter or ",",
            error=None,
        )
        .model_dump_json()
        .encode()
    )


def test_profile_selected_version_owner_artifact_and_stale_rejection(db_engine, monkeypatch):
    monkeypatch.setattr("dtd_api.inspections.run_isolated", fixture_report)
    monkeypatch.setattr("dtd_api.profiles.run_isolated", fixed_profile)
    with client_for(db_engine) as client, client_for(db_engine) as bob:
        headers, _, dataset = setup(client, db_engine)
        inspection_url = f"/api/v1/datasets/{dataset}/inspection"
        assert client.post(inspection_url, headers=headers).status_code == 202
        assert inspection_once(db_engine)
        version_id = client.post(
            inspection_url + "/selection", headers=headers, json={"table": "CSV"}
        ).json()["dataset_version_id"]
        url = f"/api/v1/dataset-versions/{version_id}/profile"
        assert client.post(url, headers=headers).status_code == 202
        assert client.post(url, headers=headers).json()["attempts"] == 0
        bob_headers = login(bob, db_engine, "bob")
        assert bob.get(url).status_code == 404
        assert bob.post(url, headers=bob_headers).status_code == 404
        assert profile_once(db_engine)
        result = client.get(url).json()
        assert result["status"] == "ready"
        assert result["report"]["tables"][0]["profile"][0]["numeric_min"] == "1"
        report = ProfileReport.model_validate(result["report"])
        assert (
            result["report_sha256"]
            == hashlib.sha256(canonical(report.model_dump(mode="json"))).hexdigest()
        )
        assert not profile_once(db_engine)
        assert (
            client.post(inspection_url, headers=headers, json={"delimiter": ";"}).status_code == 202
        )
        assert client.get(url).status_code == 404


def test_profile_lineage_failure_never_publishes(db_engine, monkeypatch):
    monkeypatch.setattr("dtd_api.inspections.run_isolated", fixture_report)
    with client_for(db_engine) as client:
        headers, _, dataset = setup(client, db_engine)
        inspection_url = f"/api/v1/datasets/{dataset}/inspection"
        client.post(inspection_url, headers=headers)
        inspection_once(db_engine)
        version = client.post(
            inspection_url + "/selection", headers=headers, json={"table": "CSV"}
        ).json()["dataset_version_id"]
        url = f"/api/v1/dataset-versions/{version}/profile"
        client.post(url, headers=headers)

        def wrong(data, fmt, image, delimiter, index):
            report = ProfileReport.model_validate_json(
                fixed_profile(data, fmt, image, delimiter, index)
            )
            report.sha256 = "0" * 64
            return report.model_dump_json().encode()

        monkeypatch.setattr("dtd_api.profiles.run_isolated", wrong)
        assert profile_once(db_engine)
        result = client.get(url).json()
        assert result["status"] == "failed" and result["report"] is None
        assert result["report_sha256"] is None
