# Session log

## 2026-09-17 — PostgreSQL persistence and local authentication

Implemented B03 and the local B04 scope: 15 SQLAlchemy metadata tables, initial Alembic revision, composite project/run lineage constraints, local one-time login, hashed sessions, origin/CSRF checks, owner-scoped project create/list/read, idempotency and pagination. Added setup/provisioning helpers, generated OpenAPI/types, and PostgreSQL CI service. Hosted sign-in is separately tracked as B04H; no hosted/provider integration is claimed.

Found PostgreSQL 17.6 binaries and created a project-owned loopback cluster in ignored `.local`. It uses port 55432 and dedicated development/test databases without altering the existing system service. Credentials were generated into ignored local files and never printed. A Windows inherited-pipe startup hang was fixed with file-based child output. After the local server stopped between sessions, restarted it and added five-second connection timeouts; reran verification successfully.

Validation: `npm run check` passes lint/format/types/contracts/build and 4 protocol tests; default Python 35 passed/12 explicit PostgreSQL skips. `npm run test:postgres` passes all 47 Python cases, including real concurrency and migration recovery. `npm run db:check` shows no drift. Two pre-existing upstream test-client warnings remain. No frontend behavior changed, so existing browser tests were not repeated. Update/commit/push this milestone to the authorized origin; verify remote hash. Next: B06 orchestration while resolving B01 for safe ingestion/execution.

## 2026-09-17 — GitHub repository and milestone push policy

The user provided `https://github.com/sharifh530/Data-to-Dashboard.git` and authorized pushes after each major task. Remote inspection returned no existing refs. Initialized local `main`, configured `origin`, and fetched before preparing the foundation commit. Recorded the standing push authorization in AGENTS.md and updated current setup/state documentation. Prior foundation validation remains applicable; this session changes source-control documentation only. Publication is recorded in Git history; verify remote HEAD after pushing. Generated artifacts, dependencies, virtual environments, and secrets remain excluded through `.gitignore`.

## 2026-09-16 — Documentation foundation

Request: define the full Data-to-Dashboard project, build process, requirements, and persistent tracking files.

Inspected the workspace; no existing files were listed. Created the specification package and repository instructions. Consulted primary references on LangGraph replay, runtime isolation, browser sandboxing, and model leakage. Chose proposed architecture defaults while leaving hosting, auth, and model provider selections open.

Validation: PowerShell enumerated all Markdown files and checked relative Markdown link targets with `Test-Path`; 20 documents, zero broken local links. `rg --files` confirmed the expected package is present. Reviewed requirements/backlog/state consistency; all application work remains TODO. Application tests not run because no application exists.

Next: B01 security feasibility and B02 toolchain foundation. All feature implementation remains TODO.

## 2026-09-16 — Foundation implementation and isolation lab

Request: proceed with the next step. Read instructions/memory/security contracts. Inspected Node 24.20.0, Python 3.13.7/3.14.7, Docker CLI, and stopped Docker-only WSL distribution. Chose Python 3.13.7 and bootstrapped uv 0.12.15 into ignored `.tools`. No Git repository existed or was initialized.

Implemented local API, contracts, scoped React bridge/lab, runtime preflight/fixed probe tooling, locked dependencies, checks, and CI definition. Added setup guide and security evidence. Uploads/model-produced execution remain disabled.

Validation: `npm run check` passed with 24 Python and 4 TypeScript tests plus lint/format/types/contracts/build. All 5 Chromium tests passed after an accessible selector fix. HTTP smoke passed. Runtime preflight returned `DOCKER_UNAVAILABLE` (exit 2); container probes were NOT run. Two upstream Python warnings remain. TypeScript peer conflict resolved using a compatible exact version.

Started API/lab sessions and queued the lab in Codex. Docker Desktop was launched hidden once; engine remained unavailable. No daemon settings changed. Next: B03 persistence/contracts and B04 ownership while resolving B01's dedicated-runtime prerequisite.

## 2026-09-17 — B06 durable synthetic processing

Implemented PostgreSQL outbox/work items, fenced leases, three fixed stages, retry/deadline bounds, owner-scoped run history/detail/SSE and cancellation. Added worker command, migration preserving event IDs, contracts, ADR-017 and run guide. No generated execution or uploaded data processing enabled.

