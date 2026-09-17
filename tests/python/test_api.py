import pytest
from dtd_api.main import Settings, create_app
from fastapi.testclient import TestClient


def test_health_is_distinct_from_analysis_readiness() -> None:
    with TestClient(create_app(Settings(environment="local", database_url=None))) as client:
        assert client.get("/health/live").json()["status"] == "ok"
        ready = client.get("/health/ready")
        assert ready.status_code == 503
        assert ready.json()["error"]["code"] == "FOUNDATION_NOT_READY"
        assert ready.json()["error"]["request_id"] == ready.headers["X-Request-ID"]
        capabilities = client.get("/api/v1/capabilities").json()
        assert capabilities["execution_enabled"] is False
        assert capabilities["uploads_enabled"] is False


def test_hosted_startup_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="hosted startup is disabled"):
        create_app(Settings(environment="production"))


def test_no_execution_enable_environment_backdoor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DTD_EXECUTION_ENABLED", "true")
    with TestClient(create_app(Settings(environment="local", database_url=None))) as client:
        assert client.get("/api/v1/capabilities").json()["execution_enabled"] is False
        assert client.post("/api/v1/runs", json={"source": "print(123)"}).status_code == 404


def test_response_headers_do_not_trust_client_request_id() -> None:
    with TestClient(create_app(Settings(environment="local", database_url=None))) as client:
        result = client.get("/health/live", headers={"X-Request-ID": "untrusted"})
        assert result.headers["X-Request-ID"] != "untrusted"
        assert result.headers["Cache-Control"] == "no-store"
        assert result.headers["X-Content-Type-Options"] == "nosniff"
        assert "Access-Control-Allow-Origin" not in result.headers
