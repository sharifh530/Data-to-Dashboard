# Milestone B10 Evidence: Dashboard Specification, Query Broker, and Fallback UI

## Overview
Milestone B10 implements the complete Dashboard Specification v1, the allowlisted server query broker, and the accessible React fallback UI. This connects the isolated data transformation pipeline (Milestone B08) and baseline model evaluation (Milestone B09) directly to visual analysis.

## Key Delivered Features

1. **Dashboard Contracts (`services/api/src/dtd_api/dashboard_contracts.py`)**:
   - `DashboardSpec`: Conforms to `docs/AGENT_AND_UI.md` v1 specifications.
     - Maximum 6 KPIs.
     - Maximum 6 Charts (Bar, Line, Histogram, Scatter).
     - Maximum 4 Filters (Category, Range, Date).
     - Paginated Table specification with default sorting and page size.
     - Warnings preservation and optional model report reference.
   - `DashboardQueryRequest` & `DashboardQueryResponse`: Typed, bounded contracts for interactive dashboard visualization.
   - `DashboardView`: Exposes validated spec, render mode (`fallback`), and execution status.

2. **Deterministic Dashboard Specification Generator (`services/api/src/dtd_api/dashboard_generator.py`)**:
   - Analyzes `ProfileReport` and `CleaningReport` (and optional `BaselineReport`).
   - Generates sensible, bounded visualizations matching actual data types (e.g. Bar charts for low-cardinality categories, Histograms for numeric columns, Line charts for date/time columns without fabrication, Scatter plots for numeric comparisons).
   - Generates KPI summaries (Cleaned rows, column count, duplicates dropped, model performance metrics).
   - Generates interactive filters for categories and numeric bounds.

3. **Stage Orchestration (`services/api/src/dtd_api/run_engine.py`)**:
   - Added `plan_dashboard` to `ANALYSIS_STAGES = ("clean_dataset", "train_baseline", "plan_dashboard")`.
   - Executes stage after baseline evaluation, generating `DashboardSpec`.
   - Stores `dashboard_spec.json` as an immutable run artifact (`kind="dashboard_spec"`).
   - Records/upserts durable `Dashboard` row in the database with `render_mode="fallback"`.

4. **Allowlisted Server Query Broker (`services/api/src/dtd_api/query_broker.py`)**:
   - Computes aggregations, binned histograms, timelines, and scatter coordinates over `cleaned.csv`.
   - Evaluates filter clauses (`eq`, `in`, `between`, `gte`, `lte`) using an allowlisted column AST.
   - Enforces 500-point chart capping with explicit `sample_indicator` indicators.
   - Enforces 100-row table pagination limits.
   - Operates purely in standard Python with zero external execution risks.

5. **API Endpoints (`services/api/src/dtd_api/runs.py`)**:
   - `GET /api/v1/runs/{id}/dashboard`: Serves the validated dashboard specification.
   - `POST /api/v1/runs/{id}/queries`: Evaluates allowlisted queries for the authenticated run owner.

6. **Accessible React Fallback UI (`apps/web/DashboardFallback.tsx`)**:
   - Displays required status badge: `Standard layout active (Fallback mode)`.
   - Interactive filter bar with category dropdowns, inputs, and a one-click `Reset filters` button.
   - Responsive KPI cards.
   - Accessible SVG visualizations for Bar, Histogram, and Line/Scatter plots with tooltips and axis labels.
   - Paginated data table with page size 50 and interactive column sorting.
   - Friendly empty-state message when filters match 0 rows.
   - Integrated into the main web workspace (`apps/web/main.tsx`).

## Validation Results

- `npm run check:python`: 31 files clean, Ruff format/lint and strict Mypy passed.
- `npm run test:python`: 84 unit and integration tests passed (45 PostgreSQL parity skips).
- `tests/python/test_dashboard_generator.py`: Verified chart, KPI, and filter limits, data type matching, and baseline report linking.
- `tests/python/test_query_broker.py`: Verified filter operators, column security, 500-point chart caps, and 100-row table paging.
- `tests/python/test_runs.py`: Verified complete 3-stage lifecycle (`clean_dataset` -> `train_baseline` -> `plan_dashboard`), spec artifact creation, and dashboard queries.
- `npm run test:postgres`: All 129 tests passed against real PostgreSQL 17 engine with zero failures.
- `npm run contracts:check`: OpenAPI and generated TypeScript contracts in sync.
- `npm run build`: Both renderer lab and workspace web UI compiled cleanly.

## Next Concrete Action
Proceed to **Milestone B11 (Generated React compile/render pipeline)**: Isolated compilation of LLM-generated React components, iframe sandbox execution, CSP enforcement, and bridge communication with the query broker.
