"""Bounded launcher for the operator-built synthetic image. Not a user-code API."""

import json
import subprocess
import threading
import time
from uuid import uuid4

from dtd_execution.policy import ProbePolicy
from dtd_execution.preflight import inspect_runtime

EXPECTED_CHECKS = {
    "non_root",
    "read_only_root",
    "ipv4_egress_denied",
    "ipv6_egress_denied",
    "metadata_denied",
    "dns_denied",
    "no_runtime_socket",
    "no_provider_secret",
}


def validate_report(raw: bytes) -> dict[str, bool]:
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Invalid probe report")
    checks = value.get("checks")
    if not isinstance(checks, dict) or set(checks) != EXPECTED_CHECKS:
        raise ValueError("Missing or unexpected probe checks")
    if any(value is not True for value in checks.values()):
        raise ValueError("An isolation probe failed")
    return {key: True for key in EXPECTED_CHECKS}


def run_probe(image: str) -> dict[str, object]:
    policy = ProbePolicy(image)
    preflight = inspect_runtime()
    if not preflight.runtime_available:
        raise RuntimeError(f"Probe refused: {preflight.code}")
    name = "dtd-probe-" + uuid4().hex
    output = bytearray()
    overflow = threading.Event()
    process: subprocess.Popen[bytes] | None = None
    reader: threading.Thread | None = None
    try:
        process = subprocess.Popen(
            policy.command(name), stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        assert process.stdout is not None
        stream = process.stdout

        def read_output() -> None:
            while chunk := stream.read(4096):
                if len(output) + len(chunk) > 65536:
                    overflow.set()
                    return
                output.extend(chunk)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        deadline = time.monotonic() + 30
        while process.poll() is None:
            if overflow.is_set():
                raise RuntimeError("Probe exceeded 64 KiB output limit")
            if time.monotonic() >= deadline:
                raise RuntimeError("Probe exceeded 30 second deadline")
            time.sleep(0.05)
        reader.join(timeout=1)
        if reader.is_alive() or overflow.is_set() or process.returncode != 0:
            raise RuntimeError("Probe failed or output was incomplete")
        checks = validate_report(bytes(output))
        return {"status": "passed", "image": image, "checks": checks, "execution_enabled": False}
    finally:
        # Remove only this generated container name, including after a timeout/client death.
        try:
            cleanup = subprocess.run(
                ["docker", "rm", "--force", name],
                capture_output=True,
                timeout=10,
                check=False,
            )
            # --rm may already have removed it. Verify absence instead of trusting an rm error.
            if cleanup.returncode != 0:
                present = subprocess.run(
                    [
                        "docker",
                        "container",
                        "ls",
                        "--all",
                        "--quiet",
                        "--filter",
                        f"name=^/{name}$",
                    ],
                    capture_output=True,
                    timeout=10,
                    check=False,
                )
                if present.returncode != 0 or present.stdout.strip():
                    raise RuntimeError("Cannot verify synthetic probe container cleanup")
        finally:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
                if reader is not None:
                    reader.join(timeout=1)
                if process.stdout is not None:
                    process.stdout.close()
