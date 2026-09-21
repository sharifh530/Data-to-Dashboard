"""Real gVisor acceptance suite for dataset transformations.

Executes actual container under runsc; never executes generated code on host.
"""

import argparse
import hashlib
from pathlib import Path

from dtd_api.cleaning_generator import generate_cleaning_workflow
from dtd_api.inspection_contracts import ProfileReport
from dtd_api.inspections import run_isolated
from dtd_api.transformations import run_isolated_transform


def main() -> None:
    parser = argparse.ArgumentParser(description="Test isolated transformation under gVisor")
    parser.add_argument("--image", required=True, help="Pinned transformer image ID")
    parser.add_argument("--inspector-image", required=True, help="Pinned inspector image ID")
    args = parser.parse_args()

    sample_path = Path("samples/synthetic-sales-messy.csv")
    sample_bytes = sample_path.read_bytes()

    print("1. Profiling sample data via inspector...", flush=True)
    raw_profile = run_isolated(sample_bytes, "csv", args.inspector_image, ",", 0)
    profile = ProfileReport.model_validate_json(raw_profile)
    assert profile.status == "ready"
    assert profile.tables[0].row_count == 245

    print("2. Generating deterministic cleaning workflow...", flush=True)
    script, operations = generate_cleaning_workflow(profile)
    assert "clean_dataset" in script
    assert len(operations) > 0

    print("3. Executing isolated transformation in gVisor...", flush=True)
    report, cleaned_csv = run_isolated_transform(
        data=sample_bytes,
        file_format="csv",
        image=args.image,
        script=script,
        delimiter=",",
    )

    assert report.status == "ready", f"Expected ready, got {report.error}"
    assert report.summary is not None
    assert report.summary.original_rows == 245
    assert report.summary.cleaned_rows == 240  # 5 exact duplicate rows removed!
    assert report.summary.duplicate_rows_removed == 5
    assert len(cleaned_csv) > 0
    assert report.output_sha256 == hashlib.sha256(cleaned_csv).hexdigest()
    print(
        f"   Success: cleaned rows: {report.summary.cleaned_rows} "
        f"(removed {report.summary.duplicate_rows_removed} duplicates)",
        flush=True,
    )

    print("4. Testing rejection of failing script...", flush=True)
    failing_script = "def clean_dataset(df):\n    raise ValueError('Deliberate test failure')\n"
    rej_report, _ = run_isolated_transform(
        data=sample_bytes,
        file_format="csv",
        image=args.image,
        script=failing_script,
        delimiter=",",
    )
    assert rej_report.status == "rejected"
    assert rej_report.error == "SCRIPT_EXECUTION_FAILED"
    print("   Success: failing script safely rejected.", flush=True)

    print("5. Testing rejection of invalid return type...", flush=True)
    invalid_script = "def clean_dataset(df):\n    return 'not a dataframe', {}\n"
    inv_report, _ = run_isolated_transform(
        data=sample_bytes,
        file_format="csv",
        image=args.image,
        script=invalid_script,
        delimiter=",",
    )
    assert inv_report.status == "rejected"
    assert inv_report.error == "INVALID_SCRIPT_OUTPUT"
    print("   Success: invalid return type safely rejected.", flush=True)

    print("All transformer gVisor acceptance tests passed successfully!", flush=True)


if __name__ == "__main__":
    main()
