# Current project state

Last updated: 2026-09-18

## Implemented

- Local FastAPI/PostgreSQL, operator-issued tickets, hashed sessions, CSRF/Origin checks and owner-scoped projects. Hosted startup disabled.
- Raw byte uploads: 10 MiB/file, 50 MiB/owner, checksums, idempotency and owner-only downloads. Synthetic sample: samples/synthetic-sales-messy.csv, 245 rows/11 columns.
- NEW: fixed CSV/SQLite inspection runs only inside dedicated WSL gVisor. Durable jobs, 90-second fenced leases, three-attempt recovery, strict bounded reports and hash/format validation. Independent timer reaps expired inspector containers; broker checks timer availability and removes containers before returning reports.
- Reviewed React workspace at port 8000 offers Inspect dataset, table previews, row/column/empty counts and five sample rows, plus projects/uploads/downloads/sample history/cancel. CSV delimiter choices now trigger bounded reinspection; saving a table creates a durable dataset version with input hash and schema fingerprint.
- PostgreSQL outbox/leases/checkpoints/SSE and cancellation for fixed synthetic runs. Generated contracts, migrations, locked dependencies and checks. Separate reviewed renderer lab on 4173/4174.
- dtd-sandbox WSL2 Ubuntu, Docker/runsc; earlier eight isolation and seven resource probes passed. Windows automount/interop disabled; Docker Desktop unchanged.

## Validation

September 18 latest: npm run test:postgres 105 passed; npm run check 4 JS tests and 63 Python passed/42 PG skipped, lint/format/types/contracts/build passed. Real inspector suite: 18 gVisor cases passed. Opt-in Chromium journey with actual gVisor and the 245-row sample passed, including delimiter revisions, saved table and reload. Earlier mobile overflow checked and screenshots reviewed; independent orphan cleanup observed after WSL startup. Two existing Python deprecation warnings remain. Evidence: docs/evidence/2026-09-18-inspection-configuration.md and inspection.md. Earlier resource/renderer suites not rerun.

## Limitations and next concrete action

B01/B05/B12 remain partial. Table selection and delimiter choice now persist; next implement B07 deterministic profiling and immutable artifact manifests from a selected dataset version. Encoding/header overrides and broader ingestion acceptance remain B05. No LangChain/Pandas generation, cleaning, model fitting, generated React build, production broker or hosted deployment exists yet. Inspection readiness does not imply analysis readiness. Running inspection cancellation returns 409; queued jobs can cancel. Same-setting retry is not implemented. Future deletion APIs need concurrent publication tests. The reaper is local recovery, not a hard guarantee across host suspension or daemon failure.

## Local operations and source control

Project PostgreSQL: 127.0.0.1:55432, ignored .local/postgres/data and .env; leave system databases untouched. Configure the pinned inspector image and runtime per docs/INSPECTION.md. Start npm run dev:api / npm run dev:worker; verify liveness before reuse. Generated execution remains disabled. Never parse uploads on the API/developer host.

User authorized milestone pushes to https://github.com/sharifh530/Data-to-Dashboard.git. Branch main/origin; fetch first, preserve history, never force-push and verify remote hash. Git history records publication. Keep credentials/private data/raw provider payloads out of Git and memory.

Historical task detail: docs/PROGRESS_REPORT.md and memory/SESSION_LOG.md. memory/CHAT_HANDOFF.md is the prior portable snapshot with a current-state pointer; internal application chat compaction was not tool-accessible. Open decisions: hosted identity, hosting/execution provider, LLM/model/budget and later product design.

Session-end service check: project PostgreSQL running; both new migrations and schema check passed; API returned HTTP 200 on port 8000; local worker reported ready. Both were restarted with the rebuilt pinned inspector configured in ignored .env. Recheck after host/app restarts.
