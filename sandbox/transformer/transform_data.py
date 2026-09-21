"""Reviewed data transformer; executes ONLY inside gVisor.

Input bytes arrive over stdin using binary framing:
- 4 bytes big-endian: length of JSON metadata header (format, delimiter, table, script)
- JSON metadata bytes
- Remaining bytes: raw input data

Output over stdout using binary framing:
- 4 bytes big-endian: length of JSON CleaningReport
- JSON CleaningReport bytes
- Remaining bytes: cleaned CSV data
"""

import hashlib
import io
import json
import sqlite3
import struct
import sys
from typing import Any

MAX_INPUT = 10 * 1024 * 1024
MAX_METADATA = 64 * 1024
MAX_CLEANED_OUTPUT = 15 * 1024 * 1024


class TransformError(Exception):
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


def run_transformation(
    raw_data: bytes,
    file_format: str,
    delimiter: str | None,
    table_name: str | None,
    script: str,
) -> tuple[dict[str, Any], bytes]:
    import numpy as np
    import pandas as pd

    input_sha = hashlib.sha256(raw_data).hexdigest()

    # 1. Load DataFrame safely
    if file_format == "csv":
        try:
            text = raw_data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise TransformError(
                "UTF8_REQUIRED", "CSV must be valid UTF-8") from exc
        if "\x00" in text:
            raise TransformError("NUL_BYTE", "NUL bytes are forbidden")
        delim = delimiter or ","
        df = pd.read_csv(io.StringIO(text), delimiter=delim, dtype=str)
    elif file_format == "sqlite":
        if not raw_data.startswith(b"SQLite format 3\x00"):
            raise TransformError("SQLITE_HEADER", "Invalid SQLite header")
        db_path = "/tmp/transform_input.sqlite"
        with open(db_path, "wb") as f:
            f.write(raw_data)
        conn = sqlite3.connect(f"file:{db_path}?mode=ro&immutable=1", uri=True)
        try:
            conn.execute("PRAGMA query_only=ON")
            if not table_name:
                raise TransformError("MISSING_TABLE_NAME",
                                     "Table name required for SQLite")
            quoted_table = '"' + table_name.replace('"', '""') + '"'
            df = pd.read_sql_query(
                f"SELECT * FROM {quoted_table}", conn, dtype=str)
        finally:
            conn.close()
    else:
        raise TransformError("UNSUPPORTED_FORMAT",
                             f"Format {file_format} is not supported")

    original_rows, original_cols = df.shape
    if original_rows > 100000 or original_cols > 64:
        raise TransformError("DATA_LIMITS_EXCEEDED",
                             "Input exceeds row or column limits")

    orig_columns = list(df.columns)
    orig_nulls = {str(c): int(df[c].isna().sum()) for c in orig_columns}

    # 2. Execute script in isolated namespace
    namespace: dict[str, Any] = {"pd": pd, "np": np}

    try:
        compiled = compile(script, "<generated_cleaner>", "exec")
        exec(compiled, namespace)  # noqa: S102
        clean_fn = namespace.get("clean_dataset")
        if not callable(clean_fn):
            raise TransformError("MISSING_CLEAN_FUNCTION",
                                 "clean_dataset function not found")
        cleaned_df, report_meta = clean_fn(df)
    except Exception as exc:
        raise TransformError("SCRIPT_EXECUTION_FAILED", str(exc)) from exc

    if not isinstance(cleaned_df, pd.DataFrame):
        raise TransformError(
            "INVALID_SCRIPT_OUTPUT", "clean_dataset must return a pandas DataFrame"
        )

    cleaned_rows, cleaned_cols = cleaned_df.shape
    if len(cleaned_df) > 100000 or cleaned_cols > 64:
        raise TransformError("OUTPUT_LIMITS_EXCEEDED",
                             "Cleaned output exceeds allowed dimensions")

    # 3. Build Column Lineage
    lineage = []
    clean_columns = list(cleaned_df.columns)
    for i, col in enumerate(clean_columns):
        orig_name = orig_columns[i] if i < len(orig_columns) else str(col)
        lineage.append(
            {
                "original_name": str(orig_name)[:128],
                "clean_name": str(col)[:128],
                "original_inferred_type": "string",
                "clean_type": str(cleaned_df[col].dtype)[:32],
                "null_count_before": orig_nulls.get(orig_name, 0),
                "null_count_after": int(cleaned_df[col].isna().sum()),
            }
        )

    # 4. Serialize cleaned CSV
    csv_buffer = io.StringIO()
    cleaned_df.to_csv(csv_buffer, index=False)
    cleaned_csv_bytes = csv_buffer.getvalue().encode("utf-8")

    if len(cleaned_csv_bytes) > MAX_CLEANED_OUTPUT:
        raise TransformError("OUTPUT_SIZE_EXCEEDED",
                             "Cleaned CSV exceeds maximum byte budget")

    output_sha = hashlib.sha256(cleaned_csv_bytes).hexdigest()

    summary = {
        "original_rows": original_rows,
        "cleaned_rows": cleaned_rows,
        "original_columns": original_cols,
        "cleaned_columns": cleaned_cols,
        "duplicate_rows_removed": original_rows - cleaned_rows,
        "cells_modified": 0,
    }

    report = {
        "schema_version": "1",
        "status": "ready",
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "summary": summary,
        "operations": report_meta.get("operations", []),
        "lineage": lineage,
        "warnings": [],
        "error": None,
    }

    return report, cleaned_csv_bytes


