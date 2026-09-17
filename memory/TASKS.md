# Task status ledger

Last updated: 2026-09-17. Detailed scope/dependencies: [roadmap](../docs/ROADMAP.md).

| ID | Status | Deliverable / next action |
| --- | --- | --- |
| DOC-01 | DONE | Initial specification and memory package; see session log for validation |
| B01 | BLOCKED | Browser fixture tests pass; Python/runtime/resource verification needs working dedicated Linux + runsc. Preflight and fixed probe tooling ready. |
| B02 | DONE | Local API/React lab scaffold, lockfiles, checks, CI definition, setup guide. Evidence: docs/evidence/2026-09-16-foundation.md. Product UI remains future work. |
| B03 | DONE | Metadata models/migration, generated contracts, upgrade/downgrade recovery and PostgreSQL schema checks. Evidence: docs/evidence/2026-09-17-persistence-auth.md. |
| B04 | DONE | Local operator-issued login, hashed sessions, CSRF, project ownership and concurrent idempotency tests. Hosted authentication is B04H, not completed. |
| B04H | TODO | Required before hosted release: identity provider, abuse controls, HTTPS/browser sign-in and recovery integration. |
| B05 | TODO | Upload/CSV/SQLite inspection |
| B06 | TODO | Durable queue, run states, SSE, cancellation |
| B07 | TODO | Profiling and validated artifacts |
| B08 | TODO | Generated Pandas workflow |
| B09 | TODO | Baseline evaluation |
| B10 | TODO | Dashboard specification/query/fallback |
| B11 | TODO | Generated React pipeline |
| B12 | TODO | Product UX/history/exports |
| B13 | TODO | Retention, deletion, quotas, controls |
| B14 | TODO | Release verification and operational rehearsal |
| B15 | TODO | Post-MVP dashboard revisions |
| B16 | TODO | Post-MVP joins/scale |

For active work add owner/session, start date, acceptance evidence, and blockers. Do not mark implementation complete solely because its design document exists.
