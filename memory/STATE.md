# Current project state

Last updated: 2026-09-17

## Implemented

B06 durable local synthetic run processing now joins PostgreSQL persistence and local authentication. The full autonomous analyst remains under construction.

- Local-only FastAPI, 16 metadata tables/migrations, operator-issued login, hashed sessions, CSRF and owner-scoped projects.
- PostgreSQL transactional outbox/work items, fenced leases, bounded recovery/checkpoints, synthetic run admission/history/detail, SSE replay/snapshot and cancellation.
- Generated contracts, lockfiles, checks and CI definition; React isolation lab; runtime preflight/fixed probe tooling.
- See docs/RUN_PROCESSING.md and docs/PERSISTENCE_AND_AUTH.md for actual behavior.

## Validation

npm run check passes: 4 protocol tests, 48 Python passed/28 PostgreSQL skipped, lint/types/contracts/build. npm run test:postgres: all 76 passed, no skips. npm run db:check: no drift. npm run dev:worker -- --once: successful startup/exit. Two upstream test-client warnings remain. Existing 5 Chromium tests were unchanged and not rerun. See docs/evidence/2026-09-17-run-processing.md.

## Limitations

B01 hardened runtime remains blocked. Synthetic stages use reviewed fixed aggregates only. Hosted identity, uploads/parsing/storage, LangChain/LangGraph, modeling, generated execution/builds and product screens remain unimplemented. Actual executor cancellation is future integration. No hosted deployment or paid service exists.

## Source control and local services

User authorized milestone pushes to https://github.com/sharifh530/Data-to-Dashboard.git. Branch main, remote origin; fetch first, preserve history, never force-push, verify remote hash. See Git history for publication state.

Project-owned PostgreSQL listens on 127.0.0.1:55432; ignored .local/postgres/data and .env hold local state/credentials. It was restarted this session. Verify liveness before reuse; leave system databases untouched. Start API/worker with npm run dev:api / npm run dev:worker. No persistent worker was left running; --once was tested. Tooling worktrees under .kilo are excluded from lint/Git.

## Next concrete action

Recheck dedicated Linux Docker/runsc availability and resolve B01 for B05 isolated CSV/SQLite inspection. Run fixed probes plus resource/termination checks before enabling generated execution. If blocked, implement bounded immutable upload storage with parsing explicitly disabled. Never parse untrusted files on the API/developer host. B04H remains required before hosted release.

## Open decisions

Execution/hosting provider, hosted identity, LLM/model/budget and product design. Never store credentials, issued tickets, private data or raw provider payloads in Git/memory.
