"""Execution boundary for isolated dataset transformations inside gVisor."""

import hashlib
import json
import struct
import subprocess
from typing import Any

from dtd_api.cleaning_contracts import CleaningReport

MAX_REPORT_JSON = 512 * 1024
MAX_CLEANED_CSV = 15 * 1024 * 1024


def run_isolated_transform(
    data: bytes,
    file_format: str,
    image: str,
    script: str,
    delimiter: str | None = None,
    table_name: str | None = None,
) -> tuple[CleaningReport, bytes]:
    """Execute cleaning transformation script strictly inside the gVisor sandbox.

    Never execute generated Python in the API process or on the developer host.
    """
    metadata: dict[str, Any] = {
        "format": file_format,
        "delimiter": delimiter,
        "table": table_name,
        "script": script,
    }
    meta_bytes = json.dumps(metadata).encode("utf-8")
    header = struct.pack(">I", len(meta_bytes))
    framed_input = header + meta_bytes + data

    command = [
        "wsl",
        "-d",
        "dtd-sandbox",
        "-u",
        "root",
        "--cd",
        "/opt/dtd",
        "--",
        "env",
        "PYTHONPATH=/opt/dtd/services/execution-broker/src",
        "python3",
        "scripts/sandbox-transform.py",
        "--image",
        image,
    ]

    result = subprocess.run(
        command, input=framed_input, capture_output=True, timeout=60, check=False
    )
    if result.returncode != 0 or len(result.stdout) < 4:
        raise RuntimeError("Isolated transformer failed or timed out")

    stdout = result.stdout
    (report_len,) = struct.unpack(">I", stdout[:4])
    if report_len > MAX_REPORT_JSON or len(stdout) < 4 + report_len:
        raise RuntimeError("Invalid report payload returned from transformer")

    report_json = stdout[4 : 4 + report_len].decode("utf-8")
    cleaned_csv_bytes = stdout[4 + report_len :]

    if len(cleaned_csv_bytes) > MAX_CLEANED_CSV:
        raise RuntimeError("Cleaned output exceeded size budget")

    report = CleaningReport.model_validate_json(report_json)

    # Validate output hash integrity if ready
    if report.status == "ready":
        computed_output_sha = hashlib.sha256(cleaned_csv_bytes).hexdigest()
        if report.output_sha256 != computed_output_sha:
            raise RuntimeError("Transformer output SHA-256 hash mismatch")

    return report, cleaned_csv_bytes
