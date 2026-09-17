# Architecture decision register

All decisions below are **proposed defaults**, dated 2026-09-16. Mark accepted after implementation evidence or explicit agreement; mark superseded with a successor link rather than deleting history.

Foundation update: React/TypeScript, FastAPI, npm, uv, and the isolated fixture bridge are implemented. Only the foundation portions of ADR-001/005/009 are accepted; unimplemented product/production behavior remains proposed. Explicitly accepted additions appear below.

| ADR | Decision | Rationale and consequence |
| --- | --- | --- |
| ADR-001 | React/TypeScript frontend and FastAPI/Python backend | Keeps UI code generation native to React and analysis native to Pandas; requires shared generated contracts. |
| ADR-002 | LangChain tools with explicit LangGraph workflow | Meets agent requirement while making retries/state visible; requires durable checkpoints and idempotent stage effects. |
| ADR-003 | PostgreSQL source of truth, queue/outbox for delivery | Separates durable state from at-least-once jobs; introduces outbox and lease recovery work. |
| ADR-004 | Independent hardened execution broker | Generated code must not share trust with API; hosting choice depends on a security proof of concept. gVisor vs managed microVM remains open. |
| ADR-005 | Validated dashboard spec plus isolated generated React | Preserves generated-code goal and reliable recovery; requires compiler, bridge, CSP, and separate renderer origin. |
| ADR-006 | Explicit optional target and one fixed baseline per task | Avoids arbitrary prediction goals and test-set optimization; EDA succeeds without a model. |
| ADR-007 | One table/file per MVP analysis | Limits joins and leakage ambiguity; larger/multitable analysis follows MVP. |
| ADR-008 | Private storage and authenticated ownership from the start | Prevents insecure public links and retrofit authorization; real auth provider is still to be selected. |
| ADR-009 | Synthetic fixtures and fake provider in ordinary CI | Predictable cost and tests; small live-provider and actual-runtime suites remain necessary. |
| ADR-010 | Conservative cleaning separate from learned preprocessing | Preserves data meaning and valid evaluation; some messy values remain flagged instead of silently repaired. |
| ADR-011 | Accepted: npm + uv and exact lockfiles | Use verified npm 11.19.0 and local Python 3.13.7. TypeScript 5.9.3 satisfies generator compatibility; no forced dependency resolution. |
| ADR-012 | Accepted: hard-disabled local-only API | Runtime registration/environment flags cannot enable arbitrary execution; broker and authentication integration remain prerequisites. |
| ADR-013 | Accepted: reviewed React lab before product shell | Tests the boundary independently; esbuild compiles checked-in fixtures only. Generated-source builds still require isolation. |
| ADR-014 | Accepted 2026-09-17: project-owned PostgreSQL 17 for local metadata | Installed binaries allow real migration/parity/concurrency tests despite Docker being unavailable. Cluster lives in ignored .local, isolated from system databases. SQLite remains a fast test backend only. |
| ADR-015 | Accepted 2026-09-17: operator-issued local login tickets and hashed server sessions | Provides testable authentication without selecting a hosted provider. Five-minute single-use tickets, eight-hour sessions, origin/CSRF checks, HTTPS secure cookies. Loopback HTTP uses an explicit local cookie exception. Hosted startup stays disabled; B04H is a separate required release gate. |
| ADR-016 | Accepted 2026-09-17: raw upload reference on dataset; run-scoped derived artifacts | Avoids circular raw-artifact linkage and enables composite project/run foreign keys. No object storage or upload execution is implied by the schema. |

## Template for future decisions

ID and title; date; status; problem/context; alternatives considered; decision; consequences; validation evidence; affected requirements; supersedes/superseded-by. For security decisions, state the trust boundary and remaining limitations explicitly.
