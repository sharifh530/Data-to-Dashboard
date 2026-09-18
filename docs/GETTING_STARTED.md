# Running the foundation

Implemented through 2026-09-17: API, PostgreSQL migrations, local authenticated projects, contracts, React isolation lab, tests, and runtime preflight. This is not yet the upload/analysis application. The lab needs no database; project APIs require a migrated database and operator-issued login. No external LLM key is needed. See [database/auth setup](PERSISTENCE_AND_AUTH.md).

## Installation

Use Node 24.20.0 (`.node-version`), Python 3.13.7 (`.python-version`), and uv 0.12.15. Exact dependencies are recorded in `package-lock.json` and `uv.lock`. TypeScript is 5.9.3 because the selected OpenAPI type generator requires TypeScript 5.

From the repository root:

```powershell
npm ci
uv sync --locked
npx playwright install chromium
```

On this Windows workspace, uv was bootstrapped without a global install. If `uv` is not on PATH:

```powershell
py -3.13 -m venv .tools
.\.tools\Scripts\python.exe -m pip install uv==0.12.15
.\.tools\Scripts\uv.exe sync --locked
```

The npm scripts select `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` on Linux/macOS. `.tools` and `.venv` are ignored. Source control uses [Data-to-Dashboard on GitHub](https://github.com/sharifh530/Data-to-Dashboard) with `origin` and branch `main`. Completed major tasks are committed and pushed after validation and memory updates, as authorized by the user.

## Run locally

Start these in separate terminals from the repository root:

```powershell
npm run dev:api
```

```powershell
npm run dev:lab
```

- API: [liveness](http://127.0.0.1:8000/health/live), [capabilities](http://127.0.0.1:8000/api/v1/capabilities), [OpenAPI](http://127.0.0.1:8000/openapi.json).
- Lab: [http://127.0.0.1:4173](http://127.0.0.1:4173/).
- Renderer fixture: `http://localhost:4174/fixture`, embedded by the lab. Hostnames are bound in the bridge and CSP.

Liveness returns 200; readiness deliberately returns 503 because analysis admission is unimplemented. `DTD_ENVIRONMENT` values other than `local` reject startup. No environment flag can enable generated-code execution.

The lab compiles only a checked-in, reviewed React fixture. Select Direct to see synthetic revenue change from $27,200 to $12,800, reset the iframe, or use the standard layout. Browser probes report blocked parent DOM, cookie, storage, eval, and network access. This is a developer test harness, not generated dashboard functionality.

Use Ctrl+C in each terminal to stop servers. Ports are fixed and startup fails if occupied. Stop the lab before browser tests, which own a fresh server on those ports.

## Verification

The authenticated product workspace is at `http://127.0.0.1:8000/` after `npm run build:web` and `npm run dev:api`. See [workspace UI](WORKSPACE_UI.md) for local tickets, uploads and sample run history. `npm run test:web` tests this UI against an ephemeral backend, separately from the renderer isolation lab.

Raw uploads are available through the workspace and storage API; see [upload storage](UPLOAD_STORAGE.md). Run `npm run db:migrate` first. Configure the dedicated runtime using [isolated inspection](INSPECTION.md) to enable CSV/SQLite previews. Analysis remains disabled.

```powershell
npm run check
npm run test:browser
npm run sandbox:preflight
```

`check` runs JS lint/types, protocol tests, Python lint/format/types/tests, contract drift detection, and fixture compilation. Browser tests use headless Chromium and actual HTTP headers. CI repeats these checks on Linux; the authored workflow has not run remotely.

Preflight returns exit 2 when Docker/runsc is unavailable. This is a blocker, not a passing isolation test. A registered runtime still reports execution disabled until actual probes and integration are complete. See [security evidence](evidence/2026-09-16-foundation.md).

After schema changes:

```powershell
npm run contracts:generate
npm run contracts:check
```

OpenAPI types cover health/capability, authentication, project and synthetic run routes. `run-create.schema.json` remains a draft future analysis input contract. Use `npm run test:postgres` for real database parity/concurrency tests. Start the durable fixture worker with `npm run dev:worker`; see [run processing](RUN_PROCESSING.md) for submission, SSE replay, cancellation and recovery.

## Synthetic Python probe on prepared Linux

A project-specific WSL2/gVisor environment is now installed locally. Use [the sandbox runbook](SANDBOX_WSL.md) and `npm run sandbox:wsl -- preflight`; ordinary Windows Docker-context preflight still reports RUNSC_MISSING. Basic probes pass, but execution admission remains disabled pending remaining tests/integration.

Docker must expose a Linux engine with `runsc` configured using the [gVisor guide](https://gvisor.dev/docs/user_guide/quick_start/docker/). Do not substitute ordinary runc. Runtime installation and daemon policy changes have not been performed here.

Build the probe with a reviewed Python 3.13 base pinned by a real digest. Example PowerShell commands after substituting that digest:

```powershell
New-Item -ItemType Directory -Force .local
docker build --build-arg BASE_IMAGE=python@sha256:REPLACE_WITH_REVIEWED_DIGEST --iidfile .local/probe-image-id sandbox/probe
$probeImage = Get-Content -LiteralPath .local/probe-image-id
npm run sandbox:probe -- --image $probeImage
```

Only the operator-built synthetic image belongs here. The launcher accepts no source or runtime flags. It fixes runsc, network denial, non-root UID, read-only root, capabilities, resource limits, and scratch storage; caps output at 64 KiB; stops after 30 seconds; and verifies removal of the specific container. Success checks basic egress/filesystem properties, not CPU/memory/PID/escape resistance or public-release readiness. Those need a dedicated security environment. Never run `sandbox/probe/probe.py` directly on the host.
