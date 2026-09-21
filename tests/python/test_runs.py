import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from dtd_api.errors import ApiError
from dtd_api.models import Dataset, Outbox, Project, Run, RunEvent, User, WorkItem, now
from dtd_api.run_engine import (
    STAGES,
    claim_one,
    complete,
    dispatch_one,
    fixture_result,
    heartbeat,
    work_once,
)
from dtd_api.runs import event_batch
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.orm import Session
from test_projects_auth import client_for, create, login


def submit(client, headers, project, key="run"):
    return client.post(
        f"/api/v1/projects/{project}/demo-runs",
        json={},
        headers={**headers, "Idempotency-Key": key},
    )


def setup_run(client, engine):
    headers = login(client, engine, "alice")
    project = create(client, headers).json()["id"]
    response = submit(client, headers, project)
    assert response.status_code == 202, response.text
    return headers, project, response.json()["id"]


def expire(engine):
    with Session(engine) as db, db.begin():
        db.execute(update(WorkItem).values(lease_expires_at=now() - timedelta(seconds=1)))


def test_submission_execution_replay_and_ownership(db_engine):
    with client_for(db_engine) as client, client_for(db_engine) as other:
        headers, project, run_id = setup_run(client, db_engine)
        assert submit(client, headers, project).json()["id"] == run_id
        assert submit(client, headers, project, "second").status_code == 429
        other_headers = login(other, db_engine, "bob")
        for path in (
            f"/runs/{run_id}",
            f"/runs/{run_id}/events?follow=false",
            f"/projects/{project}/runs",
        ):
            assert other.get("/api/v1" + path).status_code == 404
        assert other.post(f"/api/v1/runs/{run_id}/cancel", headers=other_headers).status_code == 404
        assert client.post(f"/api/v1/runs/{run_id}/cancel").status_code == 403
        with Session(db_engine) as db, db.begin():
            assert db.scalar(select(func.count()).select_from(Outbox)) == 1
            db.add(Outbox(project_id=project, topic="run.requested", payload={"run_id": run_id}))
        for _ in range(4):
            work_once(db_engine)
        result = client.get(f"/api/v1/runs/{run_id}").json()
        assert result["status"] == "succeeded"
        assert result["completed_stages"] == list(STAGES)
        assert result["result"] == {"revenue": 27200, "orders": 176, "mode": "synthetic"}
        assert len(client.get(f"/api/v1/projects/{project}/runs").json()["items"]) == 1
        response = client.get(f"/api/v1/runs/{run_id}/events?follow=false")
        assert response.status_code == 200
        ids = [int(line[4:]) for line in response.text.splitlines() if line.startswith("id: ")]
        assert ids == list(range(1, result["event_sequence"] + 1))
        replay = client.get(
            f"/api/v1/runs/{run_id}/events?follow=false", headers={"Last-Event-ID": "2"}
        )
        assert replay.text.startswith("id: 3\n")
        assert (
            client.get(
                f"/api/v1/runs/{run_id}/events", headers={"Last-Event-ID": "999"}
            ).status_code
            == 409
        )
        assert (
            client.get(f"/api/v1/runs/{run_id}/events", headers={"Last-Event-ID": "-1"}).status_code
            == 422
        )
        with Session(db_engine) as db, db.begin():
            db.execute(delete(RunEvent).where(RunEvent.run_id == run_id, RunEvent.sequence <= 2))
        assert "event: snapshot" in client.get(f"/api/v1/runs/{run_id}/events?follow=false").text
        token = client.cookies.get("__Host-dtd_session")
        owner = client.get("/api/v1/auth/session").json()["user_id"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
        with pytest.raises(ApiError):
            event_batch(db_engine, run_id, owner, token, 0)


def test_recovery_fences_old_worker_and_preserves_checkpoint(db_engine):
    with client_for(db_engine) as client:
        _, _, run_id = setup_run(client, db_engine)
        dispatch_one(db_engine)
        first = claim_one(db_engine)
        assert heartbeat(db_engine, first)
        assert complete(db_engine, first, fixture_result(first.stage))
        assert not complete(db_engine, first, fixture_result(first.stage))
        stale = claim_one(db_engine)
        expire(db_engine)
        recovered = claim_one(db_engine)
        assert recovered.stage == STAGES[1]
        assert recovered.generation > stale.generation
        assert not heartbeat(db_engine, stale)
        assert not complete(db_engine, stale, fixture_result(stale.stage))
        assert complete(db_engine, recovered, fixture_result(recovered.stage))
        work_once(db_engine)
        assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "succeeded"


@pytest.mark.parametrize("active", [False, True])
def test_cancellation_cannot_publish(db_engine, active):
    with client_for(db_engine) as client:
        headers, _, run_id = setup_run(client, db_engine)
        claim = None
        if active:
            dispatch_one(db_engine)
            claim = claim_one(db_engine)
        response = client.post(f"/api/v1/runs/{run_id}/cancel", headers=headers)
        assert response.json()["status"] == ("cancelling" if active else "cancelled")
        if claim:
            assert not complete(db_engine, claim, fixture_result(claim.stage))
        work_once(db_engine)
        result = client.get(f"/api/v1/runs/{run_id}").json()
        assert result["status"] == "cancelled" and result["result"] is None


@pytest.mark.parametrize(
    "reason",
    ["retry", "deadline", "config", "output", "project", "dataset", "owner", "cancel-crash"],
)
def test_bounded_failure_and_publication_guards(db_engine, reason):
    with client_for(db_engine) as client:
        headers, _, run_id = setup_run(client, db_engine)
        dispatch_one(db_engine)
        claim = claim_one(db_engine)
        if reason == "retry":
            for _ in range(2):
                expire(db_engine)
                assert claim_one(db_engine)
            expire(db_engine)
            assert claim_one(db_engine) is None
        elif reason == "config":
            expire(db_engine)
            with Session(db_engine) as db, db.begin():
                db.execute(update(Run).values(config={"code": "untrusted"}))
            assert claim_one(db_engine) is None
        elif reason == "cancel-crash":
            client.post(f"/api/v1/runs/{run_id}/cancel", headers=headers)
            expire(db_engine)
            assert claim_one(db_engine) is None
        else:
            with Session(db_engine) as db, db.begin():
                if reason == "deadline":
                    db.execute(update(Run).values(started_at=now() - timedelta(seconds=601)))
                if reason == "project":
                    db.execute(update(Project).values(deleted_at=now()))
                if reason == "dataset":
                    db.execute(update(Dataset).values(deleted_at=now()))
                if reason == "owner":
                    db.execute(update(User).values(active=False))
            output = {} if reason == "output" else fixture_result(claim.stage)
            assert not complete(db_engine, claim, output)
        with Session(db_engine) as db:
            run = db.get(Run, run_id)
            expected = (
                "cancelled"
                if reason in {"project", "dataset", "owner", "cancel-crash"}
                else "failed"
            )
            assert run.status == expected and run.result is None


def test_postgres_concurrent_claims_and_admission(postgres_engine):
    with client_for(postgres_engine) as client:
        headers, project, run_id = setup_run(client, postgres_engine)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: submit(client, headers, project), range(2)))
        assert all(response.json()["id"] == run_id for response in responses)
        dispatch_one(postgres_engine)
        with ThreadPoolExecutor(max_workers=2) as pool:
            claims = list(pool.map(lambda _: claim_one(postgres_engine), range(2)))
        assert sum(claim is not None for claim in claims) == 1


