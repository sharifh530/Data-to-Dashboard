# B05 raw storage slice evidence

2026-09-17, local Windows/PostgreSQL 17.6. Storage only; B05 inspection remains incomplete.

- `npm run sandbox:preflight`: failed closed, DOCKER_UNAVAILABLE; execution false.
- Local PostgreSQL helper: cluster ready on project port 55432.
- `npm run db:migrate`: migration 7c8ecbbfe69e applied.
- `npm run contracts:generate`: OpenAPI/TypeScript updated.
- `npm run check`: passed (4 protocol tests; 52 Python passed, 31 PostgreSQL skipped; lint/types/contracts/build).
- After adding concurrent quota coverage, `npm run test:postgres`: all 84 passed, no skips; `npm run check:python`: passed, 19 typed source files.
- `npm run db:check`: no migration drift.
- `git diff --check`: passed.

Tests verify exact raw byte preservation without parsing, checksums, attachment/nosniff headers, cross-owner denial, CSRF, idempotent replay/conflict, project tombstones, byte/header limits, storage quota, concurrent quota serialization, corruption rejection and logout during upload. Focused receiver tests cover timeout and disconnect. Existing migration tests cover downgrade/re-upgrade with the new table. Synthetic bytes only; no private files used.

No browser upload UI or parser exists. Production S3, administrator-resistant immutability, global download limits, deletion/retention and isolated inspection remain future work. Existing browser tests not rerun because renderer code did not change. Two upstream test-client warnings remain. ADR-018 and UPLOAD_STORAGE.md document the local storage choice and operational limits.
