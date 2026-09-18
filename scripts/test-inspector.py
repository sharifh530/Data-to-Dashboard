"""Real gVisor acceptance; construct synthetic fixtures, never parse uploads on the host."""

import argparse
import hashlib
import sqlite3
from pathlib import Path

from dtd_api.inspection_contracts import InspectionReport, ProfileReport
from dtd_api.inspections import run_isolated

parser = argparse.ArgumentParser()
parser.add_argument("--image", required=True)
args = parser.parse_args()


def inspect(data, file_format="csv", delimiter=None):
    report = InspectionReport.model_validate_json(
        run_isolated(data, file_format, args.image, delimiter)
    )
    assert report.sha256 == hashlib.sha256(data).hexdigest()
    return report


sample = inspect(Path("samples/synthetic-sales-messy.csv").read_bytes())
assert sample.status == "ready" and sample.tables[0].row_count == 245
assert len(sample.tables[0].columns) == 11 and len(sample.tables[0].preview) == 5
sample_bytes = Path("samples/synthetic-sales-messy.csv").read_bytes()
profile = ProfileReport.model_validate_json(run_isolated(sample_bytes, "csv", args.image, ",", 0))
assert profile.status == "ready" and profile.tables[0].row_count == 245
assert len(profile.tables[0].profile) == 11
assert profile.tables[0].profile[0].distinct <= 245
for data in [
    b"\xff",
    b"a\x00b",
    b'a,b\n"unterminated',
    b"a,b\n1,2,3\n",
    b"a\n" + b"x" * 70000,
    b",".join([b"a"] * 65) + b"\n",
]:
    assert inspect(data).status == "rejected"
assert inspect(b"a,a\n001,2\n").warnings == ["DUPLICATE_OR_EMPTY_HEADERS"]
assert inspect(b"a;b\n001;2\n").tables[0].preview[0][0] == "001"
forced = inspect(b"a;b\n001;2\n", delimiter=";")
assert forced.delimiter == ";" and forced.tables[0].columns == ["a", "b"]
assert inspect(b"a|b\n001|2\n", delimiter="|").tables[0].preview == [["001", "2"]]
assert inspect(b"a\n").tables[0].row_count == 0
assert inspect(b"a\n" + b"x\n" * 100001).status == "rejected"
db = sqlite3.connect(":memory:")
db.execute('CREATE TABLE "sales" ("<script>alert(1)</script>" TEXT, amount INTEGER)')
db.execute("INSERT INTO sales VALUES ('001', 42)")
db.execute("CREATE TABLE empty_table (value TEXT)")
db.execute("CREATE VIEW untrusted_view AS SELECT load_extension('must-not-load')")
database = db.serialize()
db.close()
report = inspect(database, "sqlite")
assert report.status == "ready", report.error
assert {table.name for table in report.tables} == {"sales", "empty_table"}
assert next(table for table in report.tables if table.name == "sales").preview == [["001", "42"]]
sql_profile = ProfileReport.model_validate_json(
    run_isolated(database, "sqlite", args.image, profile_index=1)
)
assert sql_profile.tables[0].name == "sales"
assert sql_profile.tables[0].profile[1].numeric_min == "42"
assert inspect(b"not a database", "sqlite").status == "rejected"
assert inspect(b"SQLite format 3\x00" + b"x" * 1024, "sqlite").status == "rejected"
for definitions in [
    [f"CREATE TABLE t{i} (v TEXT)" for i in range(11)],
    ["CREATE TABLE t (v INTEGER, generated INTEGER GENERATED ALWAYS AS (v + 1))"],
]:
    db = sqlite3.connect(":memory:")
    for definition in definitions:
        db.execute(definition)
    database = db.serialize()
    db.close()
    assert inspect(database, "sqlite").status == "rejected"
print("20 isolated inspector/profile cases passed; no uploaded file parsed on host.")
