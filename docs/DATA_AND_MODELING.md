# Data ingestion, cleaning, and modeling

## Input contract

CSV: UTF-8/UTF-8 BOM by default; offer explicit encoding override after a decode error. Infer delimiter from a bounded sample and confirm ambiguous interpretations. Preserve original header-to-canonical-name mapping. Keep numeric-looking identifiers as strings when leading zeros or identifier semantics indicate that conversion would lose information. Reject malformed rows with line diagnostics; an explicit later repair option may quarantine them, but silent skipping is prohibited.

SQLite: accept a complete standalone database, not WAL/SHM/journal fragments. Inspect schema and run bounded integrity checks inside isolation. List only ordinary user tables; exclude internal, virtual, and view objects. Use quoted validated identifiers and parameterized values. Never run uploaded SQL text, extensions, attachments, or schema-defined executable behavior. Unsupported file versions/encryption or inconsistent journals produce actionable errors. Multiple tables require user selection; joins are deferred.

Both formats: enforce upload and decoded-size limits, cap string lengths and cardinality, sanitize display values, and preserve raw file hash. Empty tables, duplicate names, all-null columns, constant columns, and mixed types require explicit diagnostics. Assign stable internal row identifiers independent of dataframe index.

## Cleaning policy

1. Profile raw values deterministically before consulting the LLM.
2. Request a structured plan and generated Pandas script with input/output contracts.
3. Permit deterministic format normalization with reported effects: header normalization, whitespace cleanup where meaningful, explicit null tokens, and unambiguous date/number conversions.
4. Preserve ambiguous values and flag them. Do not silently delete outliers, impute target labels, merge categories, or remove apparently duplicated records without a justified policy. Prompt for consequential ambiguous choices or use a conservative no-change default.
5. Execute on a copy in isolation; verify schema, row reconciliation, output size, and operation report before promotion.

The cleaned exploratory dataset and model preprocessing are separate artifacts. Data-dependent imputation, encoding, scaling, feature selection, and outlier thresholds for modeling are fit on training data only. Record raw/clean row counts, changed cell counts, removed/quarantined rows, warnings, script hash, input hash, and policy version. Cleaning does not invent unavailable source facts.

## Model eligibility and split

The user chooses target and confirms regression or classification when ambiguous. Default eligibility: at least 100 labeled rows, at least one usable feature, and two target values. Classification supports 2–20 classes with at least 10 labeled rows per class before attempting a stratified split. Recheck each partition; skip with a reason if stratification or metric computation is invalid. Exclude unlabeled target rows from modeling only and report their count.

Default split: 80/20 train/test, seed 42; classification stratified where valid. If rows represent repeated entities, require group-aware splitting. If predicting later observations, use an explicitly selected chronological split. Surface a warning when the system cannot infer independence; record the chosen strategy. Remove identifiers, direct target copies, post-outcome fields identified by the user, and known leakage proxies. Heuristics cannot guarantee leakage detection.

## Baseline protocol

| Task | Reference | Candidate | Report |
| --- | --- | --- | --- |
| Classification | DummyClassifier | LogisticRegression in preprocessing pipeline | Class counts, accuracy, macro-F1, confusion matrix; binary ROC-AUC only when valid |
| Regression | DummyRegressor | Ridge in preprocessing pipeline | MAE, RMSE, R² when defined; residual plot |

Use numeric median imputation, categorical missing token, bounded one-hot encoding with unknown handling, and numeric scaling inside a scikit-learn Pipeline/ColumnTransformer. High-cardinality and text fields are excluded with a reason in MVP; cap expanded feature count (initial target: 5,000) and fail gracefully before memory exhaustion.

The model family and settings are fixed before test evaluation. The agent cannot search repeatedly against the test set. Model repairs may fix execution errors but cannot optimize observed test scores; log attempts. A candidate below the dummy score remains a valid reported result, with the dummy identified as better. A high score is not proof of causal insight or deployment fitness.

Store split indices/hashes, seed, package/image versions, exclusions, sample sizes, timing, metrics with null reasons, and model parameters. Reproducibility targets stable code/data/policy execution, not byte-identical LLM output. Pipeline separation follows [scikit-learn's leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).

## Dashboard evidence and export

Every KPI/chart points to a validated metric ID or allowlisted aggregate query over a specific artifact version. Include units, missingness, denominator, aggregation, and sampling status. No numerical claim comes only from generated prose. Cleaned CSV exports neutralize spreadsheet formula prefixes in text fields and disclose this export-only escaping; preserve analytical values in the canonical internal artifact. Export manifest includes hashes and lineage, but no credentials or executable serialized estimator.
