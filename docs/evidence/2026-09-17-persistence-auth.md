# Persistence/authentication evidence — 2026-09-17

Environment: Windows; project-owned PostgreSQL 17.6 on loopback 55432; SQLAlchemy 2.0.54, Alembic 1.20.0, psycopg 3.3.5. Dependencies are locked; credentials remain ignored local files.

A recheck initially stalled because the local PostgreSQL server had stopped between sessions. Restarted the project cluster, bounded connection attempts to five seconds, and reran the full database suite successfully. Earlier interrupted/stalled runs are not counted as passes.

- `npm run db:migrate`: initial revision applied to the new development database.
- `npm run db:check`: no model/migration drift.
- `npm run check`: lint, types, format, four protocol tests, Python tests, contract drift and React fixture build pass. Default Python run: 35 passed, 12 PostgreSQL cases skipped without the test URL.
- `npm run test:postgres`: 47 Python tests passed, no skips, covering SQLite and real PostgreSQL. Two pre-existing upstream test-client deprecation warnings remain.

Coverage includes migration rollback/re-upgrade, cross-project foreign keys, persistence across app instances, guessed resource IDs/cursors, CSRF/origin rejection, disabled users, ticket/session expiry, cookie flags, logout, session rotation, token redaction, pagination, tombstones, idempotency/conflicts, and rejection of unmigrated databases. PostgreSQL concurrency tests verify one winning ticket exchange and one project for simultaneous duplicate creates.

Limits: local operator-issued authentication only; no hosted OIDC, sign-in UI, throttling, automatic session cleanup, or least-privilege production role. The five previous Chromium isolation tests were not rerun for this backend-only change. CI now provisions PostgreSQL; local results do not claim a remote CI pass. Worker tables do not imply implemented worker behavior. Docker sandbox verification remains blocked; uploads, LLM/model execution, and generated-source builds stay disabled/unimplemented.
