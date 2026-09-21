"""Deterministic Dashboard Specification generator conforming to spec v1."""

from typing import Any

from dtd_api.baseline_contracts import BaselineReport
from dtd_api.cleaning_contracts import CleaningReport
from dtd_api.dashboard_contracts import (
    ChartSpec,
    DashboardSpec,
    FilterSpec,
    KpiSpec,
    TableSpec,
)
from dtd_api.inspection_contracts import ColumnProfile, ProfileReport


def generate_dashboard_spec(
    dataset_version_id: str,
    profile_report: ProfileReport,
    cleaning_report: CleaningReport | dict[str, Any],
    baseline_report: BaselineReport | dict[str, Any] | None = None,
    target_column: str | None = None,
) -> DashboardSpec:
    """Generate a validated DashboardSpec v1 based on profiling and transformation outcomes."""
    # Normalize cleaning report
    if isinstance(cleaning_report, dict):
        cleaning_obj = CleaningReport.model_validate(cleaning_report)
    else:
        cleaning_obj = cleaning_report

    # Normalize baseline report
    baseline_obj: BaselineReport | None = None
    if baseline_report is not None:
        if isinstance(baseline_report, dict):
            baseline_obj = BaselineReport.model_validate(baseline_report)
        else:
            baseline_obj = baseline_report

    clean_columns = [col.clean_name for col in cleaning_obj.lineage]
    original_columns = [col.original_name for col in cleaning_obj.lineage]

    # Map column profiles by clean name
    col_profiles: dict[str, ColumnProfile] = {}
    table = profile_report.tables[0] if profile_report.tables else None
    col_list = table.profile if table else []
    for orig, clean in zip(original_columns, clean_columns, strict=False):
        for cp in col_list:
            if cp.name == orig:
                col_profiles[clean] = cp
                break

    cleaned_rows = (
        cleaning_obj.summary.cleaned_rows
        if cleaning_obj.summary
        else (table.row_count if table else 0)
    )
    dup_removed = cleaning_obj.summary.duplicate_rows_removed if cleaning_obj.summary else 0
    cells_mod = cleaning_obj.summary.cells_modified if cleaning_obj.summary else 0

    # 1. KPIs (max 6)
    kpis: list[KpiSpec] = [
        KpiSpec(
            id="kpi_rows",
            label="Cleaned Rows",
            value=cleaned_rows,
            format="number",
            description="Verified row count after cleaning",
        ),
        KpiSpec(
            id="kpi_cols",
            label="Total Features",
            value=len(clean_columns),
            format="number",
            description="Active columns available for analysis",
        ),
        KpiSpec(
            id="kpi_dups",
            label="Duplicates Removed",
            value=dup_removed,
            format="number",
            description="Identical rows removed during cleaning",
        ),
    ]

    if cells_mod > 0 and len(kpis) < 6:
        kpis.append(
            KpiSpec(
                id="kpi_mod",
                label="Values Cleaned",
                value=cells_mod,
                format="number",
                description="Whitespace stripped or sentinels coerced",
            )
        )

    if baseline_obj and baseline_obj.status == "ready" and len(kpis) < 6:
        if baseline_obj.candidate:
            cand = baseline_obj.candidate
            if baseline_obj.task_type == "regression" and cand.mae is not None:
                kpis.append(
                    KpiSpec(
                        id="kpi_model_perf",
                        label=f"{cand.model_name.title()} MAE",
                        value=round(cand.mae, 2),
                        format="number",
                        description="Test set mean absolute error of baseline candidate",
                    )
                )
            elif baseline_obj.task_type == "classification" and cand.macro_f1 is not None:
                kpis.append(
                    KpiSpec(
                        id="kpi_model_perf",
                        label=f"{cand.model_name.title()} F1",
                        value=round(cand.macro_f1, 3),
                        format="percent",
                        description="Macro-averaged F1 score on test split",
                    )
                )

    if target_column and target_column in col_profiles and len(kpis) < 6:
        t_prof = col_profiles[target_column]
        if t_prof.numeric_count > 0:
            kpis.append(
                KpiSpec(
                    id="kpi_target",
                    label=f"Target: {target_column}",
                    value=f"Range: {t_prof.numeric_min or '0'} - {t_prof.numeric_max or '0'}",
                    format="text",
                    description="Modeling target column interval",
                )
            )

    # 2. Charts (max 6)
    charts: list[ChartSpec] = []

    # Detect date column if present (never fabricated)
    date_col = None
    for c in clean_columns:
        if any(token in c.lower() for token in ("date", "time", "day", "month", "year")):
            date_col = c
            break

    if date_col:
        charts.append(
            ChartSpec(
                id=f"chart_line_{date_col}",
                title=f"Trend over {date_col.replace('_', ' ').title()}",
                chart_type="line",
                query_id=f"line_{date_col}",
                x_axis=date_col,
                y_axis="count",
                summary=f"Chronological event count across {date_col}",
            )
        )

    # Add Bar charts for low-cardinality categorical columns
    for c in clean_columns:
        if len(charts) >= 6:
            break
        if c == date_col:
            continue
        c_prof = col_profiles.get(c)
        if not c_prof:
            continue
        is_cat = 2 <= c_prof.distinct <= 20
        if is_cat and c_prof.nonnumeric_count >= c_prof.numeric_count:
            charts.append(
                ChartSpec(
                    id=f"chart_bar_{c}",
                    title=f"Distribution by {c.replace('_', ' ').title()}",
                    chart_type="bar",
                    query_id=f"bar_{c}",
                    x_axis=c,
                    y_axis="count",
                    summary=f"Frequency counts grouped by {c}",
                )
            )

    # Add Histogram charts for numeric columns
    numeric_cols = []
    for c in clean_columns:
        n_prof = col_profiles.get(c)
        if n_prof and n_prof.numeric_count > n_prof.nonnumeric_count:
            numeric_cols.append(c)

    for c in numeric_cols:
        if len(charts) >= 6:
            break
        charts.append(
            ChartSpec(
                id=f"chart_hist_{c}",
                title=f"{c.replace('_', ' ').title()} Distribution",
                chart_type="histogram",
                query_id=f"hist_{c}",
                x_axis=c,
                y_axis="frequency",
                summary=f"Binned distribution of values for {c}",
            )
        )

    # Add Scatter chart if target is numeric and another numeric column exists
    if target_column and target_column in numeric_cols and len(charts) < 6:
        other_nums = [c for c in numeric_cols if c != target_column]
        if other_nums:
            x_col = other_nums[0]
            x_title = x_col.replace("_", " ").title()
            tgt_title = target_column.replace("_", " ").title()
            charts.append(
                ChartSpec(
                    id=f"chart_scatter_{x_col}_{target_column}",
                    title=f"{x_title} vs {tgt_title}",
                    chart_type="scatter",
                    query_id=f"scatter_{x_col}_{target_column}",
                    x_axis=x_col,
                    y_axis=target_column,
                    summary=f"Correlation comparison between {x_col} and {target_column}",
                )
            )

    # 3. Filters (max 4)
    filters: list[FilterSpec] = []
    for c in clean_columns:
        if len(filters) >= 4:
            break
        f_prof = col_profiles.get(c)
        if not f_prof:
            continue
        if 2 <= f_prof.distinct <= 20 and f_prof.nonnumeric_count >= f_prof.numeric_count:
            opts = [tv.value for tv in f_prof.top_values if tv.value]
            filters.append(
                FilterSpec(
                    column=c,
                    label=c.replace("_", " ").title(),
                    type="category",
                    allowed_operators=["in", "eq"],
                    options=opts,
                )
            )

    # If space remains, add numeric range filters
    for c in numeric_cols:
        if len(filters) >= 4:
            break
        if any(f.column == c for f in filters):
            continue
        r_prof = col_profiles.get(c)
        if r_prof and r_prof.numeric_min is not None and r_prof.numeric_max is not None:
            try:
                min_v = float(r_prof.numeric_min)
                max_v = float(r_prof.numeric_max)
                filters.append(
                    FilterSpec(
                        column=c,
                        label=c.replace("_", " ").title(),
                        type="range",
                        allowed_operators=["between", "gte", "lte"],
                        min_val=min_v,
                        max_val=max_v,
                    )
                )
            except (ValueError, TypeError):
                continue

    # 4. Table Spec
    table_spec = TableSpec(
        columns=clean_columns[:10],
        page_size=50,
        default_sort=clean_columns[0] if clean_columns else None,
        sort_direction="asc",
    )

    # 5. Warnings
    warnings = list(cleaning_obj.warnings)
    if baseline_obj:
        warnings.extend(baseline_obj.warnings)
        if baseline_obj.status == "skipped" and baseline_obj.skip_reason:
            warnings.append(f"Baseline skipped: {baseline_obj.skip_reason}")

    # Summary
    summary_parts = [f"Analyzed {cleaned_rows} rows across {len(clean_columns)} columns."]
    if dup_removed > 0:
        summary_parts.append(f"Removed {dup_removed} duplicate records.")
    if baseline_obj and baseline_obj.status == "ready":
        cand_name = baseline_obj.candidate.model_name if baseline_obj.candidate else "Candidate"
        summary_parts.append(
            f"Trained baseline {cand_name} model for {baseline_obj.task_type} "
            f"on '{baseline_obj.target_column}'."
        )

    return DashboardSpec(
        schema_version="1",
        dataset_version_id=dataset_version_id,
        title="Dataset Analysis Dashboard",
        summary=" ".join(summary_parts),
        kpis=kpis,
        charts=charts,
        filters=filters,
        table=table_spec,
        warnings=warnings,
        model_report_ref=None,
    )
