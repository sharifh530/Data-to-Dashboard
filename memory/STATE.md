# Current project state

Last updated: 2026-09-17

## Implemented

Uploadable test fixture: `samples/synthetic-sales-messy.csv` (245 rows, 11 columns, fictional sales with deliberate quality issues). Validated with the standard CSV reader; see samples/README.md. Actual upload inspection remains disabled.

B12 local workspace UI now connects B05 raw storage and B06 synthetic runs to local authentication. The full autonomous analyst remains under construction; B05 inspection is still blocked.

- Local-only FastAPI, 17 metadata tables/migrations, operator-issued login, hashed sessions, CSRF and owner-scoped projects.
- Raw byte upload storage in PostgreSQL, 10 MiB/file and 50 MiB/owner limits, checksums, idempotency and owner-only downloads. See docs/UPLOAD_STORAGE.md.
- Reviewed React workspace at API port 8000: local sign-in, project selection/creation, uploads, paginated stored files/downloads, sample history, polling/cancel and logout. See docs/WORKSPACE_UI.md. Port 4173 is still the separate renderer lab.
- PostgreSQL transactional outbox/work items, fenced leases, bounded recovery/checkpoints, synthetic run admission/history/detail, SSE replay/snapshot and cancellation.
- Generated contracts, lockfiles, checks and CI definition; React isolation lab; runtime preflight/fixed probe tooling.
- See docs/RUN_PROCESSING.md and docs/PERSISTENCE_AND_AUTH.md for actual behavior.
- Dedicated `dtd-sandbox` WSL2 Ubuntu environment, Docker 29.1.3 and runsc 20260914.0. Eight actual isolation probes plus writable-root negative control passed. Runbook: docs/SANDBOX_WSL.md. Application execution remains disabled.

## Validation

npm run check passed: 4 protocol tests, 53 Python passed/33 PostgreSQL skipped, lint/types/contracts/build. npm run test:postgres passed all 86 with no skips. npm run test:web passed the real API Chromium journey; desktop/mobile screenshots visually inspected and mobile overflow checked. Final UI copy fixes passed lint/types and repeated test:web. Existing renderer tests unchanged, not rerun. Two upstream test-client warnings remain. See docs/evidence/2026-09-17-workspace-ui.md.

## Limitations

B01 is now partial, not runtime-blocked: dedicated WSL gVisor is available and basic probes pass. Resource/exhaustion, cancellation/termination, adversarial parser tests and broker integration remain. Raw files still await isolated inspection. Hosted identity, parsing, production storage, LangChain/LangGraph, modeling, generated execution/builds and analysis/dashboard screens remain unimplemented. No hosted deployment or paid service exists.

## Source control and local services

User authorized milestone pushes to https://github.com/sharifh530/Data-to-Dashboard.git. Branch main, remote origin; fetch first, preserve history, never force-push, verify remote hash. See Git history for publication state.

Project-owned PostgreSQL listens on 127.0.0.1:55432; ignored .local/postgres/data and .env hold local state/credentials. It was restarted this session. Verify liveness before reuse; leave system databases untouched. Start API/worker with npm run dev:api / npm run dev:worker. No persistent worker was left running; --once was tested. Tooling worktrees under .kilo are excluded from lint/Git.

## Next concrete action

Extend the real dtd-sandbox probes to resource limits and whole-container timeout/cancellation cleanup, then implement bounded isolated CSV/SQLite inspection and broker/result validation. Use `npm run sandbox:wsl -- sync` / `preflight` / `probe --image <digest>`; ordinary Windows Docker context still lacks runsc. Pinned image/version evidence: docs/evidence/2026-09-17-wsl-sandbox.md. Never parse uploads or execute generated code on the API/developer host. Hosted release still requires B04H.

## Open decisions

Execution/hosting provider, hosted identity, LLM/model/budget and product design. Never store credentials, issued tickets, private data or raw provider payloads in Git/memory.
