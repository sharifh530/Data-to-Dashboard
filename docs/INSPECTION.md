# Isolated dataset inspection

Implemented local slice, 2026-09-18. Upload a CSV or SQLite file in the workspace, then choose **Inspect dataset**. Keep `npm run dev:worker` running. The worker transfers original bytes over stdin to a fixed, reviewed parser inside the dedicated WSL gVisor runtime. The API never parses the uploaded format. Inspection does not clean data, fit models, or enable generated code.

## Behavior and limits

- Original upload bytes and SHA-256 remain unchanged. An owner-only report contains table names, headers, row counts, per-column empty counts and the first five rows. Preview cells are limited to 128 characters; React renders them as text.
- CSV accepts UTF-8/BOM, treats the first row as headers and infers comma, semicolon, tab or pipe. Ambiguous detection falls back to comma. Values remain strings, preserving leading zeros. Empty/duplicate headers produce a warning; inconsistent widths and malformed quoting are rejected. No encoding/delimiter/header override exists yet.
- SQLite opens an ephemeral in-container copy read-only and immutable, disables extension loading and trusted schema, checks integrity and reads only ordinary tables. Views, virtual/shadow tables and internal tables are excluded. Generated/hidden columns are rejected. Read authorization restricts queries to the selected ordinary table; preview order is not guaranteed.
- Limits: 10 MiB input, 10 ordinary tables, 64 columns/table, 100,000 rows/table, 128-character names, 65,536-character CSV fields, and a 512 KiB JSON result. SQLite additionally limits SQL and value/row lengths; wide rows may be rejected before the cell limit. Missing means NULL or the empty string, not whitespace or tokens such as `N/A`.
- Container policy uses gVisor, no network/host mounts, read-only root, UID 65532, dropped capabilities, no-new-privileges, 2 CPU/2 GiB, 64 MiB scratch, 128 host tasks and 32 guest processes. The broker enforces a 30-second execution deadline, drains bounded output, suppresses raw errors, removes the container and verifies removal before releasing a result.

## Durable jobs and boundaries

`POST /api/v1/datasets/{id}/inspection` requires ownership, session, exact Origin and CSRF. It is idempotent per dataset and admits one queued/running inspection per owner. `GET` is owner-only. The cancel endpoint cancels queued jobs; running jobs return 409 and finish under their deadline. Failed/rejected/cancelled inspections cannot currently be manually retried; a new upload creates a new dataset.

PostgreSQL row locks claim work with a 90-second lease and unique token. Expired claims can recover, up to three attempts. Publication validates strict report shape, input/output hash and format, current token/lease and active ownership/non-deletion. Runtime errors publish only `INSPECTOR_FAILED`. Inspection readiness is separate from analysis readiness; the existing synthetic workflow still does not consume uploads.

An independent systemd timer removes inspector-labelled, correctly named containers older than 60 seconds. It normally runs every 15 seconds while WSL is active and also after boot. This covers orphan cleanup after broker interruption; it is not a hard wall-clock SLA during host suspension/runtime failure. The broker refuses new work when the timer is inactive. The acceptance session verified orphan-container cleanup, not an exhaustive process-death/power-loss matrix. This local WSL bridge is not the production execution broker.

## Reproduce setup on the existing dedicated distro

First follow [the WSL runbook](SANDBOX_WSL.md). Use PowerShell from the repository; these commands touch only `dtd-sandbox`:

```powershell
npm run sandbox:wsl -- sync
wsl -d dtd-sandbox -u root -- cp /opt/dtd/sandbox/inspector/dtd-inspection-reaper.service /etc/systemd/system/
wsl -d dtd-sandbox -u root -- cp /opt/dtd/sandbox/inspector/dtd-inspection-reaper.timer /etc/systemd/system/
wsl -d dtd-sandbox -u root -- systemctl daemon-reload
wsl -d dtd-sandbox -u root -- systemctl enable --now dtd-inspection-reaper.timer
wsl -d dtd-sandbox -u root --cd /opt/dtd -- docker build --build-arg BASE_IMAGE=python@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 --iidfile /opt/dtd/inspector-image-id sandbox/inspector
wsl -d dtd-sandbox -u root -- cat /opt/dtd/inspector-image-id
npm run db:migrate
```

Set `DTD_INSPECTION_IMAGE` in ignored `.env` to the exact resulting `sha256:` image ID. Restart the API and worker (`npm run dev:api`, `npm run dev:worker`). No tag or unpinned image is accepted. Building the image does not parse any upload.

## Verification commands

```powershell
npm run check
npm run test:postgres
$inspectorImage = (wsl -d dtd-sandbox -u root -- cat /opt/dtd/inspector-image-id).Trim()
node scripts/python.mjs scripts/test-inspector.py --image $inspectorImage
$env:DTD_TEST_INSPECTION_IMAGE = $inspectorImage
npm run test:web
Remove-Item Env:DTD_TEST_INSPECTION_IMAGE
```

The ordinary Python suite mocks the execution boundary to exercise durable publication and access rules. The separate parser suite executes actual gVisor containers. The opt-in browser journey uses actual inspection with an ephemeral SQLite metadata backend, while PostgreSQL parity is checked separately. No live LLM is used. See [acceptance evidence](evidence/2026-09-18-inspection.md).

Remaining B05 work: persistent table choice, explicit parsing overrides and analysis input configuration. B07 profiling/artifact manifests follow that work. Full generated execution, model evaluation, production deployment and comprehensive hostile-runtime testing remain separate milestones.
