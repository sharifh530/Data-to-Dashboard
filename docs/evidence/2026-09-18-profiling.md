# Selected-table profiling acceptance — 2026-09-18

Delivered fixed profile mode in the reviewed gVisor inspector, durable version-scoped profile jobs, strict result contracts, SHA-256 artifact fingerprint, owner-only API and responsive workspace table. The worker rechecks current selection and ownership before publication. It never executes uploaded parsers on the host.

Executed evidence:

- `npm run test:postgres`: **109 passed**, no skips. Migration upgrade/downgrade and profile ownership, idempotency, lineage failure, artifact fingerprint and stale-selection access are included. These API tests mock execution.
- `npm run check`: **4 JavaScript tests; 65 Python passed, 44 PostgreSQL-only skipped**; lint, format, type checks, contracts and builds passed.
- `node scripts/python.mjs scripts/test-inspector.py --image <rebuilt image>`: **20 real gVisor cases**, including full-table profiling of the 245-row CSV and a chosen SQLite table. Results validated against strict profile contracts.
- Opt-in `npm run test:web` with `DTD_TEST_INSPECTION_IMAGE` pointing to the rebuilt image: Chromium upload → inspect → revise delimiter → save table → profile → refresh journey passed. A 390px viewport had no document overflow; screenshot inspected. The browser test uses an ephemeral SQLite metadata database and actual gVisor parsing.

Two existing upstream Python deprecation warnings and the Docker legacy-builder warning remain. Earlier generic resource/renderer suites were not rerun. Limits and private-data semantics are in [PROFILING.md](../PROFILING.md). This is a local development acceptance, not a hosted security certification or generated analysis pipeline.
