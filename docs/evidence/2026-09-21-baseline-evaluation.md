# Milestone B09 Evidence: Baseline Evaluation

## Overview

The goal of Milestone B09 was to implement a secure, deterministic baseline model generation and evaluation pipeline running in isolated gVisor containers. The system now parses profiling reports to exclude identifiers, select features, apply one-hot encoding or scaling, and fit a dummy reference against an intelligent candidate (Ridge/Logistic Regression) to score basic signal strength.

## Implementation Details

1. **Baseline Generator (`services/api/src/dtd_api/baseline_generator.py`)**:
   - Parses `ProfileReport` to map valid target columns.
   - Automatically drops high-cardinality `identifier` features.
   - Computes appropriate preprocessing pipelines (`StandardScaler` and `OneHotEncoder`).
   - Handles both `classification` and `regression` tasks.
   - Validates class counts (minimum 10 rows per class, 2-20 classes total).
   - Injects the generated script to train a `Dummy` vs `Candidate` model and evaluate the performance safely.

2. **Run Engine Integration (`services/api/src/dtd_api/run_engine.py`)**:
   - Integrated the generation stage into the `train_baseline` stage loop.
   - Triggers isolated execution (`run_isolated_transform(mode="baseline")`).
   - Reads back and logs the final validation reports to the API DB checkpoint.

3. **gVisor Sandbox Implementation (`sandbox/transformer/transform_data.py`)**:
   - Implemented `run_baseline()` matching the security characteristics of `run_transformation()`.
   - Uses `compile` and `exec` inside a namespace strictly bounded to `pd` and `np`.
   - Ensures memory thresholds, NUL byte stripping, and hash signatures on inputs and outputs.

## Validation

- `npm run test:python` passes, specifically `tests/python/test_baseline.py` covers classification limits, feature exclusions, and regression schemas.
- `scripts/test-transformer.py` integration acceptance tests successfully generate and execute a pipeline end-to-end inside gVisor.
- `npm run check` passes, guaranteeing rigorous type consistency and deterministic linting.

## Next Steps
Proceeding to B10 (Analysis rendering & layout).
