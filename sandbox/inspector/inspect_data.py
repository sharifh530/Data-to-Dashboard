"""Reviewed parser; execute ONLY inside gVisor. Input bytes arrive over stdin."""

import csv
import hashlib
import io
import json
import sqlite3
import sys
import time
from pathlib import Path

MAX_INPUT = 10 * 1024 * 1024


class Rejected(Exception):
    pass


def table_report(name, columns, rows):
    if not columns or len(columns) > 64 or any(len(str(col)) > 128 for col in columns):
        raise Rejected("COLUMN_LIMIT")
    preview = []
    count = 0
    missing = [0] * len(columns)
    for row in rows:
        count += 1
        if count > 100000:
            raise Rejected("ROW_LIMIT")
        if len(row) != len(columns):
            raise Rejected("INCONSISTENT_ROW_WIDTH")
        for i, value in enumerate(row):
            if value is None or value == "":
                missing[i] += 1
            if isinstance(value, (str, bytes)) and len(value) > 65536:
                raise Rejected("CELL_LIMIT")
        if count <= 5:
            preview.append(
                [
                    None
                    if value is None
                    else f"[BLOB: {len(value)} bytes]"
                    if isinstance(value, bytes)
                    else str(value)[:128]
                    for value in row
                ]
            )
    return {
        "name": name,
        "columns": [str(col) for col in columns],
        "row_count": count,
        "missing": missing,
        "preview": preview,
    }


def inspect_csv(data, override=None):
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise Rejected("UTF8_REQUIRED") from error
    if "\x00" in text:
        raise Rejected("NUL_BYTE")
    csv.field_size_limit(65536)
    if override:
        delimiter = override
    else:
        try:
            delimiter = csv.Sniffer().sniff(text[:32768], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    columns = next(reader, None)
    if columns is None:
        raise Rejected("EMPTY_FILE")
    warnings = []
    if len(set(columns)) != len(columns) or any(not col.strip() for col in columns):
        warnings.append("DUPLICATE_OR_EMPTY_HEADERS")
    result = table_report("CSV", columns, reader)
    if result["row_count"] == 0:
        warnings.append("EMPTY_TABLE")
    return [result], warnings, delimiter


def inspect_sqlite(data):
    if not data.startswith(b"SQLite format 3\x00"):
        raise Rejected("SQLITE_HEADER")
    path = Path("/tmp/input.sqlite")
    path.write_bytes(data)
    db = sqlite3.connect("file:/tmp/input.sqlite?mode=ro&immutable=1", uri=True, timeout=1)
    try:
        db.enable_load_extension(False)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 65536)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 32768)
        deadline = time.monotonic() + 10
        db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        if db.execute("PRAGMA quick_check(1)").fetchone() != ("ok",):
            raise Rejected("SQLITE_INTEGRITY")
        entries = db.execute("PRAGMA table_list").fetchall()
        names = sorted(
            row[1]
            for row in entries
            if row[0] == "main" and row[2] == "table" and not row[1].startswith("sqlite_")
        )
        if not names or len(names) > 10 or any(len(name) > 128 for name in names):
            raise Rejected("TABLE_LIMIT_OR_NO_ORDINARY_TABLES")
        reports = []
        for name in names:
            quoted = '"' + name.replace('"', '""') + '"'
            info = db.execute(f"PRAGMA table_xinfo({quoted})").fetchall()
            if any(col[6] != 0 for col in info):
                raise Rejected("GENERATED_OR_HIDDEN_COLUMNS")
            columns = [col[1] for col in info]

            def authorize(action, arg1, _arg2, _database, _source, current=name):
                if action == sqlite3.SQLITE_SELECT:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_READ and arg1 == current:
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            db.set_authorizer(authorize)
            selection = ",".join('"' + col.replace('"', '""') + '"' for col in columns)
            reports.append(
                table_report(
                    name, columns, db.execute(f"SELECT {selection} FROM {quoted} LIMIT 100001")
                )
            )
            db.set_authorizer(None)
        return reports, ["PREVIEW_ORDER_NOT_GUARANTEED"], None
    finally:
        db.close()


def main():
    if len(sys.argv) not in {2, 3} or (
        len(sys.argv) == 3 and sys.argv[2] not in {",", ";", "\t", "|"}
    ):
        raise SystemExit(2)
    data = sys.stdin.buffer.read(MAX_INPUT + 1)
    sha = hashlib.sha256(data).hexdigest()
    result = {"schema_version": "1", "sha256": sha, "format": sys.argv[1]}
    try:
        if not data or len(data) > MAX_INPUT:
            raise Rejected("INPUT_SIZE")
        if sys.argv[1] == "csv":
            tables, warnings, delimiter = inspect_csv(
                data, sys.argv[2] if len(sys.argv) == 3 else None
            )
        elif sys.argv[1] == "sqlite":
            tables, warnings, delimiter = inspect_sqlite(data)
        else:
            raise Rejected("FORMAT")
        result.update(
            status="ready", tables=tables, warnings=warnings, delimiter=delimiter, error=None
        )
    except (Rejected, csv.Error, sqlite3.Error, ValueError, OverflowError) as error:
        code = str(error) if isinstance(error, Rejected) else "MALFORMED_OR_UNSUPPORTED_DATA"
        result.update(status="rejected", tables=[], warnings=[], delimiter=None, error=code)
    encoded = json.dumps(result, ensure_ascii=True).encode()
    if len(encoded) > 524288:
        result.update(
            status="rejected", tables=[], warnings=[], delimiter=None, error="RESULT_LIMIT"
        )
    print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