def test_postgres_cancel_publication_race(postgres_engine):
    with client_for(postgres_engine) as client:
        headers, _, run_id = setup_run(client, postgres_engine)
        work_once(postgres_engine)
        work_once(postgres_engine)
        claim = claim_one(postgres_engine)
        with ThreadPoolExecutor(max_workers=2) as pool:
            publish = pool.submit(complete, postgres_engine, claim, fixture_result(claim.stage))
            cancel = pool.submit(client.post, f"/api/v1/runs/{run_id}/cancel", headers=headers)
            assert cancel.result().status_code == 200
            published = publish.result()
        result = client.get(f"/api/v1/runs/{run_id}").json()
        assert result["status"] == ("succeeded" if published else "cancelled")
        assert (result["result"] is not None) == published
        assert not complete(postgres_engine, claim, fixture_result(claim.stage))


def test_postgres_worker_process_restart(postgres_engine):
    with client_for(postgres_engine) as client:
        _, _, run_id = setup_run(client, postgres_engine)
        with postgres_engine.connect() as connection:
            schema = connection.scalar(text("SELECT current_schema()"))
        url = postgres_engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
        env = {**os.environ, "DTD_PROCESS_TEST_URL": url.render_as_string(hide_password=False)}
        code = (
            "import os,json; from dataclasses import asdict; "
            "from dtd_api.database import make_engine; "
            "from dtd_api.run_engine import work_once,claim_one; "
            "e=make_engine(os.environ['DTD_PROCESS_TEST_URL']); "
            "work_once(e); print(json.dumps(asdict(claim_one(e)))); e.dispose()"
        )
        process = subprocess.run(
            [sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=30
        )
        assert process.returncode == 0
        abandoned = json.loads(process.stdout)
        assert abandoned["stage"] == STAGES[1]
        expire(postgres_engine)
        recovered = claim_one(postgres_engine)
        assert recovered.stage == STAGES[1]
        assert recovered.token != abandoned["token"]
        assert complete(postgres_engine, recovered, fixture_result(recovered.stage))
        work_once(postgres_engine)
        assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "succeeded"


def test_analysis_run_lifecycle_and_artifacts(db_engine, monkeypatch):
    import hashlib

    from dtd_api.baseline_contracts import (
        BaselineComparison,
        BaselineReport,
        ModelMetrics,
        SplitInfo,
    )
    from dtd_api.cleaning_contracts import CleaningReport, CleaningSummary, ColumnLineage
    from dtd_api.inspections import inspection_once
    from dtd_api.profiles import profile_once
    from test_inspections import fixture_report, setup
    from test_profiles import fixed_profile

    monkeypatch.setattr("dtd_api.inspections.run_isolated", fixture_report)
    monkeypatch.setattr("dtd_api.profiles.run_isolated", fixed_profile)

    fake_csv = b"col_a,col_b\n1,2\n"

    def fake_transform(
        data, file_format, image, script, delimiter=None, table_name=None, mode="transform"
    ):
        if mode == "transform":
            report = CleaningReport(
                schema_version="1",
                status="ready",
                input_sha256=hashlib.sha256(data).hexdigest(),
                output_sha256=hashlib.sha256(fake_csv).hexdigest(),
                summary=CleaningSummary(
                    original_rows=2,
                    cleaned_rows=2,
                    original_columns=2,
                    cleaned_columns=2,
                    duplicate_rows_removed=0,
                ),
                operations=[],
                lineage=[
                    ColumnLineage(
                        original_name="a",
                        clean_name="a",
                        original_inferred_type="string",
                        clean_type="string",
                        null_count_before=0,
                        null_count_after=0,
                    ),
                    ColumnLineage(
                        original_name="b",
                        clean_name="b",
                        original_inferred_type="string",
                        clean_type="string",
                        null_count_before=0,
                        null_count_after=0,
                    ),
                ],
                warnings=[],
            )
            return report, fake_csv
        elif mode == "baseline":
            report = BaselineReport(
                schema_version="1",
                status="ready",
                input_sha256=hashlib.sha256(data).hexdigest(),
                task_type="classification",
                target_column="a",
                features=[],
                split=SplitInfo(
                    train_rows=1, test_rows=1, seed=42, strategy="stratified", test_fraction=0.5
                ),
                reference=ModelMetrics(
                    model_name="dummy", accuracy=1.0, macro_f1=1.0, fit_time_seconds=0.1
                ),
                candidate=ModelMetrics(
                    model_name="logistic", accuracy=1.0, macro_f1=1.0, fit_time_seconds=0.1
                ),
                comparison=BaselineComparison(
                    candidate_better=False, better_model="dummy", reason="test"
                ),
                confusion_matrix=[[1]],
            )
            return report, fake_csv

    monkeypatch.setattr("dtd_api.run_engine.run_isolated_transform", fake_transform)

    with client_for(db_engine) as client, client_for(db_engine) as bob:
        headers, project, dataset = setup(client, db_engine)
        inspection_url = f"/api/v1/datasets/{dataset}/inspection"
        assert client.post(inspection_url, headers=headers).status_code == 202
        assert inspection_once(db_engine)
        version_id = client.post(
            inspection_url + "/selection", headers=headers, json={"table": "CSV"}
        ).json()["dataset_version_id"]

        run_url = f"/api/v1/projects/{project}/runs"

        run_payload = {
            "dataset_version_id": version_id,
            "target_column": "a",
            "task_type": "classification",
        }

        assert (
            client.post(
                run_url,
                headers={**headers, "Idempotency-Key": "analysis-1"},
                json=run_payload,
            ).status_code
            == 409
        )

        profile_url = f"/api/v1/dataset-versions/{version_id}/profile"
        assert client.post(profile_url, headers=headers).status_code == 202
        assert profile_once(db_engine)

        res = client.post(
            run_url,
            headers={**headers, "Idempotency-Key": "analysis-1"},
            json=run_payload,
        )
        assert res.status_code == 202
        run_id = res.json()["id"]
        assert res.json()["mode"] == "analysis"

        replay = client.post(
            run_url,
            headers={**headers, "Idempotency-Key": "analysis-1"},
            json=run_payload,
        )
        assert replay.status_code == 202
        assert replay.json()["id"] == run_id

        assert (
            client.post(
                run_url,
                headers={**headers, "Idempotency-Key": "analysis-2"},
                json=run_payload,
            ).status_code
            == 429
        )

        fake_transformer_image = "sha256:" + "a" * 64
        assert work_once(db_engine, fake_transformer_image)  # clean_dataset
        assert work_once(db_engine, fake_transformer_image)  # train_baseline
        assert work_once(db_engine, fake_transformer_image)  # plan_dashboard

        run_data = client.get(f"/api/v1/runs/{run_id}").json()
        assert run_data["status"] == "succeeded"
        assert "clean_dataset" in run_data["completed_stages"]
        assert "train_baseline" in run_data["completed_stages"]
        assert "plan_dashboard" in run_data["completed_stages"]
        assert run_data["result"]["schema_version"] == "1"

        art_url = f"/api/v1/projects/{project}/runs/{run_id}/artifacts"
        artifacts = client.get(art_url).json()
        assert len(artifacts) == 6
        kinds = {a["kind"] for a in artifacts}
        assert kinds == {
            "cleaned_data",
            "cleaning_report",
            "generated_script",
            "baseline_report",
            "baseline_script",
            "dashboard_spec",
        }

        # Test dashboard spec endpoint
        dash_res = client.get(f"/api/v1/runs/{run_id}/dashboard")
        assert dash_res.status_code == 200
        dash_data = dash_res.json()
        assert dash_data["render_mode"] == "fallback"
        assert dash_data["spec"]["schema_version"] == "1"
        assert len(dash_data["spec"]["kpis"]) > 0

        # Test dashboard query endpoint
        q_res = client.post(
            f"/api/v1/runs/{run_id}/queries",
            json={"query_id": "table", "cursor": 0, "page_size": 10},
        )
        assert q_res.status_code == 200
        assert q_res.json()["query_id"] == "table"
        assert len(q_res.json()["data"]) == 1

        cleaned_art = next(a for a in artifacts if a["kind"] == "cleaned_data")
        dl_res = client.get(f"{art_url}/{cleaned_art['id']}/download")
        assert dl_res.status_code == 200
        assert dl_res.content == fake_csv

        bob_headers = login(bob, db_engine, "bob")
        assert bob.get(art_url, headers=bob_headers).status_code == 404
        dl_url = f"{art_url}/{cleaned_art['id']}/download"
        assert bob.get(dl_url, headers=bob_headers).status_code == 404
