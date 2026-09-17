"""Fixed resource acceptance suite. Run inside dtd-sandbox, never on the developer host."""

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path
from uuid import uuid4

from dtd_execution.policy import ProbePolicy
from dtd_execution.preflight import inspect_runtime


def docker(*args: str) -> str:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=True, timeout=15
    ).stdout.strip()


def exercise(image: str, mode: str) -> dict[str, object]:
    name = "dtd-probe-" + uuid4().hex
    command = ProbePolicy(image).command(name)
    command[1] = "create"
    command.remove("--rm")
    replacements = {
        "--cpus=2": "--cpus=0.5",
        "--memory=2g": "--memory=256m",
        "--memory-swap=2g": "--memory-swap=256m",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777": (
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=8m,mode=1777"
        ),
    }
    command = [replacements.get(arg, arg) for arg in command]
    command.append(mode)
    process = None
    reader = None
    output = bytearray()
    overflow = threading.Event()
    ready = threading.Event()
    cgroup = None
    reason = "exit"
    started = time.monotonic()
    try:
        subprocess.run(command, capture_output=True, check=True, timeout=15)
        process = subprocess.Popen(
            ["docker", "start", "--attach", name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stream = process.stdout
        assert stream is not None

        def drain() -> None:
            while chunk := stream.read1(4096):
                if len(output) + len(chunk) > 65536:
                    overflow.set()
                    continue  # Drain without retaining data so the Docker client can exit.
                output.extend(chunk)
                if b'"ready": true' in output:
                    ready.set()

        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if mode in {"cpu", "cancel", "timeout"} and ready.is_set() and cgroup is None:
                info = json.loads(docker("inspect", name))[0]
                pid = info["State"]["Pid"]
                relative = Path(f"/proc/{pid}/cgroup").read_text().strip().split("::", 1)[1]
                cgroup = (Path("/sys/fs/cgroup") / relative.lstrip("/")).resolve()
                assert cgroup.is_relative_to(Path("/sys/fs/cgroup"))
            if overflow.is_set():
                reason = "output_limit"
                break
            if mode == "cancel" and ready.is_set() and cgroup is not None:
                reason = "cancelled"
                break
            if mode == "cpu" and cgroup is not None and elapsed >= 3:
                values = dict(
                    line.split() for line in (cgroup / "cpu.stat").read_text().splitlines()
                )
                assert int(values["nr_throttled"]) > 0, "CPU throttling not observed"
                reason = "cpu_throttled"
                break
            if mode == "timeout" and elapsed >= 3:
                assert ready.is_set(), "Timeout did not reach running child workload"
                reason = "deadline"
                break
            if elapsed > 15:
                raise RuntimeError(f"Resource exercise {mode} exceeded hard deadline")
            time.sleep(0.02)
        if process.poll() is None:
            docker("kill", name)
        process.wait(timeout=5)
        reader.join(timeout=2)
        assert not reader.is_alive()
        state = json.loads(docker("inspect", name))[0]["State"]
        assert state["Running"] is False
        if mode == "memory":
            assert state["OOMKilled"] is True and state["ExitCode"] != 0, "OOM not enforced"
        elif mode in {"disk", "pids"}:
            if not output.startswith(b"{"):
                raise RuntimeError(
                    f"Fixed exercise {mode}: {state}; output={bytes(output[:1200])!r}"
                )
            report = json.loads(output)
            assert (
                state["ExitCode"] == 0
                and report["disk_full" if mode == "disk" else "pids_limited"] is True
            )
            if mode == "pids":
                assert report["children"] < 32
        else:
            expected = {
                "output": "output_limit",
                "cancel": "cancelled",
                "cpu": "cpu_throttled",
                "timeout": "deadline",
            }
            assert reason == expected[mode]
        if cgroup and cgroup.exists():
            assert not (cgroup / "cgroup.procs").read_text().strip(), "Child processes survived"
        return {
            "case": mode,
            "status": "passed",
            "stop_reason": reason,
            "captured_bytes": len(output),
            "seconds": round(time.monotonic() - started, 2),
        }
    finally:
        # Remove exactly this generated container; never prune unrelated resources.
        docker("rm", "--force", name)
        assert not docker("ps", "-aq", "--filter", f"name=^/{name}$")
        if process:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            if reader:
                reader.join(timeout=2)
            if process.stdout:
                process.stdout.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    ProbePolicy(args.image)
    if not inspect_runtime().runtime_available:
        raise SystemExit("Required runtime unavailable; refusing resource exercises")
    reports = []
    for mode in ("disk", "pids", "memory", "output", "cpu", "timeout", "cancel"):
        report = exercise(args.image, mode)
        reports.append(report)
        print(json.dumps(report), flush=True)
    print(json.dumps({"status": "passed", "cases": len(reports), "execution_enabled": False}))


if __name__ == "__main__":
    main()