Validation: npm run check passed (4 protocol tests; 48 Python passed/28 PostgreSQL skipped; lint/types/contracts/build). npm run test:postgres: all 76 passed, no skips; two existing upstream warnings. Includes real concurrency, separate process restart, lease recovery, cancellation/publication race and ownership/revocation. npm run db:check: no drift. npm run dev:worker -- --once succeeded. Renderer unchanged, browser tests not rerun. Initial nested .kilo lint discovery and migration import-order failures corrected. Tooling worktree contents untouched.

Fetched remote main; unchanged from persistence/auth milestone before publication. Authorized commit/push follows documentation updates. Next: resolve B01 for B05, or bounded immutable upload storage with parsing disabled if runtime stays blocked.

## 2026-09-17 — B05 bounded raw upload storage slice

Rechecked sandbox preflight: Docker unreachable, generated execution disabled. Implemented storage-only raw upload endpoint, transactional PostgreSQL bytes/metadata/idempotency, checksum verification, owner-only metadata/download, bounded receipt and per-owner quotas. Migration 7c8ecbbfe69e; ADR-018 documents local bytea instead of unimplemented S3. B05 remains partial: no parsing, inspection, selection, preview or analysis admission.

Validation: npm run check passed (4 protocol tests, 52 Python passed/31 PostgreSQL skipped, lint/types/contracts/build). Final npm run test:postgres passed 84/84 after concurrent quota test; npm run check:python passed; npm run db:check reported no drift. Receiver timeout/disconnect, revocation during upload, corruption, idempotency and ownership covered. Two existing upstream warnings. Renderer unchanged, browser tests not rerun. See docs/evidence/2026-09-17-upload-storage.md.

Updated docs/memory and publishing this completed storage slice under standing authorization. Next: resolve dedicated sandbox for inspection, or authenticated upload/history product UX while visibly reporting inspection blocked.

## 2026-09-17 — B12 local workspace shell

Built reviewed React workspace on the same API origin, local ticket sign-in, project sidebar/creation, raw upload/download, dataset list, sample run history/polling/cancel and logout. Added paginated owner-scoped dataset listing, static asset allowlisting/CSP, esbuild command, browser test harness, CI step and ADR-019. Responsive desktop/mobile screenshots visually checked. B12 remains partial; analysis/dashboard/model screens depend on actual isolated processing.

Validation: npm run check passed (4 protocol tests, 53 Python passed/33 PostgreSQL skipped, lint/types/contracts/build); npm run test:postgres passed 86/86; npm run test:web passed real API Chromium journey, repeated after minor UI fixes with lint/types. Existing renderer suite unchanged, not rerun. No JavaScript page errors or mobile horizontal overflow. Two existing Python test-client warnings remain. See docs/evidence/2026-09-17-workspace-ui.md.

Restarted only the verified project API process; new server on 127.0.0.1:8000, process 11388 at time of startup. PostgreSQL verified. No normal worker started. Next priority: establish a verified hardened execution environment and implement actual file inspection, rather than expanding synthetic workflows. Standing authorization covers milestone commit/push.

## 2026-09-17 — Uploadable sample dataset

Created samples/synthetic-sales-messy.csv at user request: 245 rows, 11 columns, 17,418 bytes of fictional sales. Includes five exact duplicates, missing values, case/whitespace differences and currency formatting. Python CSV roundtrip verified row/field counts, 240 distinct order IDs and positive revenue. samples/README.md explains contents and the constructed target limitation. No application code changed; application tests were not rerun. Upload inspection remains disabled. Published under standing repository authorization.

## 2026-09-17 — Dedicated WSL2 gVisor runtime

Docker Desktop became reachable but lacked runsc. User explicitly selected creating a separate project WSL2 environment. Imported official pinned Ubuntu 24.04 filesystem into ignored .local/wsl/dtd-sandbox, installed Docker 29.1.3 and runsc 20260914.0 from signed package repositories, enabled systemd and disabled drive automount/fstab/Windows interoperability only in dtd-sandbox. Existing Docker Desktop was unchanged. No unauthenticated daemon TCP socket opened. First systemd start failed because the shell package install consumed remaining stdin; wrote wsl.conf explicitly, restarted only the project distribution, and verified systemd/mounts.

