"""Deterministic cleaning plan and Pandas code generator."""

import ast
import re

from dtd_api.cleaning_contracts import CleaningOperation
from dtd_api.inspection_contracts import ProfileReport


def safe_identifier(name: str, index: int, existing: set[str]) -> str:
    """Derive a clean, safe, unique snake_case column name."""
    clean = re.sub(r"[^\w\s-]", "", name).strip().lower()
    clean = re.sub(r"[-\s]+", "_", clean)
    clean = clean[:64]
    if not clean or not clean[0].isalpha():
        clean = f"col_{clean}" if clean else f"col_{index + 1}"
    candidate = clean
    suffix = 2
    while candidate in existing:
        candidate = f"{clean}_{suffix}"
        suffix += 1
    existing.add(candidate)
    return candidate


def generate_cleaning_workflow(
    profile_report: ProfileReport,
) -> tuple[str, list[CleaningOperation]]:
    """Analyze profile report and generate deterministic Pandas code and operations list."""
    if not profile_report.tables:
        raise ValueError("ProfileReport has no tables")
    columns = profile_report.tables[0].profile
    existing_identifiers: set[str] = set()
    rename_mapping: dict[str, str] = {}
    rename_needed = False

    for idx, col in enumerate(columns):
        clean_name = safe_identifier(col.name, idx, existing_identifiers)
        rename_mapping[col.name] = clean_name
        if clean_name != col.name:
            rename_needed = True

    operations: list[CleaningOperation] = []

    # 1. Header normalization operation
    if rename_needed:
        operations.append(
            CleaningOperation(
                operation_type="normalize_headers",
                description="Standardize column names to lower_snake_case.",
                target_columns=list(rename_mapping.keys()),
                details={"rename_mapping": rename_mapping},
            )
        )

    # 2. Duplicate row removal operation
    operations.append(
        CleaningOperation(
            operation_type="drop_duplicate_rows",
            description="Identify and remove exact duplicate rows across all columns.",
            target_columns=[],
            details={},
        )
    )

    # 3. Null sentinel replacement
    operations.append(
        CleaningOperation(
            operation_type="replace_null_sentinels",
            description="Replace text sentinels ('N/A', 'NA', 'null', 'None') with nulls.",
            target_columns=[rename_mapping[c.name] for c in columns],
            details={
                "sentinels": ["N/A", "NA", "n/a", "na", "null", "NULL", "None", "none", "?", "-"]
            },
        )
    )

    # 4. Whitespace trimming
    operations.append(
        CleaningOperation(
            operation_type="trim_whitespace",
            description="Strip leading and trailing whitespace from text fields.",
            target_columns=[rename_mapping[c.name] for c in columns if c.nonnumeric_count > 0],
            details={},
        )
    )

    # 5. Numeric coercion
    numeric_coercion_cols = [
        rename_mapping[c.name]
        for c in columns
        if c.numeric_count > 0 and c.numeric_count >= c.nonnumeric_count
    ]
    if numeric_coercion_cols:
        operations.append(
            CleaningOperation(
                operation_type="coerce_numeric",
                description="Coerce numeric-predominant columns to numeric type.",
                target_columns=numeric_coercion_cols,
                details={"coercion_columns": numeric_coercion_cols},
            )
        )

    # Build the Python script
    code_lines = [
        '"""Generated cleaning script with transformation provenance.',
        "Execute ONLY inside an isolated gVisor runtime.",
        '"""',
        "",
        "import numpy as np",
        "import pandas as pd",
        "",
        "",
        "def clean_dataset(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:",
        "    initial_rows, initial_cols = df.shape",
        "    recorded_operations = []",
        "",
    ]

    # Code: Normalize headers
    if rename_needed:
        code_lines.extend(
            [
                "    # 1. Normalize column headers",
                f"    rename_mapping = {repr(rename_mapping)}",
                "    df = df.rename(columns=rename_mapping)",
                "    recorded_operations.append({",
                '        "operation_type": "normalize_headers",',
                '        "description": "Standardized headers to snake_case.",',
                '        "target_columns": list(rename_mapping.keys()),',
                '        "rows_affected": 0,',
                "    })",
                "",
            ]
        )

    # Code: Drop duplicates
    code_lines.extend(
        [
            "    # 2. Drop exact duplicate rows",
            "    before_dup_count = len(df)",
            "    df = df.drop_duplicates()",
            "    dup_removed = before_dup_count - len(df)",
            "    recorded_operations.append({",
            '        "operation_type": "drop_duplicate_rows",',
            '        "description": "Removed exact duplicate rows.",',
            '        "target_columns": list(df.columns),',
            '        "rows_affected": dup_removed,',
            "    })",
            "",
        ]
    )

    # Code: Replace null sentinels
    code_lines.extend(
        [
            "    # 3. Replace text null sentinels",
            '    sentinels = ["N/A", "NA", "n/a", "na", "null", "NULL", "None", "none", "?"]',
            "    df = df.replace(sentinels, np.nan).replace('', np.nan)",
            "    recorded_operations.append({",
            '        "operation_type": "replace_null_sentinels",',
            '        "description": "Replaced text null sentinels with NaN.",',
            '        "target_columns": list(df.columns),',
            '        "rows_affected": 0,',
            "    })",
            "",
        ]
    )

    # Code: Trim whitespace on string columns
    code_lines.extend(
        [
            "    # 4. Strip whitespace from string columns",
            "    trimmed_cols = []",
            "    for col in df.select_dtypes(include=['object', 'string']).columns:",
            "        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)",
            "        trimmed_cols.append(col)",
            "    recorded_operations.append({",
            '        "operation_type": "trim_whitespace",',
            '        "description": "Stripped leading/trailing whitespace.",',
            '        "target_columns": trimmed_cols,',
            '        "rows_affected": 0,',
            "    })",
            "",
        ]
    )

    # Code: Coerce numeric columns
    if numeric_coercion_cols:
        code_lines.extend(
            [
                "    # 5. Coerce numeric columns",
                f"    numeric_cols = {repr(numeric_coercion_cols)}",
                "    for col in numeric_cols:",
                "        if col in df.columns:",
                "            # Strip currency signs or comma separators if strings",
                "            cleaned = df[col].astype(str).str.replace(r'[$£€,]', '', regex=True)",
                "            df[col] = pd.to_numeric(cleaned, errors='coerce')",
                "    recorded_operations.append({",
                '        "operation_type": "coerce_numeric",',
                '        "description": "Coerced columns to numeric.",',
                '        "target_columns": numeric_cols,',
                '        "rows_affected": 0,',
                "    })",
                "",
            ]
        )

    # Code: Summary and Lineage
    code_lines.extend(
        [
            "    # Compute summary & lineage",
            "    final_rows, final_cols = df.shape",
            "    summary = {",
            '        "original_rows": initial_rows,',
            '        "cleaned_rows": final_rows,',
            '        "original_columns": initial_cols,',
            '        "cleaned_columns": final_cols,',
            '        "duplicate_rows_removed": dup_removed,',
            "    }",
            "    return df, {",
            '        "summary": summary,',
            '        "operations": recorded_operations,',
            "    }",
            "",
        ]
    )

    generated_code = "\n".join(code_lines)

    # Validate AST to ensure valid Python syntax
    ast.parse(generated_code)

    return generated_code, operations
