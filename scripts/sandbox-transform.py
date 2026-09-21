"""Trusted Linux broker for isolated dataset transformation.

Never execute generated code or parse user uploads directly here.
Passes framed payload into gVisor container and drains bounded results.
"""

import argparse
import subprocess
import sys
import threading
import time
from uuid import uuid4

from dtd_execution.policy import ProbePolicy
from dtd_execution.preflight import inspect_runtime

MAX_TRANSFORM_INPUT = 12 * 1024 * 1024  # 10 MiB data + metadata
MAX_TRANSFORM_OUTPUT = 16 * 1024 * 1024  # 15 MiB cleaned CSV + report


def main() -> None:
    parser = argparse.ArgumentParser(description="Broker for isolated dataset transformation")
    parser.add_argument("--image", required=True, help="Pinned Docker image ID")
    args = parser.parse_args()

    policy = ProbePolicy(args.image)
    if not inspect_runtime().runtime_available:
        raise SystemExit(2)

    # Verify container reaper timer is active
    supervisor = subprocess.run(
        ["systemctl", "is-active", "--quiet", "dtd-inspection-reaper.timer"], timeout=5
    )
    if supervisor.returncode:
        raise SystemExit(2)

    # Read framed input
    data = sys.stdin.buffer.read(MAX_TRANSFORM_INPUT + 1)
    if not data or len(data) > MAX_TRANSFORM_INPUT:
        raise SystemExit(2)

    name = "dtd-probe-" + uuid4().hex
    command = policy.command(name)
    command.insert(-1, "--interactive")
    command.insert(-1, "--label=dtd.inspector=1")

    output = bytearray()
    overflow = threading.Event()
    process = None
    reader = writer = None

    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        def drain():
            while chunk := process.stdout.read1(65536):
                if len(output) + len(chunk) > MAX_TRANSFORM_OUTPUT:
                    overflow.set()
                else:
                    output.extend(chunk)

        def feed():
            try:
                process.stdin.write(data)
                process.stdin.close()
            except (BrokenPipeError, OSError):
                pass

        reader = threading.Thread(target=drain, daemon=True)
        writer = threading.Thread(target=feed, daemon=True)
        reader.start()
        writer.start()

        # 45-second execution deadline for transformation
        deadline = time.monotonic() + 45
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() > deadline:
                raise RuntimeError("Transformation budget exceeded")
            time.sleep(0.05)

        reader.join(timeout=2)
        writer.join(timeout=2)
        if process.returncode or overflow.is_set() or reader.is_alive() or writer.is_alive():
            raise RuntimeError("Transformation failed or budget exceeded")
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
        remaining = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"name=^/{name}$"],
            capture_output=True,
            timeout=10,
            check=True,
        )
        if remaining.stdout.strip():
            raise RuntimeError("Container cleanup failed")
        if process:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if reader:
                reader.join(timeout=2)
            if writer:
                writer.join(timeout=2)

    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    main()