Added sandbox:wsl wrapper for allowlisted reviewed source sync and fixed preflight/probe. Built pinned Python probe image, passed all eight real isolation checks under runsc. Tightened read-only check to require EROFS on a world-writable image file; negative control without read-only was correctly rejected. No dtd-probe containers remained. Generated execution remains false. B01 now PARTIAL; resource/termination and broker/parser integration remain.

Validation: nine execution unit tests passed; npm run check passed (four protocol tests; Python 53 passed/33 PostgreSQL skipped; lint/types/contracts/build). Prior PostgreSQL/browser suites unchanged, not rerun. Versions/digests, reproducible commands and limits are in docs/SANDBOX_WSL.md and dated evidence. Next: real resource/timeout/cancel tests, then isolated CSV/SQLite inspection. Authorized milestone commit/push follows.

## 2026-09-17 — Real resource and termination acceptance

Added fixed bounded gVisor resource image and sandbox:wsl resources command. Seven real cases pass: tmpfs ENOSPC, guest fork EAGAIN, memory OOM kill, retained output cap, observed cgroup CPU throttling, deadline kill and cancellation of parent plus children. Repeated all eight basic isolation checks under final policy; no probe containers remain. Limits separate 128 host tasks from guest RLIMIT_NPROC 32 (ADR-021).

Found and fixed two issues: 32 host tasks caused runtime exit rather than controlled guest fork failure; output flood blocked Docker attach after kill because the reader stopped draining. Excess data is now discarded while draining, retaining at most 64 KiB. Actual final suite passed; image digest and measured evidence in docs/evidence/2026-09-17-resource-probes.md.

npm run check passed: four JS tests, 53 Python passed/33 PostgreSQL skipped, lint/format/types/contracts/build. Unchanged PostgreSQL/browser suites not rerun. Two existing upstream warnings and Docker legacy-builder warning remain. B01 stays partial for adversarial parser and broker-death/integration checks. Next: bounded isolated CSV/SQLite inspector with safe transfer/results and application integration; no upload parsing or arbitrary execution enabled by this milestone. Standing authorization covers commit/push.

## 2026-09-18 — Detailed progress report and compact chat handoff

At user request, reconciled session memory, task ledger, dated evidence and eight implementation commits into docs/PROGRESS_REPORT.md. Covers 11 delivered work areas, exact boundaries, issues fixed, validation provenance, remaining roadmap and operating commands. Created memory/CHAT_HANDOFF.md as a compact portable continuation summary; no available tool can force internal chat compaction, and no such action is claimed. Updated memory index, task/state and stale README status. Preserved full session history.

Validation: checked all local links in the report/handoff/index/README and verified all eight referenced implementation commits exist. Documentation-only change; application tests not rerun. User-authorized documentation milestone commit/push follows.

## 2026-09-18 — Isolated CSV/SQLite inspection and workspace previews

Delivered fixed parser image, bounded stdin/results, gVisor execution, per-container cleanup and independent systemd orphan reaper. Added durable PostgreSQL inspection migration, owner/CSRF API, one-active-job admission, lease/token publication fencing, three-attempt recovery and strict result/lineage validation. Reviewed React now requests inspection and shows tables, counts and five rows. Raw originals unchanged; no cleaning/modeling/generated execution enabled. Added runbook, ADR-022, evidence, current memory and corrected stale status docs.

Validation: npm run test:postgres 103 passed; npm run check passed with four JS tests, 62 Python passed/41 PG-only skipped, lint/format/types/contracts/build. Actual gVisor inspector suite 16 cases passed. Opt-in browser journey with sample245x11 passed, including mobile overflow check; screenshots reviewed after readable cell-width correction. Orphan cleanup observed after WSL startup, not a measured crash SLA. Two existing Python deprecation warnings remain.

Fixed report publication after lineage rejection, strict error-code digit handling, concurrent SQLite test-harness connection reuse and mobile preview layout. Restarted project-owned PostgreSQL after it was found stopped; local image configuration added only to ignored .env. Remaining: persistent table choice/CSV overrides, then profiling/artifacts. Full death-matrix, running cancellation and production broker remain incomplete. User-authorized milestone commit/push follows; Git history records the resulting commit.

## 2026-09-18 — Delimiter revisions and saved dataset version

