"""Tests for baseline workflow generation."""

import ast

import pytest
from dtd_api.baseline_generator import generate_baseline_workflow
from dtd_api.inspection_contracts import ColumnProfile, ProfileReport, ProfileTable


@pytest.fixture
def mock_profile_report():
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
                columns=[
                    "target_cls",
                    "target_reg",
                    "num_feat",
                    "cat_feat",
                    "high_card_cat",
                    "target_cls_leakage",
                    "id_feat",
                ],
                row_count=1000,
                missing=[0, 0, 0, 0, 0, 0, 0],
                preview=[["1", "2", "3", "A", "B", "1", "id1"]] * 5,
                profile=[
                    ColumnProfile(
                        name="target_cls",
                        distinct=2,
                        numeric_count=1000,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="target_reg",
                        distinct=100,
                        numeric_count=1000,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="num_feat",
                        distinct=50,
                        numeric_count=1000,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="cat_feat",
                        distinct=5,
                        numeric_count=0,
                        nonnumeric_count=1000,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="high_card_cat",
                        distinct=60,
                        numeric_count=0,
                        nonnumeric_count=1000,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="target_cls_leakage",
                        distinct=50,
                        numeric_count=1000,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="id_feat",
                        distinct=980,
                        numeric_count=0,
                        nonnumeric_count=1000,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                ],
            )
        ],
    )


def test_generate_baseline_classification(mock_profile_report):
    clean_columns = [
        "target_cls",
        "target_reg",
        "num_feat",
        "cat_feat",
        "high_card_cat",
        "target_cls_leakage",
        "id_feat",
    ]

    script, features = generate_baseline_workflow(
        profile_report=mock_profile_report,
        target_column="target_cls",
        task_type="classification",
        clean_columns=clean_columns,
    )

    # target_cls is excluded from feature list entirely
    assert len(features) == 6

    # Check exclusions
    excluded = [f.name for f in features if f.role == "excluded"]
    assert "target_cls_leakage" in excluded
    assert "high_card_cat" in excluded
    assert "id_feat" in excluded

    # Check inclusions
    included = [f.name for f in features if f.role in ["numeric", "categorical"]]
    assert "num_feat" in included
    assert "cat_feat" in included
    assert "target_reg" in included

    # Check syntax
    ast.parse(script)

    # Check script contents
    assert "DummyClassifier" in script
    assert "LogisticRegression" in script


def test_generate_baseline_regression(mock_profile_report):
    clean_columns = [
        "target_cls",
        "target_reg",
        "num_feat",
        "cat_feat",
        "high_card_cat",
        "target_cls_leakage",
        "id_feat",
    ]

    script, features = generate_baseline_workflow(
        profile_report=mock_profile_report,
        target_column="target_reg",
        task_type="regression",
        clean_columns=clean_columns,
    )

    ast.parse(script)
    assert "DummyRegressor" in script
    assert "Ridge" in script


def test_generate_baseline_no_usable_features(mock_profile_report):
    # Pass only features that will be excluded
    clean_columns = ["target_cls", "high_card_cat", "target_cls_leakage", "id_feat"]

    mock_profile_report.tables[0].columns = clean_columns
    mock_profile_report.tables[0].missing = [0, 0, 0, 0]
    mock_profile_report.tables[0].preview = [["1", "B", "1", "id1"]] * 5
    mock_profile_report.tables[0].profile = [
        ColumnProfile(
            name="target_cls",
            distinct=2,
            numeric_count=1000,
            nonnumeric_count=0,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
        ColumnProfile(
            name="high_card_cat",
            distinct=60,
            numeric_count=0,
            nonnumeric_count=1000,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
        ColumnProfile(
            name="target_cls_leakage",
            distinct=50,
            numeric_count=1000,
            nonnumeric_count=0,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
        ColumnProfile(
            name="id_feat",
            distinct=980,
            numeric_count=0,
            nonnumeric_count=1000,
            numeric_min=None,
            numeric_max=None,
            top_values=[],
        ),
    ]

    script, features = generate_baseline_workflow(
        profile_report=mock_profile_report,
        target_column="target_cls",
        task_type="classification",
        clean_columns=clean_columns,
    )

    assert "report['status'] = 'skipped'" in script
    assert "No usable features remain" in script


def test_generate_baseline_skip_too_few_rows():
    report = ProfileReport(
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
                columns=["target_cls", "num_feat"],
                row_count=50,  # < 100
                missing=[0, 0],
                preview=[["1", "3"]] * 5,
                profile=[
                    ColumnProfile(
                        name="target_cls",
                        distinct=2,
                        numeric_count=50,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                    ColumnProfile(
                        name="num_feat",
                        distinct=50,
                        numeric_count=50,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                ],
            )
        ],
    )

    script, features = generate_baseline_workflow(
        profile_report=report,
        target_column="target_cls",
        task_type="classification",
        clean_columns=["target_cls", "num_feat"],
    )

    assert "Too few labeled rows" in script
    assert "report['status'] = 'skipped'" in script


def test_generate_baseline_skip_no_target():
    report = ProfileReport(
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
                columns=["num_feat"],
                row_count=1000,
                missing=[0],
                preview=[["3"]] * 5,
                profile=[
                    ColumnProfile(
                        name="num_feat",
                        distinct=50,
                        numeric_count=1000,
                        nonnumeric_count=0,
                        numeric_min=None,
                        numeric_max=None,
                        top_values=[],
                    ),
                ],
            )
        ],
    )

    with pytest.raises(ValueError, match="Target column 'target_cls' not found"):
        generate_baseline_workflow(
            profile_report=report,
            target_column="target_cls",
            task_type="classification",
            clean_columns=["num_feat"],
        )
