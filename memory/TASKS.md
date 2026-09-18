# Task status ledger

Last updated: 2026-09-18. Detailed scope/dependencies: [roadmap](../docs/ROADMAP.md).

| ID | Status | Deliverable / next action |
| --- | --- | --- |
| DOC-01 | DONE | Initial specification and memory package; see session log for validation |
| DOC-02 | DONE | Detailed task-by-task PROGRESS_REPORT.md and compact CHAT_HANDOFF.md, reconciled against memory/evidence/Git history. Internal chat compaction is not tool-accessible. |
| SAMPLE-01 | DONE | Uploadable synthetic sales CSV: 245 rows/11 columns with deliberate quality issues; samples/README.md records validation. |
| B01 | PARTIAL | Eight isolation/seven resource probes previously passed; 16 real parser cases and independent orphan cleanup now verified. Fixed inspector broker integrated. Production broker, full death/failure matrix and running cancellation remain. docs/evidence/2026-09-18-inspection.md. |
| B02 | DONE | Local API/React lab scaffold, lockfiles, checks, CI definition, setup guide. Evidence: docs/evidence/2026-09-16-foundation.md. Product UI remains future work. |
| B03 | DONE | Metadata models/migration, generated contracts, upgrade/downgrade recovery and PostgreSQL schema checks. Evidence: docs/evidence/2026-09-17-persistence-auth.md. |
| B04 | DONE | Local operator-issued login, hashed sessions, CSRF, project ownership and concurrent idempotency tests. Hosted authentication is B04H, not completed. |
| B04H | TODO | Required before hosted release: identity provider, abuse controls, HTTPS/browser sign-in and recovery integration. |
| B05 | PARTIAL | Raw storage, isolated CSV/SQLite preview, durable table choice/dataset version and bounded CSV delimiter override complete (2026-09-18). Encoding/header overrides and full ingestion acceptance remain. Evidence: docs/evidence/2026-09-18-inspection-configuration.md. |
| B06 | DONE (synthetic scope) | PostgreSQL outbox/leases/checkpoints, SSE/history/cancel and process recovery. Evidence: docs/evidence/2026-09-17-run-processing.md. Executor cancellation/LangGraph remain B01/B08. |
| B07 | TODO | Profiling and validated artifacts |
| B08 | TODO | Generated Pandas workflow |
| B09 | TODO | Baseline evaluation |
| B10 | TODO | Dashboard specification/query/fallback |
| B11 | TODO | Generated React pipeline |
| B12 | PARTIAL | Local shell, projects, upload/download, isolated previews, delimiter and table configuration, sample history/cancel implemented. Dashboard/model UX and exports remain. docs/evidence/2026-09-18-inspection-configuration.md. |
| B13 | TODO | Retention, deletion, quotas, controls |
| B14 | TODO | Release verification and operational rehearsal |
| B15 | TODO | Post-MVP dashboard revisions |
| B16 | TODO | Post-MVP joins/scale |

For active work add owner/session, start date, acceptance evidence, and blockers. Do not mark implementation complete solely because its design document exists.
