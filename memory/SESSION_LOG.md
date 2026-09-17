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
