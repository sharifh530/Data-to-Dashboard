# Compact continuation handoff

Prepared 2026-09-18; implementation snapshot through `f638134` on September 17. This is a portable chat summary, not a claim that the application's internal conversation was compacted. Read current STATE.md, TASKS.md and AGENTS.md before editing; this snapshot can become stale.

## Goal and authorization

Build Data-to-Dashboard: upload messy CSV/SQLite → agent-generated Pandas cleaning → baseline model when valid → generated interactive React dashboard. User wants autonomous milestone-by-milestone implementation, detailed docs and persistent memory. Routine milestone commits/pushes to https://github.com/sharifh530/Data-to-Dashboard.git are authorized; fetch first, preserve history, never force-push, verify remote hash. User explicitly chose a separate project WSL2 sandbox. No hosted service/provider spending is configured.

Workspace: `H:\Work\My Projects\data-to-dashboard`, Windows PowerShell, branch main/origin. Node 24.20.0; project Python 3.13.7/.venv; npm and uv lockfiles. No delegation unless separately authorized.

## What actually works

- Local FastAPI + PostgreSQL 17.6 metadata/migrations (17 application tables). Project-owned DB at 127.0.0.1:55432; ignored .env/.local hold credentials and data.
- Five-minute single-use local tickets, hashed eight-hour sessions, CSRF/Origin checks, logout, owner-scoped projects and idempotency. Hosted startup disabled.
- React workspace at http://127.0.0.1:8000/: sign-in, projects, raw upload/download, paginated files/history, sample runs, polling/cancel, responsive layout. Generated JavaScript never runs here.
- Raw byte storage: 10 MiB/file, 50 MiB/owner, two upload slots/process, 30-second receipt timeout, SHA-256, atomic DB bytes/metadata/idempotency. Files remain awaiting isolated inspection. No parsing in API.
- PostgreSQL outbox/work items, five-second fenced leases, checkpoints, bounded retries/deadline, SSE replay and cancellation. Only three fixed sample stages; totals 27200 revenue/176 orders. These do not use uploads or train models.
- Separate renderer isolation lab at ports 4173/4174; only reviewed fixture code.
- Uploadable fictional CSV: samples/synthetic-sales-messy.csv, 245 rows/11 columns, five duplicates and deliberate quality issues; see samples/README.md.
- dtd-sandbox WSL2 Ubuntu 24.04, Docker 29.1.3, runsc 20260914.0. Explicit WSL access; Windows automount/interop disabled. Docker Desktop unchanged. Eight isolation checks and seven resource/termination cases pass; read-only negative control rejected.

## Recent important findings

gVisor host tasks differ from guest processes: policy now allows 128 host tasks, guest RLIMIT_NPROC 32. Low host cap killed runtime. Output readers must keep draining/discarding beyond 64 KiB, otherwise Docker attach can block after container kill. Read-only probe requires EROFS on a world-writable file, not any permission error. All fixed test containers were cleaned up.

## Next task

Implement bounded isolated CSV/SQLite inspection, safe input transfer, schema-validated bounded results and adversarial parser tests inside gVisor. Integrate tested termination behavior into a real broker with crash recovery and API cancellation, then add inspection/selection/preview UX. Do not spend another milestone expanding synthetic features. No upload parser, LLM, generated Pandas, model or generated React pipeline exists yet. Application execution stays disabled until actual integration passes. B01/B05/B12 partial; B07–B11, hosted identity, retention and release work remain.

## Commands and evidence

`npm run check`: latest passed; 4 protocol tests, 53 Python passed/33 PostgreSQL skipped, lint/types/contracts/build. `npm run test:postgres`: last full run 86 passed at UI milestone. `npm run test:web`: real ephemeral-API Chromium journey passed. Renderer suite: 5 passed at foundation, not recently rerun. Runtime: 8 isolation + 7 resource cases passed on actual gVisor. Two upstream Python warnings and Docker legacy-builder warning remain. Remote CI not verified.

Run `npm run build:web`, `npm run dev:api`; `npm run dev:worker` handles only synthetic jobs. `npm run auth:issue -- --subject your-name` issues local login. Verify services before reuse. Sandbox commands: `npm run sandbox:wsl -- sync`, `preflight`, `probe --image <digest>`, `resources --image <digest>`. Ordinary Windows preflight lacks runsc; use explicit WSL wrapper. See docs/SANDBOX_WSL.md for pinned images and setup. Never run sandbox exercise/parser code directly on developer host.

Read docs/PROGRESS_REPORT.md for task-by-task history and commits; docs/evidence for exact milestone results; docs/DECISIONS.md for architecture. Preserve original data, split before fitted preprocessing, enforce ownership everywhere, bound retries/resources, and never commit credentials/private data. WSL is local development infrastructure, not proof of production escape resistance.
