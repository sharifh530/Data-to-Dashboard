"""Deterministic baseline plan and scikit-learn code generator."""

import ast
from typing import Literal

from dtd_api.baseline_contracts import FeatureInfo
from dtd_api.inspection_contracts import ProfileReport


def generate_baseline_workflow(
    profile_report: ProfileReport,
    target_column: str,
    task_type: Literal["classification", "regression"],
    clean_columns: list[str],
) -> tuple[str, list[FeatureInfo]]:
    """Analyze profile report and generate a deterministic scikit-learn script."""
    if not profile_report.tables:
        raise ValueError("ProfileReport has no tables")

    table = profile_report.tables[0]
    total_rows = table.row_count

    # 1. Target column checks
    target_profile = next((c for c in table.profile if c.name == target_column), None)
    if not target_profile:
        raise ValueError(f"Target column '{target_column}' not found in profile")

    target_idx = next((i for i, c in enumerate(table.profile) if c.name == target_column), -1)
    if target_idx == -1:
        raise ValueError(f"Target column '{target_column}' not found in profile")

    # target_missing = table.missing[target_idx]
    # labeled_rows = total_rows - target_missing

    # We will build feature selection info
    features: list[FeatureInfo] = []
    numeric_features = []
    categorical_features = []

    for idx, col in enumerate(table.profile):
        if col.name == target_column:
            continue

        clean_name = clean_columns[idx]

        # Heuristic rules for exclusion
        if col.name.lower() in target_column.lower() or target_column.lower() in col.name.lower():
            features.append(
                FeatureInfo(
                    name=clean_name,
                    dtype="unknown",
                    role="excluded",
                    exclusion_reason="Potential leakage (name overlaps with target)",
                )
            )
            continue

        if (
            "id" in col.name.lower()
            or "key" in col.name.lower()
            or col.distinct >= total_rows * 0.95
        ):
            features.append(
                FeatureInfo(
                    name=clean_name,
                    dtype="unknown",
                    role="excluded",
                    exclusion_reason="High cardinality identifier",
                )
            )
            continue

        if col.distinct > 50 and col.nonnumeric_count > 0:
            features.append(
                FeatureInfo(
                    name=clean_name,
                    dtype="string",
                    role="excluded",
                    exclusion_reason="High cardinality categorical or text",
                )
            )
            continue

        # Select as feature
        if col.numeric_count > col.nonnumeric_count:
            features.append(FeatureInfo(name=clean_name, dtype="numeric", role="numeric"))
            numeric_features.append(clean_name)
        else:
            features.append(FeatureInfo(name=clean_name, dtype="string", role="categorical"))
            categorical_features.append(clean_name)

    # Base script structure
    code_lines = [
        '"""Generated baseline script with scikit-learn pipelines.',
        "Execute ONLY inside an isolated gVisor runtime.",
        '"""',
        "",
        "import json",
        "import time",
        "import numpy as np",
        "import pandas as pd",
        "from sklearn.model_selection import train_test_split",
        "from sklearn.pipeline import Pipeline",
        "from sklearn.compose import ColumnTransformer",
        "from sklearn.preprocessing import StandardScaler, OneHotEncoder",
        "from sklearn.impute import SimpleImputer",
        "from sklearn.linear_model import LogisticRegression, Ridge",
        "from sklearn.dummy import DummyClassifier, DummyRegressor",
        "from sklearn.metrics import (accuracy_score, f1_score, roc_auc_score,",
        "                              mean_absolute_error, mean_squared_error, r2_score,",
        "                              confusion_matrix)",
        "",
        "",
        "def train_baseline(df: pd.DataFrame) -> dict:",
        "    report = {",
        '        "schema_version": "1",',
        f'        "task_type": "{task_type}",',
        f'        "target_column": "{target_column}",',
        '        "features": [],',
        '        "warnings": [],',
        "    }",
        "",
    ]

    # We must construct features properly
    features_list = [f.model_dump() for f in features]
    code_lines.extend(
        [
            f"    features_info = {repr(features_list)}",
            "    report['features'] = features_info",
            "",
            f"    target = '{target_column}'",
            "    if target not in df.columns:",
            "        report['status'] = 'failed'",
            "        report['error'] = 'Target column missing in cleaned data'",
            "        return report",
            "",
            "    # Drop rows without target labels",
            "    df = df.dropna(subset=[target])",
            "    if len(df) < 100:",
            "        report['status'] = 'skipped'",
            "        report['skip_reason'] = f'Too few labeled rows ({len(df)} < 100)'",
            "        return report",
            "",
        ]
    )

    if not numeric_features and not categorical_features:
        code_lines.extend(
            [
                "    report['status'] = 'skipped'",
                "    report['skip_reason'] = 'No usable features remain after exclusions'",
                "    return report",
                "",
            ]
        )
    else:
        # Preprocessing setup
        code_lines.extend(
            [
                "    # Feature definition",
                f"    numeric_features = {repr(numeric_features)}",
                f"    categorical_features = {repr(categorical_features)}",
                "",
                "    numeric_transformer = Pipeline(steps=[",
                "        ('imputer', SimpleImputer(strategy='median')),",
                "        ('scaler', StandardScaler())])",
                "",
                "    categorical_transformer = Pipeline(steps=[",
                "        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),",
                "        ('onehot', OneHotEncoder(handle_unknown='ignore', max_categories=50))])",
                "",
                "    preprocessor = ColumnTransformer(transformers=[",
                "        ('num', numeric_transformer,\n            [f for f in numeric_features if f in df.columns]),",  # noqa: E501
                "        ('cat', categorical_transformer,\n            [f for f in categorical_features if f in df.columns])",  # noqa: E501
                "    ])",
                "",
            ]
        )

        # Task specific logic
        if task_type == "classification":
            code_lines.extend(
                [
                    "    unique_classes = df[target].nunique()",
                    "    if unique_classes < 2 or unique_classes > 20:",
                    "        report['status'] = 'skipped'",
                    "        report['skip_reason'] = (\n            f'Classification requires 2-20 classes, found {unique_classes}'\n        )",  # noqa: E501
                    "        return report",
                    "",
                    "    # Check min samples per class",
                    "    class_counts = df[target].value_counts()",
                    "    if class_counts.min() < 10:",
                    "        report['status'] = 'skipped'",
                    "        report['skip_reason'] = (\n            f'All classes must have >=10 samples, '\n            f'{class_counts.idxmin()} has {class_counts.min()}'\n        )",  # noqa: E501
                    "        return report",
                    "",
                    "    # Split",
                    "    X = df.drop(columns=[target])",
                    "    y = df[target].astype(str)",
                    "    X_train, X_test, y_train, y_test = train_test_split(",
                    "        X, y, test_size=0.2, random_state=42, stratify=y",
                    "    )",
                    "",
                    "    report['split'] = {",
                    "        'train_rows': len(X_train),",
                    "        'test_rows': len(X_test),",
                    "        'seed': 42,",
                    "        'strategy': 'stratified',",
                    "        'test_fraction': 0.2",
                    "    }",
                    "",
                    "    models = {",
                    "        'dummy': DummyClassifier(strategy='most_frequent'),",
                    "        'logistic': LogisticRegression(max_iter=1000, random_state=42)",
                    "    }",
                    "",
                    "    results = {}",
                    "    for name, clf in models.items():",
                    "        pipe = Pipeline(steps=[('preprocessor', preprocessor),\n                               ('classifier', clf)])",  # noqa: E501
                    "        t0 = time.time()",
                    "        pipe.fit(X_train, y_train)",
                    "        t_fit = time.time() - t0",
                    "",
                    "        y_pred = pipe.predict(X_test)",
                    "        acc = accuracy_score(y_test, y_pred)",
                    "        f1 = f1_score(y_test, y_pred, average='macro')",
                    "",
                    "        results[name] = {",
                    "            'model_name': name,",
                    "            'accuracy': acc,",
                    "            'macro_f1': f1,",
                    "            'parameters': clf.get_params(),",
                    "            'fit_time_seconds': t_fit,",
                    "        }",
                    "",
                    "    report['reference'] = results['dummy']",
                    "    report['candidate'] = results['logistic']",
                    "",
                    "    cand_better = (\n        results['logistic']['macro_f1'] > results['dummy']['macro_f1']\n    )",  # noqa: E501
                    "    report['comparison'] = {",
                    "        'candidate_better': cand_better,",
                    "        'better_model': 'logistic' if cand_better else 'dummy',",
                    "        'reason': 'Based on macro-F1 score on test set',",
                    "    }",
                    "",
                    "    y_pred = pipe.predict(X_test)\n    report['confusion_matrix'] = confusion_matrix(y_test, y_pred).tolist()",  # noqa: E501
                    "    report['status'] = 'ready'",
                    "    return report",
                ]
            )
        else:
            code_lines.extend(
                [
                    "    # Split",
                    "    X = df.drop(columns=[target])",
                    "    y = pd.to_numeric(df[target], errors='coerce')",
                    "    valid_y = ~y.isna()",
                    "    X, y = X[valid_y], y[valid_y]",
                    "",
                    "    X_train, X_test, y_train, y_test = train_test_split(",
                    "        X, y, test_size=0.2, random_state=42",
                    "    )",
                    "",
                    "    report['split'] = {",
                    "        'train_rows': len(X_train),",
                    "        'test_rows': len(X_test),",
                    "        'seed': 42,",
                    "        'strategy': 'random',",
                    "        'test_fraction': 0.2",
                    "    }",
                    "",
                    "    models = {",
                    "        'dummy': DummyRegressor(strategy='mean'),",
                    "        'ridge': Ridge(alpha=1.0, random_state=42)",
                    "    }",
                    "",
                    "    results = {}",
                    "    for name, reg in models.items():",
                    "        pipe = Pipeline(steps=[('preprocessor', preprocessor),\n                               ('regressor', reg)])",  # noqa: E501
                    "        t0 = time.time()",
                    "        pipe.fit(X_train, y_train)",
                    "        t_fit = time.time() - t0",
                    "",
                    "        y_pred = pipe.predict(X_test)",
                    "        mae = mean_absolute_error(y_test, y_pred)",
                    "        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))",
                    "        r2 = r2_score(y_test, y_pred)",
                    "",
                    "        results[name] = {",
                    "            'model_name': name,",
                    "            'mae': mae,",
                    "            'rmse': rmse,",
                    "            'r2': r2,",
                    "            'parameters': reg.get_params(),",
                    "            'fit_time_seconds': t_fit,",
                    "        }",
                    "",
                    "    report['reference'] = results['dummy']",
                    "    report['candidate'] = results['ridge']",
                    "",
                    "    cand_better = results['ridge']['mae'] < results['dummy']['mae']",
                    "    report['comparison'] = {",
                    "        'candidate_better': cand_better,",
                    "        'better_model': 'ridge' if cand_better else 'dummy',",
                    "        'reason': 'Based on MAE on test set',",
                    "    }",
                    "    report['status'] = 'ready'",
                    "    return report",
                ]
            )

    generated_code = "\n".join(code_lines)

    # Validate AST to ensure valid Python syntax
    ast.parse(generated_code)

    return generated_code, features