def main() -> None:
    stdin_buffer = sys.stdin.buffer

    # Read 4-byte metadata header length
    header_len_bytes = stdin_buffer.read(4)
    if len(header_len_bytes) < 4:
        raise SystemExit(2)
    (meta_len,) = struct.unpack(">I", header_len_bytes)
    if meta_len > MAX_METADATA:
        raise SystemExit(2)

    meta_bytes = stdin_buffer.read(meta_len)
    if len(meta_bytes) < meta_len:
        raise SystemExit(2)

    meta = json.loads(meta_bytes.decode("utf-8"))
    file_format = meta.get("format", "csv")
    delimiter = meta.get("delimiter")
    table_name = meta.get("table")
    script = meta.get("script", "")

    raw_data = stdin_buffer.read(MAX_INPUT + 1)
    if not raw_data or len(raw_data) > MAX_INPUT:
        report = {
            "schema_version": "1",
            "status": "rejected",
            "input_sha256": hashlib.sha256(raw_data).hexdigest(),
            "output_sha256": None,
            "summary": None,
            "operations": [],
            "lineage": [],
            "warnings": [],
            "error": "INPUT_SIZE_LIMIT",
        }
        report_bytes = json.dumps(report).encode("utf-8")
        sys.stdout.buffer.write(struct.pack(
            ">I", len(report_bytes)) + report_bytes)
        return

    try:
        report, cleaned_csv_bytes = run_transformation(
            raw_data=raw_data,
            file_format=file_format,
            delimiter=delimiter,
            table_name=table_name,
            script=script,
        )
    except TransformError as err:
        report = {
            "schema_version": "1",
            "status": "rejected",
            "input_sha256": hashlib.sha256(raw_data).hexdigest(),
            "output_sha256": None,
            "summary": None,
            "operations": [],
            "lineage": [],
            "warnings": [str(err)[:100]] if str(err) else [],
            "error": err.code,
        }
        cleaned_csv_bytes = b""
    except Exception:
        report = {
            "schema_version": "1",
            "status": "failed",
            "input_sha256": hashlib.sha256(raw_data).hexdigest(),
            "output_sha256": None,
            "summary": None,
            "operations": [],
            "lineage": [],
            "warnings": [],
            "error": "UNEXPECTED_TRANSFORM_ERROR",
        }
        cleaned_csv_bytes = b""

    report_bytes = json.dumps(report).encode("utf-8")
    header = struct.pack(">I", len(report_bytes))
    sys.stdout.buffer.write(header + report_bytes + cleaned_csv_bytes)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
