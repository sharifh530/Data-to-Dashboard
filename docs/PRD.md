# Product requirements

Version 0.1 • 2026-09-16 • Status: proposed implementation baseline

## Product objective

Enable an analyst or small-business operator to get an auditable first analysis from a messy tabular file without writing code. Demonstrate autonomous code generation, constrained execution, sound baseline modeling, and dynamic UI generation in one usable full-stack product.

Primary users: a nontechnical operator exploring a business dataset; a data analyst accelerating initial investigation; a developer inspecting generated code and provenance. The application supports exploratory decisions, not automated high-stakes decisions.

## MVP boundary

Included: authenticated private workspaces; CSV and standalone SQLite uploads; one table per analysis; schema preview; cleaning reports; bounded agent execution; optional classification or regression; generated React dashboards with filters; run history; cancellation; artifact exports; deletion; security and operational tests.

Deferred: joins across tables/files, Excel, live database credentials, streaming data, forecasting models, hyperparameter search, model serving, collaborative editing, public sharing, billing, arbitrary dependency installation, user-defined plugins, unrestricted code editing/execution, and natural-language dashboard revision. Chronological evaluation is supported when configured, but does not constitute a forecasting product.

Target selection is explicit. The agent may suggest a target and task type but cannot silently choose an outcome. Exploratory analysis remains successful if modeling is skipped, unsupported, or fails independently.

## User journey

1. Sign in and create a project.
2. Upload a CSV or SQLite file; receive validation progress.
3. Select a SQLite table when needed; review preview, inferred types, and warnings.
4. Set an optional analysis question and prediction target, exclusions, and split strategy.
5. Review external-model data disclosure and start the analysis.
6. Follow durable progress, inspect cleaning decisions, resolve ambiguous inputs if necessary, or cancel.
7. Explore dashboard and model report; download cleaned data and a provenance bundle.
8. Revisit a prior immutable run or delete the dataset and derived outputs.

## Functional requirements

| ID | Requirement | Acceptance criterion |
| --- | --- | --- |
| FR-01 | Project ownership | A second user cannot list, read, modify, stream, or download the first user's resources, even using known IDs. |
| FR-02 | Upload validation | Streamed uploads enforce byte limits regardless of client headers; file signatures and parse results determine supported format. |
| FR-03 | CSV import | Quoted delimiters, BOMs, missing values, duplicate headers, and malformed rows produce a preview or an actionable error without silently discarding rows. |
| FR-04 | SQLite import | Enumerate ordinary user tables in isolation; select exactly one; views, virtual tables, extensions, and sidecar-dependent files are rejected or clearly unsupported. |
| FR-05 | Profiling | Display row/column counts, types, null ratios, duplicate counts, and bounded distributions with sampling explicitly labeled. |
| FR-06 | Cleaning | Generate Pandas source; execute only in sandbox; persist before/after quality, operation reasons, and row/column lineage. |
| FR-07 | Modeling | For an eligible selected target, compare a dummy estimator with one baseline using a documented split and appropriate metrics; otherwise explain why skipped. |
| FR-08 | Dashboard | Generate a validated specification and React component, including evidence-backed KPIs, at least two suitable charts where data permits, a table, and applicable filters. |
| FR-09 | UI resilience | Invalid code, compilation failure, or rendering failure produces the spec-based fallback with an honest status and useful data. |
| FR-10 | Durable runs | Refresh/reconnect restores progress; retries cannot publish duplicate outputs; cancel terminates active execution and prevents late publication. |
| FR-11 | Provenance/export | Download cleaned CSV, cleaning report, metrics, generated source, and manifest tied to an immutable run version. |
| FR-12 | Privacy/deletion | Disclose provider-bound data before analysis; deletion immediately revokes access and schedules physical cleanup across artifacts and checkpoints. |
| FR-13 | History | View past run inputs, status, timestamps, warnings, and dashboard version; reruns create new records. |
| FR-14 | Honest narratives | Every numerical assertion references an artifact/metric; no invented metrics or claims of causation. |

## Proposed limits and quality targets

These are configurable engineering targets, not measured capabilities. Start with 25 MiB per upload, 100,000 rows and 100 columns per selected table, 5 MiB maximum cell size, one active run per user, and five concurrent runs per development deployment. Reject oversized decoded tables rather than silently truncate training data. Preview at most 100 rows; provider payload at most 20 masked sample rows and 32 KiB of serialized context.

On a reference environment to be recorded in the benchmark report (initial target: 4 vCPU/16 GiB Linux control plane plus isolated 2 vCPU/2 GiB jobs), a 10,000-row/20-column fixture should finish within five minutes at p95 across 20 runs with a named provider/model. Application API reads should remain below 500 ms p95 excluding downloads and provider calls. Progress should update within three seconds of a persisted stage event. Cancellation should stop compute within ten seconds. Hard run deadline: ten minutes, excluding explicitly paused user-input time (pause expiry: 24 hours).

Accessibility target: WCAG 2.2 AA for owned application surfaces; keyboard access and textual chart summaries for generated/fallback dashboards. Test widths of 360, 768, and 1440 pixels. Reliability target: at least 18 of 20 documented representative supported fixtures produce usable dashboards; security violations have zero tolerated successes. Numerical correctness and modeling validity take precedence over completion rate.

## Release definition

All P0 tasks and security gates pass; requirements have linked evidence; the demonstration works for CSV, SQLite, no-target, and failed-generation cases; setup and cleanup are reproducible from a clean environment. A public release also requires real authentication, authorization tests, enforced runtime isolation, retention cleanup, provider disclosure, deployment/restore rehearsal, and an operational owner.
