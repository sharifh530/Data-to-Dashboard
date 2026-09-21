"""Unit tests for deterministic cleaning code generation and contracts."""

import ast

from dtd_api.cleaning_contracts import (
    CleaningOperation,
    CleaningReport,
    CleaningSummary,
    ColumnLineage,
)
from dtd_api.cleaning_generator import generate_cleaning_workflow, safe_identifier
from dtd_api.inspection_contracts import ColumnProfile, ProfileReport, ProfileTable, TopValue


def sample_profile_report() -> ProfileReport:
    columns = [
        ColumnProfile(
            name="Order ID",
            distinct=1,
            numeric_count=0,
            nonnumeric_count=1,
            numeric_min=None,
            numeric_max=None,
            top_values=[TopValue(value="ORD-001", count=1)],
        ),
        ColumnProfile(
            name="Total Amount ($)",
            distinct=1,
            numeric_count=1,
            nonnumeric_count=0,
            numeric_min="100.00",
            numeric_max="100.00",
            top_values=[TopValue(value="100.00", count=1)],
        ),
        ColumnProfile(
            name="Customer Status",
            distinct=1,
            numeric_count=0,
            nonnumeric_count=1,
            numeric_min=None,
            numeric_max=None,
            top_values=[TopValue(value="Active", count=1)],
        ),
    ]
    table = ProfileTable(
        name="sales",
        columns=["Order ID", "Total Amount ($)", "Customer Status"],
        row_count=1,
        missing=[0, 0, 0],
        preview=[["ORD-001", "100.00", "Active"]],
        profile=columns,
    )
    return ProfileReport(
        schema_version="1",
        sha256="0" * 64,
        format="csv",
        status="ready",
        tables=[table],
        warnings=[],
        delimiter=",",
        error=None,
    )


def test_safe_identifier_generation():
    existing: set[str] = set()
    assert safe_identifier("Order ID", 0, existing) == "order_id"
    assert safe_identifier("Order ID", 1, existing) == "order_id_2"
    assert safe_identifier("123 Numerical Start", 2, existing) == "col_123_numerical_start"
    assert safe_identifier("Special!@#$%Chars", 3, existing) == "specialchars"


def test_generate_cleaning_workflow_produces_valid_python():
    profile = sample_profile_report()
    code, operations = generate_cleaning_workflow(profile)

    # 1. Ensure valid Python AST
    parsed = ast.parse(code)
    assert isinstance(parsed, ast.Module)

    # 2. Check function clean_dataset exists in AST
    funcs = [n.name for n in parsed.body if isinstance(n, ast.FunctionDef)]
    assert "clean_dataset" in funcs

    # 3. Check expected operations were planned
    op_types = [op.operation_type for op in operations]
    assert "normalize_headers" in op_types
    assert "drop_duplicate_rows" in op_types
    assert "replace_null_sentinels" in op_types
    assert "trim_whitespace" in op_types
    assert "coerce_numeric" in op_types


def test_cleaning_contracts_serialization():
    report = CleaningReport(
        schema_version="1",
        status="ready",
        input_sha256="a" * 64,
        output_sha256="b" * 64,
        summary=CleaningSummary(
            original_rows=245,
            cleaned_rows=240,
            original_columns=3,
            cleaned_columns=3,
            duplicate_rows_removed=5,
        ),
        operations=[
            CleaningOperation(
                operation_type="drop_duplicate_rows",
                description="Removed duplicate rows",
                target_columns=[],
                rows_affected=5,
            )
        ],
        lineage=[
            ColumnLineage(
                original_name="Order ID",
                clean_name="order_id",
                original_inferred_type="string",
                clean_type="string",
                null_count_before=0,
                null_count_after=0,
            )
        ],
        generated_code="import pandas as pd",
        warnings=[],
    )
    json_str = report.model_dump_json()
    restored = CleaningReport.model_validate_json(json_str)
    assert restored.summary.duplicate_rows_removed == 5
    assert restored.operations[0].operation_type == "drop_duplicate_rows"
