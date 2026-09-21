"""Contracts for bounded dataset cleaning and transformation provenance."""

from typing import Any, Literal

from pydantic import Field

from dtd_api.contracts import Contract


class CleaningOperation(Contract):
    """An individual recorded cleaning operation with rationale."""

    operation_type: Literal[
        "normalize_headers",
        "trim_whitespace",
        "replace_null_sentinels",
        "coerce_numeric",
        "drop_duplicate_rows",
    ]
    description: str = Field(max_length=256)
    target_columns: list[str] = Field(default_factory=list)
    rows_affected: int = Field(ge=0, default=0)
    details: dict[str, Any] = Field(default_factory=dict)


class ColumnLineage(Contract):
    """Lineage record tracking column names and type evolution."""

    original_name: str = Field(max_length=128)
    clean_name: str = Field(max_length=128)
    original_inferred_type: str = Field(max_length=32)
    clean_type: str = Field(max_length=32)
    null_count_before: int = Field(ge=0)
    null_count_after: int = Field(ge=0)


class CleaningSummary(Contract):
    """High-level metrics before and after cleaning."""

    original_rows: int = Field(ge=0)
    cleaned_rows: int = Field(ge=0)
    original_columns: int = Field(ge=0)
    cleaned_columns: int = Field(ge=0)
    duplicate_rows_removed: int = Field(ge=0)
    cells_modified: int = Field(ge=0, default=0)


class CleaningReport(Contract):
    """Complete provenance report produced by the cleaning execution."""

    schema_version: Literal["1"] = "1"
    status: Literal["ready", "rejected", "failed"]
    input_sha256: str = Field(max_length=64)
    output_sha256: str | None = Field(default=None, max_length=64)
    summary: CleaningSummary | None = None
    operations: list[CleaningOperation] = Field(default_factory=list)
    lineage: list[ColumnLineage] = Field(default_factory=list)
    generated_code: str | None = None
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
