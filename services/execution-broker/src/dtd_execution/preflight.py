"""Inspect Docker capabilities without starting a workload or changing host settings."""

import json
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Preflight:
    runtime_available: bool
    execution_enabled: bool
    code: str
    reason: str

    def to_dict(self) -> dict[str, bool | str]:
        return asdict(self)


def inspect_runtime() -> Preflight:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return Preflight(False, False, "DOCKER_UNAVAILABLE", "Docker is unavailable or timed out.")
    if result.returncode != 0:
        return Preflight(False, False, "DOCKER_UNAVAILABLE", "Docker engine is not reachable.")
    try:
        info = json.loads(result.stdout)
        if not isinstance(info, dict):
            raise ValueError("Unexpected Docker response")
        runtimes = info.get("Runtimes")
        if info.get("OSType") != "linux" or not isinstance(runtimes, dict):
            return Preflight(False, False, "UNSUPPORTED_ENGINE", "A Linux engine is required.")
        if "runsc" not in runtimes:
            return Preflight(False, False, "RUNSC_MISSING", "The runsc runtime is not registered.")
    except (ValueError, TypeError):
        return Preflight(False, False, "INVALID_RESPONSE", "Cannot validate Docker capabilities.")
    return Preflight(
        True,
        False,
        "PROBES_REQUIRED",
        "runsc is registered. Actual isolation probes and broker integration are still required.",
    )
