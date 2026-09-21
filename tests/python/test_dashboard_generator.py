"""Tests for deterministic dashboard specification generation."""

from dtd_api.baseline_contracts import (
    BaselineComparison,
    BaselineReport,
    ModelMetrics,
    SplitInfo,
)
from dtd_api.cleaning_contracts import CleaningReport, CleaningSummary, ColumnLineage
from dtd_api.dashboard_contracts import DashboardSpec
from dtd_api.dashboard_generator import generate_dashboard_spec
from dtd_api.inspection_contracts import (
    ColumnProfile,
    ProfileReport,
    ProfileTable,
    TopValue,
)


def create_mock_profile() -> ProfileReport:
    cols = [
        "order_id",
        "order_date",
        "channel",
        "category",
        "quantity",
        "unit_price",
        "revenue",
    ]
    profiles = [
        ColumnProfile(
            name="order_id",
            distinct=240,
            numeric_count=0,
            nonnumeric_count=240,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
        ColumnProfile(
            name="order_date",
            distinct=180,
            numeric_count=0,
            nonnumeric_count=240,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
        ColumnProfile(
            name="channel",
            distinct=3,
            numeric_count=0,
            nonnumeric_count=240,
            numeric_min=None,
            numeric_max=None,
            top_values=[
                TopValue(value="Direct", count=100),
                TopValue(value="Organic", count=80),
                TopValue(value="Referral", count=60),
            ],
        ),
        ColumnProfile(
            name="category",
            distinct=4,
            numeric_count=0,
            nonnumeric_count=240,
            numeric_min=None,
            numeric_max=None,
            top_values=[
                TopValue(value="Electronics", count=90),
                TopValue(value="Apparel", count=80),
            ],
        ),
        ColumnProfile(
            name="quantity",
            distinct=15,
            numeric_count=240,
            nonnumeric_count=0,
            numeric_min="1.0",
            numeric_max="20.0",
            top_values=[],
        ),
        ColumnProfile(
            name="unit_price",
            distinct=45,
            numeric_count=240,
            nonnumeric_count=0,
            numeric_min="5.0",
            numeric_max="500.0",
            top_values=[],
        ),
        ColumnProfile(
            name="revenue",
            distinct=120,
            numeric_count=240,
            nonnumeric_count=0,
            numeric_min="10.0",
            numeric_max="10000.0",
            top_values=[],
        ),
    ]
    return ProfileReport(
        schema_version="1",
        sha256="0" * 64,
        format="csv",
        status="ready",
        delimiter=",",
        error=None,
        warnings=[],
        tables=[
            ProfileTable(
                name="CSV",
                columns=cols,
                row_count=240,
                missing=[0] * 7,
                preview=[["1", "2026-01-01", "Direct",
                          "Apparel", "2", "50", "100"]]
                * 5,
                profile=profiles,
            )
        ],
    )


def create_mock_cleaning() -> CleaningReport:
    cols = [
        "order_id",
        "order_date",
        "channel",
        "category",
        "quantity",
        "unit_price",
        "revenue",
    ]
    lineage = [
        ColumnLineage(
            original_name=c,
            clean_name=c,
            original_inferred_type="string",
            clean_type="float64" if c in (
                "quantity", "unit_price", "revenue") else "object",
            null_count_before=0,
            null_count_after=0,
        )
        for c in cols
    ]
    return CleaningReport(
        schema_version="1",
        status="ready",
        input_sha256="1" * 64,
        output_sha256="2" * 64,
        summary=CleaningSummary(
            original_rows=245,
            cleaned_rows=240,
            original_columns=7,
            cleaned_columns=7,
            duplicate_rows_removed=5,
            cells_modified=3,
        ),
        lineage=lineage,
        warnings=["Duplicate rows removed."],
    )


def test_generate_dashboard_spec_basic():
    profile = create_mock_profile()
    cleaning = create_mock_cleaning()
    spec = generate_dashboard_spec(
        dataset_version_id="ver-123",
        profile_report=profile,
        cleaning_report=cleaning,
        target_column="revenue",
    )

    assert isinstance(spec, DashboardSpec)
    assert spec.schema_version == "1"
    assert spec.dataset_version_id == "ver-123"
    assert len(spec.kpis) <= 6
    assert len(spec.charts) <= 6
    assert len(spec.filters) <= 4
    assert spec.table.page_size == 50

    # Ensure date column has a line chart
    chart_types = [c.chart_type for c in spec.charts]
    assert "line" in chart_types
    assert "bar" in chart_types
    assert "histogram" in chart_types

    # Ensure filters picked categories/ranges
    filter_cols = [f.column for f in spec.filters]
    assert "channel" in filter_cols
    assert "category" in filter_cols


def test_generate_dashboard_spec_with_baseline():
    profile = create_mock_profile()
    cleaning = create_mock_cleaning()
    baseline = BaselineReport(
        schema_version="1",
        status="ready",
        input_sha256="3" * 64,
        task_type="regression",
        target_column="revenue",
        split=SplitInfo(
            train_rows=192,
            test_rows=48,
            strategy="random",
            test_fraction=0.2,
            seed=42,
        ),
        reference=ModelMetrics(
            model_name="dummy", mae=228.24, fit_time_seconds=0.01),
        candidate=ModelMetrics(model_name="ridge", mae=73.47,
                               r2=0.88, fit_time_seconds=0.01),
        comparison=BaselineComparison(
            candidate_better=True,
            better_model="ridge",
            reason="Lower MAE",
        ),
    )

    spec = generate_dashboard_spec(
        dataset_version_id="ver-123",
        profile_report=profile,
        cleaning_report=cleaning,
        baseline_report=baseline,
        target_column="revenue",
    )

    assert any("Ridge MAE" in k.label for k in spec.kpis)
    assert any(k.value == 73.47 for k in spec.kpis)
    assert "ridge model" in spec.summary.lower()