Added explicit CSV delimiter choice and bounded reinspection of unchanged raw bytes. Corrected Windows-to-WSL semicolon transport with fixed name codes. A new inspection revision clears the previous report and selected table. Saving an inspected table now creates an owner-scoped dataset-version record with table, effective delimiter, raw hash and schema fingerprint; the current version ID survives refresh. Added two migrations, contracts, UI controls, cross-owner/invalid-choice tests and runbook/ADR-023 updates.

Validation: 105 PostgreSQL-backed tests passed; npm run check passed four JS tests, 63 Python passed/42 PostgreSQL-only skipped, lint/types/contracts/build. The rebuilt image passed 18 real gVisor parser cases. The opt-in Chromium journey passed delimiter changes, cleared/re-saved table choice and persistence after reload. Migration SQLite parity initially failed on ALTER CONSTRAINT; batch migration fixed it. Earlier generic isolation/resource suites were not rerun. Project API/worker were restarted after migrating; HTTP 200 and worker-ready output verified. No generated analysis/modeling enabled. Next: B07 deterministic profiling and validated artifacts. Authorized milestone commit/push follows.

## 2026-09-18 — Selected-table profiling and validated report

Added fixed gVisor profile pass for the currently saved dataset version. It counts missing/distinct/numeric-looking/other values, finite numeric ranges and top-five values for each column. Added durable fenced profile claims, owner-scoped API, strict schema/lineage checks, canonical SHA-256 report fingerprint, migration, generated contracts and reviewed React profile table. A changed selection removes access to prior profile. No generated Pandas or model execution enabled.

Validation: 109 PostgreSQL-backed tests passed; npm run check passed 4 JS tests, 65 Python passed/44 PostgreSQL-only skipped, lint/format/types/contracts/build. Rebuilt image passed 20 real gVisor inspector/profile cases, including sample CSV and selected SQLite table. Opt-in Chromium journey passed end-to-end profiling and mobile overflow check; screenshot reviewed. Fixed numeric accumulation to use bounded aggregates and corrected mobile overflow. Earlier general resource/renderer suites not rerun. Two upstream Python warnings remain. Next: B08 generated Pandas cleaning/provenance with stronger execution boundary and run-scoped artifacts. Authorized milestone commit/push follows.

## 2026-09-21 — Generated Pandas cleaning workflow and provenance (Milestone B08)

Delivered Milestone B08: generated Pandas cleaning workflow with column lineage and provenance tracking, isolated execution in gVisor, run-scoped immutable artifacts, and analysis run lifecycle orchestration.

- Built and pinned dedicated transformer container (`sandbox/transformer/Dockerfile`) with pandas==2.2.3 on python:3.13-slim.
- Implemented in-container binary framing protocol (`transform_data.py`), Linux broker (`scripts/sandbox-transform.py`), and host execution boundary (`run_isolated_transform`).
- Implemented deterministic cleaning plan and Pandas code generator (`cleaning_generator.py`) with AST safety validation.
- Created analysis run orchestration (`POST /projects/{project_id}/runs`, stage progression `clean_dataset`), and run-scoped immutable artifact store (`Artifact` model, SHA-256 integrity verification, owner-isolated retrieval and download).
- Fixed Windows telemetry hook path issue and resolved circular dependency in API artifacts module.

Validation:

- `npm run test:postgres`: 114 passed (0 failures, 0 skips).
- `npm run check`: 4 JS tests, 69 Python tests passed (45 PG skipped), lint, format, type check, contracts, and builds passed cleanly.
- Real gVisor acceptance suite (`test-transformer.py`): passed on `samples/synthetic-sales-messy.csv` (245 rows -> 240 rows, 5 duplicates dropped, whitespace stripped), verified safe rejection of failing scripts and invalid return types.
- Unit suite `test_cleaning.py`: AST validation, safe identifier normalization, and serialization passed.
  Authorized milestone commit/push follows. Next: B09 Baseline evaluation.

## 2026-09-21 — Baseline evaluation in gVisor sandbox (Milestone B09)

Delivered Milestone B09: deterministic baseline evaluation workflow generation, strict feature selection, train/test splitting before fitting preprocessing to prevent data leakage, isolated execution in gVisor, and run-scoped evaluation reports.

