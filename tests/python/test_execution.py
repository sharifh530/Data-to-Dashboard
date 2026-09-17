import json
import subprocess
from unittest.mock import patch

import pytest
from dtd_execution.policy import ProbePolicy
from dtd_execution.preflight import inspect_runtime
from dtd_execution.probe import EXPECTED_CHECKS, run_probe, validate_report


@pytest.mark.parametrize("failure", [FileNotFoundError(), subprocess.TimeoutExpired("docker", 10)])
def test_missing_or_hung_engine_fails_closed(failure: Exception) -> None:
    with patch("dtd_execution.preflight.subprocess.run", side_effect=failure):
        result = inspect_runtime()
    assert not result.execution_enabled
    assert not result.runtime_available


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"OSType": "linux", "Runtimes": {"runc": {}}}, "RUNSC_MISSING"),
        ({"OSType": "windows", "Runtimes": {"runsc": {}}}, "UNSUPPORTED_ENGINE"),
        ({"OSType": "linux", "Runtimes": {"runsc": {}}}, "PROBES_REQUIRED"),
        (None, "INVALID_RESPONSE"),
    ],
)
def test_registration_never_enables_execution(payload: object, expected: str) -> None:
    completed = subprocess.CompletedProcess([], 0, json.dumps(payload), "")
    with patch("dtd_execution.preflight.subprocess.run", return_value=completed):
        result = inspect_runtime()
    assert result.code == expected
    assert not result.execution_enabled


def test_probe_policy_cannot_inject_options_or_use_mutable_image() -> None:
    for image in ["python:latest", "--privileged", "python@sha256:wrong"]:
        with pytest.raises(ValueError):
            ProbePolicy(image)
    policy = ProbePolicy("example/probe@sha256:" + "a" * 64)
    with pytest.raises(ValueError):
        policy.command("--privileged")
    command = policy.command("dtd-probe-" + "b" * 32)
    assert "--runtime=runsc" in command
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--pids-limit=128" in command
    assert "--ulimit=nproc=32:32" in command
    assert "--privileged" not in command
    assert not any(value.startswith(("--volume", "--mount", "--env")) for value in command)


def test_probe_refuses_before_any_workload_when_engine_is_unavailable() -> None:
    from dtd_execution.preflight import Preflight

    unavailable = Preflight(False, False, "DOCKER_UNAVAILABLE", "Unavailable")
    with patch("dtd_execution.probe.inspect_runtime", return_value=unavailable):
        with patch("dtd_execution.probe.subprocess.Popen") as start:
            with pytest.raises(RuntimeError, match="Probe refused"):
                run_probe("example/probe@sha256:" + "a" * 64)
            start.assert_not_called()


def test_missing_failed_or_truthy_probe_results_cannot_pass() -> None:
    checks = dict.fromkeys(EXPECTED_CHECKS, True)
    assert validate_report(json.dumps({"schema_version": 1, "checks": checks}).encode()) == checks
    for patch_value in (False, 1, "true", None):
        with pytest.raises(ValueError):
            validate_report(
                json.dumps(
                    {
                        "schema_version": 1,
                        "checks": {
                            **checks,
                            "dns_denied": patch_value,
                        },
                    }
                ).encode()
            )
    with pytest.raises(ValueError):
        validate_report(b'{"schema_version": 1, "checks": {}}')
