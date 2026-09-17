# Current project state

Last updated: 2026-09-17

## Objective

Build the documented autonomous CSV/SQLite analyst. The current milestone implements persistence and local authenticated project access (B03/B04); hosted identity is explicitly tracked as B04H.

## Implemented

- Local FastAPI: liveness, unavailable analysis readiness, capability reporting, hosted-startup rejection.
- PostgreSQL metadata with 15 application tables and Alembic migrations; no implicit table creation. Composite foreign keys enforce project/run lineage.
- Operator-issued single-use login, hashed server sessions, origin/CSRF checks, logout, and owner-scoped project creation/list/read with idempotency and pagination.
- Python schemas, generated OpenAPI/TypeScript, contract drift checks.
- React isolation lab: synthetic filtering, MessageChannel scoping, hash-based CSP, reset/fallback.
- Runtime preflight, fixed probe policy, bounded synthetic-image launcher and Dockerfile. No arbitrary-code executor.
- Exact npm/uv lockfiles, checks, and CI workflow (not run remotely).
- Getting-started guide and dated evidence; planning package remains the product specification.

## Validation

`npm run check` passes (4 protocol tests; default Python run 35 passed/12 PostgreSQL cases skipped). `npm run test:postgres` passes all 47 Python cases with no skips; `npm run db:check` reports no drift. Previous 5 Chromium tests are unchanged and were not rerun for this backend milestone. Two upstream test-client warnings remain. See `docs/evidence/2026-09-17-persistence-auth.md`.

## Blocker and missing features

Docker isolation is still unverified; do not enable generated execution or mark B01 complete. Hosted identity, queues/workers, uploads, LLM/modeling, generated-source builds, and product screens remain unimplemented. Local authentication is not hosted SSO. No deployment or paid service exists.

## Source control

The user authorized `https://github.com/sharifh530/Data-to-Dashboard.git` as the project repository and routine pushes after every completed major task. Local branch: `main`; remote: `origin`. Commit verified milestone changes with updated memory, fetch/reconcile remote changes without force-pushing, and verify the pushed commit. See Git history for the latest publication state.

## Local sessions

Project-owned PostgreSQL uses `127.0.0.1:55432` with `.local/postgres/data`; ignored `.env` contains its URL. The helper leaves the system PostgreSQL service alone. The database stopped between sessions and was restarted; connection attempts are now bounded to five seconds. Verify database/API/lab liveness before reuse. API/lab commands and sign-in examples are in `docs/PERSISTENCE_AND_AUTH.md` and `docs/GETTING_STARTED.md`. Stop only this project's processes.

## Next concrete action

Advance B06 durable run/outbox/progress orchestration using synthetic fixtures while B05 isolated upload parsing depends on resolving B01. Recheck Docker/runtime availability, run the fixed probe on a dedicated Linux runtime, and extend resource/cancellation/escape tests before enabling generated execution. Implement B04H before hosted release.

## Pending decisions

Execution/hosting provider, hosted identity provider, LLM/model/budget, product design. Local database credentials are generated and ignored; local sign-in tokens are operator-issued and must never enter Git/memory. No deadline is assumed.
