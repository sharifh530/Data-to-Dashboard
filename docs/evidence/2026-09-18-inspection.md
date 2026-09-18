# Isolated inspection acceptance — 2026-09-18

Local Windows/WSL development evidence; no hosted production certification. Setup and limits: [INSPECTION.md](../INSPECTION.md).

## Delivered

Fixed CSV/SQLite inspector, stdin byte transfer, gVisor execution with bounded output/deadline and verified cleanup; independent systemd orphan reaper; migration ff09fd7a653b; durable inspection leases/attempts/fenced publication; owner/CSRF APIs; reviewed React previews and generated contracts.

Tested image: sha256:8a2a247fa87f5d7f8d2d2b9da37a1945b57d34bcaaf0084fda0ea58a2bfa50e4. Built from the pinned Python base in dtd-sandbox. Uploaded formats were parsed only inside runsc containers.

## Executed checks

- npm run test:postgres: 103 passed, no skips. Includes migration recovery and inspection ownership, replay, shape, lineage, stale token, expired lease, deletion and retry limits. Execution is mocked in this suite.
- npm run check: 4 JavaScript tests; 62 Python passed/41 PostgreSQL-only skipped; lint, format, types, contracts and builds passed. Two existing upstream Python deprecation warnings remain.
- node scripts/python.mjs scripts/test-inspector.py --image <image above>: 16 actual gVisor cases passed. Sample245x11, invalid UTF-8, NUL, bad quoting, inconsistent widths, field/column/row limits, duplicate headers, semicolon/leading zeros, empty table, SQLite ordinary tables with unexecuted extension-loading view, invalid header, corrupt database, excessive tables and generated columns.
- DTD_TEST_INSPECTION_IMAGE=<image> with npm run test:web: real Chromium upload/inspection/preview/reload/download/synthetic cancellation/logout journey passed. Fixture shows 245 rows, 11 columns, 15 empty values. Browser metadata uses temporary SQLite; runtime parsing uses actual gVisor. Desktop and 390px mobile screenshots are ignored test artifacts.
- Independent reaper: created idle labelled inspector container, verified it existed, then verified removal by successful systemd service. WSL restarted during observation; this establishes eventual orphan cleanup after startup, not a measured 75-second bound or full broker-death matrix.

## Bugs found and corrected

A lineage-invalid report remained assigned after validation raised, allowing publication; failure now discards the report. Error-code validation initially rejected UTF8_REQUIRED; digits are accepted. Concurrent reuse of a single SQLite connection failed in the browser harness; it now uses a temporary file with separate pooled connections. Wider previews exposed mobile overflow and unreadably narrow columns; bounded scrolling and minimum cell widths address both.

## Limits

No generated Python/React, LangChain, cleaning, modeling or profiling pipeline enabled. Running inspection cancellation returns 409; queued cancellation supported. Persistent selection, parse overrides, manual retry, production admission and comprehensive process-death/host-failure tests remain. Future deletion APIs need publication concurrency tests. Prior generic resource/renderer suites were not rerun; earlier evidence retains its original scope.
