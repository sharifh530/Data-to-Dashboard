# Current project state

Last updated: 2026-09-17

## Implemented

B05 raw storage now joins B06 synthetic runs and local authentication. The full autonomous analyst remains under construction; B05 inspection is still blocked.

- Local-only FastAPI, 17 metadata tables/migrations, operator-issued login, hashed sessions, CSRF and owner-scoped projects.
- Raw byte upload storage in PostgreSQL, 10 MiB/file and 50 MiB/owner limits, checksums, idempotency and owner-only downloads. See docs/UPLOAD_STORAGE.md.
- PostgreSQL transactional outbox/work items, fenced leases, bounded recovery/checkpoints, synthetic run admission/history/detail, SSE replay/snapshot and cancellation.
- Generated contracts, lockfiles, checks and CI definition; React isolation lab; runtime preflight/fixed probe tooling.
- See docs/RUN_PROCESSING.md and docs/PERSISTENCE_AND_AUTH.md for actual behavior.

## Validation

npm run check passed: 4 protocol tests, 52 Python passed/31 PostgreSQL skipped, lint/types/contracts/build. After adding the concurrency case, npm run test:postgres passed all 84 with no skips and npm run check:python passed. npm run db:check: no drift. Two upstream test-client warnings remain. Renderer unchanged; browser tests not rerun. See docs/evidence/2026-09-17-upload-storage.md.

## Limitations

B01 remains blocked: preflight again reports DOCKER_UNAVAILABLE. Raw files are opaque and awaiting isolated inspection. Hosted identity, parsing, production object storage, LangChain/LangGraph, modeling, generated execution/builds and product screens remain unimplemented. Actual executor cancellation is future integration. No hosted deployment or paid service exists.

## Source control and local services

User authorized milestone pushes to https://github.com/sharifh530/Data-to-Dashboard.git. Branch main, remote origin; fetch first, preserve history, never force-push, verify remote hash. See Git history for publication state.

Project-owned PostgreSQL listens on 127.0.0.1:55432; ignored .local/postgres/data and .env hold local state/credentials. It was restarted this session. Verify liveness before reuse; leave system databases untouched. Start API/worker with npm run dev:api / npm run dev:worker. No persistent worker was left running; --once was tested. Tooling worktrees under .kilo are excluded from lint/Git.

## Next concrete action

Resolve B01 dedicated Linux Docker/runsc for B05 isolated inspection, selection and preview. Raw storage slice is complete. Never parse uploads or execute generated code on the API/developer host. If runtime remains unavailable, add the authenticated product shell/upload/history UX against implemented endpoints, clearly showing inspection blocked. Hosted release still requires B04H.

## Open decisions

Execution/hosting provider, hosted identity, LLM/model/budget and product design. Never store credentials, issued tickets, private data or raw provider payloads in Git/memory.
