"""Trusted Linux broker for one fixed inspector. Never parse uploaded files here."""

import argparse
import subprocess
import sys
import threading
import time
from uuid import uuid4

from dtd_execution.policy import ProbePolicy
from dtd_execution.preflight import inspect_runtime


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--format", required=True, choices=["csv", "sqlite"])
    parser.add_argument("--delimiter", choices=["comma", "semicolon", "tab", "pipe"])
    parser.add_argument("--profile-index", type=int, choices=range(10))
    args = parser.parse_args()
    if args.delimiter and args.format != "csv":
        raise SystemExit(2)
    policy = ProbePolicy(args.image)
    if not inspect_runtime().runtime_available:
        raise SystemExit(2)
    supervisor = subprocess.run(
        ["systemctl", "is-active", "--quiet", "dtd-inspection-reaper.timer"], timeout=5
    )
    if supervisor.returncode:
        raise SystemExit(2)
    data = sys.stdin.buffer.read(10485761)
    if not data or len(data) > 10485760:
        raise SystemExit(2)
    name = "dtd-probe-" + uuid4().hex
    command = policy.command(name)
    command.insert(-1, "--interactive")
    command.insert(-1, "--label=dtd.inspector=1")
    command.append(args.format)
    if args.delimiter:
        command.append({"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}[args.delimiter])
    elif args.profile_index is not None:
        command.append("auto")
    if args.profile_index is not None:
        command.extend(["profile", str(args.profile_index)])
    output = bytearray()
    overflow = threading.Event()
    process = None
    reader = writer = None
    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )

        def drain():
            while chunk := process.stdout.read1(4096):
                if len(output) + len(chunk) > 524288:
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
        deadline = time.monotonic() + 30
        while process.poll() is None:
            if overflow.is_set() or time.monotonic() > deadline:
                raise RuntimeError("Inspector budget exceeded")
            time.sleep(0.05)
        reader.join(timeout=2)
        writer.join(timeout=2)
        if process.returncode or overflow.is_set() or reader.is_alive() or writer.is_alive():
            raise RuntimeError("Inspector failed")
    finally:
        subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=10)
        remaining = subprocess.run(
            ["docker", "ps", "-aq", "--filter", f"name=^/{name}$"],
            capture_output=True,
            timeout=10,
            check=True,
        )
        if remaining.stdout.strip():
            raise RuntimeError("Inspector cleanup failed")
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
