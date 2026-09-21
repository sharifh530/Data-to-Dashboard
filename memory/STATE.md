# Current project state

Last updated: 2026-09-21

## Implemented

- Local FastAPI/PostgreSQL, operator-issued tickets, hashed sessions, CSRF/Origin checks and owner-scoped projects. Hosted startup disabled.
- Raw byte uploads: 10 MiB/file, 50 MiB/owner, checksums, idempotency and owner-only downloads. Synthetic sample: samples/synthetic-sales-messy.csv, 245 rows/11 columns.
- Fixed CSV/SQLite inspection and profiling run only inside dedicated WSL gVisor. Durable jobs, fenced leases, three-attempt recovery, strict bounded reports and hash/format validation. Independent timer reaps expired containers.
- Reviewed React workspace at port 8000 offers Inspect dataset, table previews, row/column/empty counts and five sample rows, delimiter revision, durable dataset versioning, and profile report visualization.
- NEW (B08): Bounded generated Pandas cleaning workflow with column lineage and provenance tracking. Dedicated pinned transformer container in WSL gVisor (`runsc`), binary stdin/stdout framing, strict resource caps (1 CPU, 512MB RAM, 60s timeout, 10MB output cap). AST safety validation for generated code.
- NEW (B08): Analysis run orchestration (`POST /projects/{project_id}/runs`, stage progression `clean_dataset`), and run-scoped immutable artifact store (`Artifact` model, SHA-256 integrity verification, owner-isolated retrieval and download).
- PostgreSQL outbox/leases/checkpoints/SSE and cancellation for runs. Generated contracts, migrations, locked dependencies and checks. Separate reviewed renderer lab on 4173/4174.
- dtd-sandbox WSL2 Ubuntu, Docker/runsc; pinned inspector and transformer images.

- NEW (B10): Validated Dashboard Specification v1 generator, allowlisted server-side Query Broker with 500-pt chart caps and 100-row table pagination, stage progression `plan_dashboard`, and accessible reviewed React Fallback UI with SVG charts and interactive filters.

## Validation

September 21: `npm run test:postgres` 129 passed (0 failures, 0 skips); `npm run check` passed 4 JS tests, 84 Python passed (45 PG skipped), lint, format, type checks, contracts, and builds passed cleanly. Evidence: docs/evidence/2026-09-21-dashboard-specification.md.

## Limitations and next concrete action

B01/B05/B07/B12 remain partial; B08, B09, and B10 are complete.
Current Phase: Milestone B10 (Dashboard specification, query broker, fallback UI)
Status: Completed! Validated specification generation conforming to v1 limits, secure query broker over cleaned dataset artifacts, and accessible React fallback UI with SVG charts and pagination are fully tested and verified against PostgreSQL.

Next concrete action: Milestone B11 (Generated React pipeline): isolated compilation of generated React dashboard components in sandbox, iframe bridge with CSP, and end-to-end integration.

## Local operations and source control

Project PostgreSQL: 127.0.0.1:55432, ignored .local/postgres/data and .env; leave system databases untouched. Configure the pinned inspector image and runtime per docs/INSPECTION.md. Start npm run dev:api / npm run dev:worker; verify liveness before reuse. Generated execution remains disabled. Never parse uploads on the API/developer host.

User authorized milestone pushes to https://github.com/sharifh530/Data-to-Dashboard.git. Branch main/origin; fetch first, preserve history, never force-push and verify remote hash. Git history records publication. Keep credentials/private data/raw provider payloads out of Git and memory.

Historical task detail: docs/PROGRESS_REPORT.md and memory/SESSION_LOG.md. memory/CHAT_HANDOFF.md is the prior portable snapshot with a current-state pointer; internal application chat compaction was not tool-accessible. Open decisions: hosted identity, hosting/execution provider, LLM/model/budget and later product design.

Session-end service check: project PostgreSQL running; both new migrations and schema check passed; API returned HTTP 200 on port 8000; local worker reported ready. Both were restarted with the rebuilt pinned inspector configured in ignored .env. Recheck after host/app restarts.

Local service check: new profile migration/schema check passed; API returned HTTP 200 on port 8000; worker reported ready with rebuilt pinned image configured in ignored .env. Both were left running. Recheck after host/app restarts.
