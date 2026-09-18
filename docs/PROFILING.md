# Selected-table profiling

Implemented local B07 slice, 2026-09-18. After **Use this table**, choose **Profile selected table**. The worker runs a fixed second pass over the immutable upload inside the dedicated gVisor runtime. No uploaded CSV/SQLite is parsed by the API or developer host.

The profile covers only the current selected dataset version. It reports each column's missing count, distinct nonempty count, numeric-looking count, other nonempty count, finite numeric minimum/maximum, and up to five most frequent values. All counts scan the table up to the existing 100,000-row/10 MiB limits. Values remain strings; numeric-looking identifiers such as `00029` are counted as numeric-looking without converting the source or claiming semantic type inference. Missing means NULL/empty string only. Frequency values shown to the owner may contain private data; the API never makes reports public.

`POST /api/v1/dataset-versions/{id}/profile` queues an idempotent job; `GET` returns status and the private report. Both enforce the current selected version and project ownership. The worker admits one active profile per owner, uses a 90-second fenced lease, limits recovery to three attempts, and validates the profile schema, raw SHA-256, format, table, delimiter and saved column fingerprint. It publishes an immutable-at-application-level JSON report with a canonical `report_sha256` in PostgreSQL. A changed table/delimiter invalidates access to the previous profile. The old version and report remain historical database records until retention/deletion work is implemented.

The same pinned inspector image implements a fixed `profile` mode. The Windows-to-WSL broker passes a validated table index 0–9, never a user-controlled table name or source code. gVisor/no-network/read-only-root/resource/timeout/cleanup rules from [inspection](INSPECTION.md) apply. The profile report is bounded to 512 KiB. This local version-scoped report is the first validated artifact; the existing `artifacts` table is run-scoped and will be used by later analysis stages.

To use the updated image, run `npm run sandbox:wsl -- sync`, rebuild the image as in [inspection setup](INSPECTION.md), set the new local image ID in ignored `.env`, migrate with `npm run db:migrate`, and restart the API and worker. Existing images lack the profile mode.

Acceptance commands: `npm run test:postgres`, `npm run check`, `node scripts/python.mjs scripts/test-inspector.py --image <new-image-id>` and `DTD_TEST_INSPECTION_IMAGE=<new-image-id> npm run test:web` (set the environment variable with PowerShell syntax as in the inspection runbook). See [dated evidence](evidence/2026-09-18-profiling.md).

Remaining B07 scope: broader profiling semantics, retention/deletion and run-scoped artifact manifests for cleaning/model/dashboard outputs. No generated Pandas, cleaning or model fitting runs yet.
