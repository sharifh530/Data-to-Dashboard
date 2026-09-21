"""Copy only reviewed runtime sources into the dedicated distro and run fixed commands."""

import argparse
import io
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ["wsl", "--distribution", "dtd-sandbox",
          "--user", "root", "--cd", "/opt/dtd", "--"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=[
                        "sync", "preflight", "probe", "resources", "transform"])
    parser.add_argument("--image")
    args = parser.parse_args()
    if args.action == "sync":
        files = [ROOT / "scripts/sandbox-preflight.py",
                 ROOT / "scripts/sandbox-probe.py"]
        files += [ROOT / "scripts/sandbox-resources.py"]
        files += [ROOT / "scripts/sandbox-inspect.py"]
        files += [ROOT / "scripts/sandbox-transform.py"]
        files += [ROOT / "scripts/inspection-reaper.py"]
        files += sorted((ROOT / "sandbox/probe").glob("*"))
        files += sorted((ROOT / "sandbox/resources").glob("*"))
        files += sorted((ROOT / "sandbox/inspector").glob("*"))
        files += sorted((ROOT / "sandbox/transformer").glob("*"))
        files += sorted((ROOT /
                        "services/execution-broker/src/dtd_execution").glob("*.py"))
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as tar:
            for file in files:
                if file.is_file() and not file.is_symlink():
                    data = file.read_bytes().replace(b"\r\n", b"\n")
                    info = tarfile.TarInfo(file.relative_to(ROOT).as_posix())
                    info.size = len(data)
                    info.mode = 0o644
                    tar.addfile(info, io.BytesIO(data))
        subprocess.run(PREFIX[:6] + ["/", "--", "mkdir",
                       "-p", "/opt/dtd"], check=True, timeout=30)
        subprocess.run(
            PREFIX + ["tar", "-xf", "-"], input=archive.getvalue(), check=True, timeout=30
        )
        print(
            "Synced reviewed runtime sources only; no credentials, uploads or host mounts.")
        return
    command = PREFIX + [
        "env",
        "PYTHONPATH=/opt/dtd/services/execution-broker/src",
        "python3",
        f"scripts/sandbox-{args.action}.py",
    ]
    if args.action in {"probe", "resources", "transform"}:
        from dtd_execution.policy import ProbePolicy

        if not args.image:
            parser.error("probe/resources/transform requires --image")
        ProbePolicy(args.image)
        command += ["--image", args.image]
    raise SystemExit(subprocess.run(
        command, timeout=180, check=False).returncode)


if __name__ == "__main__":
    main()