- Implemented baseline contracts (`baseline_contracts.py`) defining `BaselineReport`, `ModelMetrics`, `SplitInfo`, and `FeatureInfo`.
- Implemented deterministic baseline workflow generator (`baseline_generator.py`) supporting both `regression` and `classification` tasks, automatic identifier/leakage column exclusion, target class balance validation (minimum 10 rows per class, 2-20 classes), `train_test_split` (80/20, seed 42) before any preprocessing fitting (`StandardScaler`, `OneHotEncoder`), and fitting a reference dummy model against a candidate model (`Ridge` for regression, `LogisticRegression` for classification).
- Implemented `run_baseline` execution handler in sandbox transformer (`sandbox/transformer/transform_data.py`), safely compiling and executing generated baseline scripts in an isolated namespace containing only `pd` and `np`, with NUL byte detection, size limits, and SHA-256 validation. Rebuilt and pinned transformer image.
- Updated `run_engine.py` to orchestrate `train_baseline` stage, retrieving the `cleaned.csv` artifact from the prior `clean_dataset` stage and saving the baseline evaluation report to run checkpoint and artifact storage.
- Added support for `target_column` and `task_type` in `AnalysisRunCreate` contract and run creation endpoint (`runs.py`).

Validation:

- `tests/python/test_baseline.py`: 5 unit tests covering classification, regression, feature exclusion, and skip conditions passed.
- `tests/python/test_runs.py`: lifecycle and artifact tests updated and passed.
- `scripts/test-transformer.py`: end-to-end gVisor acceptance test passed in isolated container (Dummy MAE: 228.24 vs Ridge MAE: 73.47; verified script failure and invalid return type rejections).
- `npm run check`: lint, format, typecheck (mypy), protocol tests, 74 Python tests passed cleanly.
- Milestone committed (`78c8e7b`) and pushed to remote `main`. Next: B10 Analysis rendering & layout.

## 2026-09-21 — Dashboard Specification, Query Broker, and Fallback UI (Milestone B10)

Delivered Milestone B10: validated Dashboard Specification v1, allowlisted server-side Query Broker with 500-point chart capping and 100-row table pagination, stage progression `plan_dashboard`, and accessible reviewed React Fallback UI.

- Defined contracts (`dashboard_contracts.py`): `DashboardSpec`, `KpiSpec`, `ChartSpec`, `FilterSpec`, `TableSpec`, `DashboardQueryRequest`, `DashboardQueryResponse`, and `DashboardView`.
- Implemented deterministic specification generator (`dashboard_generator.py`) conforming to v1 limits (<=6 KPIs, <=6 charts, <=4 filters, table spec) based on `ProfileReport`, `CleaningReport`, and `BaselineReport`. Matches charts to actual data types and forbids fabricated time series if dates are absent.
- Extended run state machine (`run_engine.py`) with `plan_dashboard` stage, generating the spec artifact (`kind="dashboard_spec"`), checkpointing the summary, and creating the `Dashboard` database record with `render_mode="fallback"`.
- Implemented allowlisted server query broker (`query_broker.py`) using pure Python standard library to filter, aggregate, bin, and paginate over `cleaned.csv` artifacts without executing client-provided code.
- Added API routes (`runs.py`): `GET /runs/{run_id}/dashboard` and `POST /runs/{run_id}/queries`.
- Built accessible React Fallback UI (`apps/web/DashboardFallback.tsx`) with status banner, interactive filter bar, KPI cards, SVG Bar/Histogram/Line/Scatter charts, paginated sortable table, and integrated into workspace shell (`apps/web/main.tsx`).

Validation:

- `npm run check:python`: 31 files clean, Ruff format/lint and strict Mypy passed.
- `npm run test:python`: 84 unit and integration tests passed (45 PostgreSQL parity skips).
- `tests/python/test_dashboard_generator.py`: 2 tests covering spec limits and baseline model integration passed.
- `tests/python/test_query_broker.py`: 8 tests covering filtering, chart capping, binning, and security passed.
- `tests/python/test_runs.py`: 3-stage lifecycle test passed.
- `npm run test:postgres`: All 129 tests passed against local PostgreSQL 17 engine (0 failures, 0 skips).
- `npm run contracts:check`: Generated contracts and TypeScript types in sync.
- `npm run build`: Both renderer lab and workspace web UI built cleanly.
- Next: Milestone B11 (Generated React pipeline).
