"""Interface to the offline UI compiler for generated React dashboards."""

import json
import subprocess
from dataclasses import dataclass

from dtd_api.settings import ROOT

COMPILER_TIMEOUT_SECONDS = 30


@dataclass
class CompilationResult:
    status: str  # "ready" | "error"
    bundle: str | None = None
    sha256: str | None = None
    size_bytes: int = 0
    error: str | None = None


def compile_dashboard_ui(source: str, run_id: str) -> CompilationResult:
    """Compile generated React TSX component into an offline IIFE bundle."""
    payload = json.dumps({"source": source, "run_id": run_id})
    script_path = ROOT / "scripts" / "compile-dashboard.mjs"

    try:
        proc = subprocess.run(
            ["node", str(script_path)],
            input=payload.encode("utf-8"),
            capture_output=True,
            timeout=COMPILER_TIMEOUT_SECONDS,
            cwd=str(ROOT),
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CompilationResult(
            status="error",
            error=f"UI compilation timed out after {COMPILER_TIMEOUT_SECONDS} seconds.",
        )
    except Exception as exc:
        return CompilationResult(
            status="error",
            error=f"Failed to launch UI compiler: {exc}",
        )

    if proc.returncode != 0:
        err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
        return CompilationResult(
            status="error",
            error=f"UI compiler failed with code {proc.returncode}: {err_msg}",
        )

    try:
        out_data = json.loads(proc.stdout.decode("utf-8"))
        if out_data.get("status") == "ready":
            return CompilationResult(
                status="ready",
                bundle=out_data["bundle"],
                sha256=out_data["sha256"],
                size_bytes=out_data["size_bytes"],
            )
        return CompilationResult(
            status="error",
            error=out_data.get("error", "Unknown compilation error"),
        )
    except Exception as exc:
        return CompilationResult(
            status="error",
            error=f"Failed to parse compiler output: {exc}",
        )
