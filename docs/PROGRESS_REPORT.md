# Data-to-Dashboard: detailed implementation progress

Prepared 2026-09-18. Implementation snapshot: 2026-09-17, through commit `f638134`. Sources: project memory, dated evidence reports and Git history. This report is a historical snapshot; [current state](../memory/STATE.md) and [task ledger](../memory/TASKS.md) take precedence as work continues.

## 1. Goal and current outcome

The intended product accepts messy CSV or SQLite data, uses a LangChain/LangGraph agent to generate Pandas cleaning code, evaluates a baseline predictive model when appropriate, and generates an interactive React dashboard inside a separate security boundary.

What works today: a local authenticated workspace, projects, bounded raw upload/download, stored-file history, a durable synthetic workflow, and a dedicated gVisor environment with actual isolation/resource tests. The app does **not yet inspect or analyze uploaded files**, call an LLM, train a model, or generate a dashboard. A sample run demonstrates orchestration using fixed numbers rather than uploaded data.

## 2. Task-by-task delivery history

### Task 1 — Requirements, architecture and project memory (DOC-01)

**Status:** complete as the initial planning package. **Date:** September 16.

Created requirements, architecture, API/data, security/privacy, data/modeling, agent/generated-UI, UX, testing, development, operations, roadmap, risk, decision and reference documents. Added repository working instructions and persistent state, task and session-log files. These capture the core features, acceptance criteria, dependencies and rules for continuing work across sessions.

The initial stack choices were proposals rather than claims of deployed services. Hosting, external identity and LLM providers were deliberately left undecided. The project rules require preserving raw data, preventing model leakage, enforcing ownership and keeping generated code out of the trusted API/browser origin.

**Evidence:** the initial 20-document package had zero broken local Markdown links in the recorded check. No application tests existed at that point. See [requirements](PRD.md), [roadmap](ROADMAP.md), [decisions](DECISIONS.md) and [session history](../memory/SESSION_LOG.md).

### Task 2 — Application foundation and renderer isolation lab (B02; part of B01)

**Status:** foundation complete; security feasibility remained partial. **Date:** September 16. **Commit:** [8dcea55](https://github.com/sharifh530/Data-to-Dashboard/commit/8dcea55).

Established React/TypeScript and FastAPI, generated API contracts, exact npm/uv lockfiles, lint/type/test/build commands and a CI workflow. The API exposed health/capability information and rejected hosted startup or unavailable analysis admission. Python 3.13.7 and Node 24.20.0 were selected from the available tools.

Built a separate React isolation lab with an opaque iframe, scoped MessageChannel communication, request validation, replay limits, restrictive CSP and reset/fallback behavior. Only reviewed fixtures were compiled. Added Docker/runsc preflight and a bounded fixed-probe launcher; generated Python execution remained disabled.

**Problems resolved:** a TypeScript dependency compatibility conflict and an accessible browser-test selector. Docker was unavailable, so no runtime test was claimed then.

**Evidence at delivery:** 24 Python tests, four protocol tests and five Chromium tests passed, along with lint/types/contracts/build and HTTP smoke checks. See [foundation evidence](evidence/2026-09-16-foundation.md). The renderer lab remains separate from the product UI.

### Task 3 — GitHub publication and continuity process

**Status:** established. **Date:** September 17; policy recorded with the foundation publication.

Configured `origin` as the user-provided GitHub repository and preserved `main` history. Recorded standing authorization to commit and push after each completed major task. The workflow fetches before publication, never force-pushes, and verifies the remote commit hash afterwards.

Ignored credentials, local databases/virtual disks, dependencies, builds and test outputs. Every subsequent milestone updated memory and documentation before publication. These files provide continuity; they are not an automatic background memory service.

### Task 4 — PostgreSQL persistence (B03)

**Status:** complete for the implemented metadata foundation. **Date:** September 17. **Commit:** [6ba2a08](https://github.com/sharifh530/Data-to-Dashboard/commit/6ba2a08).

Implemented the initial 15 SQLAlchemy application tables and Alembic migration. Entities cover identities/sessions, projects, datasets/versions, runs, stage attempts, artifacts, dashboards, events, questions, outbox delivery, idempotency and audits. Composite foreign keys enforce project/run lineage. Later milestones added work items and raw uploads, bringing the current count to 17 application tables.

Created a project-owned PostgreSQL 17.6 cluster on loopback port 55432, separate from the existing system service. Development/test databases and ignored local credential configuration were established. The API checks migration readiness rather than creating schema implicitly.

**Problems resolved:** Windows inherited child-process pipes hanging database startup, and unbounded connection attempts after the database stopped between sessions.

**Evidence:** migration upgrade/downgrade/re-upgrade, schema drift checks, lineage rejection and real PostgreSQL tests. Persistence/auth delivery passed all 47 Python cases with no skips in the PostgreSQL run. See [persistence guide](PERSISTENCE_AND_AUTH.md) and [evidence](evidence/2026-09-17-persistence-auth.md).

### Task 5 — Local authentication and project ownership (B04 local scope)

**Status:** local scope complete; hosted authentication is separate B04H. **Commit:** [6ba2a08](https://github.com/sharifh530/Data-to-Dashboard/commit/6ba2a08).

Implemented operator-issued, five-minute, single-use login tickets; hashed eight-hour server sessions; cookie-based sign-in; logout/revocation; exact-Origin and CSRF checks. HTTPS uses secure host-only cookies; loopback HTTP has an explicit local exception.

Added owner-scoped project creation, listing and retrieval, cursor pagination, request validation, audit records and idempotency. Concurrent replay and cross-user access tests validate enforcement. Error responses avoid echoing credentials or raw request input.

**Not completed:** external identity provider, hosted sign-in/recovery, authentication abuse controls and hosted browser/session acceptance. Local tickets are not SSO.

### Task 6 — Durable synthetic run orchestration (B06)

**Status:** complete for fixed synthetic workflows. **Commit:** [b100490](https://github.com/sharifh530/Data-to-Dashboard/commit/b100490).

Implemented atomic run/outbox creation, PostgreSQL work items, row-locking claims, five-second leases, generation/token fencing, checkpoints, bounded retries and a run deadline. Delivery and replay are idempotent; one unfinished run per owner is admitted. A local worker processes three reviewed sample stages.

Added run detail/history, persistent progress events, SSE replay with Last-Event-ID, snapshot recovery when history is missing, and cancellation. Ownership/session state is rechecked for streams. Stale workers cannot publish after losing their lease or a cancellation race.

**Problems resolved:** nested tooling-worktree lint discovery and migration formatting. The migration also preserves existing event sequence values.

**Evidence:** all 76 Python cases passed with PostgreSQL, including concurrent admission/claims, duplicate delivery, separate-process restart, expired leases, stale completion, cancellation/publication races and ownership. See [run guide](RUN_PROCESSING.md) and [evidence](evidence/2026-09-17-run-processing.md).

**Boundary:** fixed sales totals only—27,200 revenue and 176 orders. No uploaded file, model, external provider or generated program participates in these runs. Real broker cancellation and LangGraph integration remain future work.

### Task 7 — Bounded raw upload storage (B05 storage slice)

**Status:** storage complete; inspection/selection/preview incomplete. **Commit:** [2f15347](https://github.com/sharifh530/Data-to-Dashboard/commit/2f15347).

Added authenticated raw CSV/SQLite byte submission, owner-only metadata and original downloads, SHA-256 integrity verification and retry-safe idempotency. Bytes, metadata, audit and idempotency commit together in PostgreSQL. The application does not overwrite stored content; this is not administrator-resistant WORM storage.

Enforced 1 byte–10 MiB per file, 50 MiB per owner, two concurrent upload slots per API process and a 30-second receive deadline. Content-Length is independently checked against received bytes. Ownership/session validity is checked before receipt and again before persistence. Quotas serialize on the owner row.

**Evidence:** 84 Python tests passed with PostgreSQL, including concurrent quota checks, corruption rejection, length/format limits, interruption, timeout, idempotency and revocation during upload. See [storage guide](UPLOAD_STORAGE.md) and [evidence](evidence/2026-09-17-upload-storage.md).

**Boundary:** files are opaque bytes with awaiting-inspection status. Malformed content can be stored without being considered valid data. No parser runs in the API. Production S3 storage, deletion/purge and global download limits are not implemented.

### Task 8 — Authenticated product workspace (B12 first slice)

**Status:** local workspace slice complete; full analyst UX incomplete. **Commit:** [6dd3b90](https://github.com/sharifh530/Data-to-Dashboard/commit/6dd3b90).

Built the reviewed React application at the API origin, with ticket sign-in, session restoration, logout, project creation/selection, file upload/format choice, stored-file pagination, checksums/downloads, sample run history, stage status and cancellation. Added the owner-scoped paginated dataset-list API.

The UI explicitly explains that analysis is unavailable. It polls active runs every two seconds; SSE exists in the backend but is not consumed by this first interface. Same-origin static assets are allowlisted and governed by restrictive CSP. No generated JavaScript is served from this origin.

**Evidence:** 86 Python cases passed with PostgreSQL. A real Chromium journey against an ephemeral test API exercised sign-in, project creation, upload/download, refresh, cancellation and logout. Desktop/mobile screenshots were inspected; mobile horizontal overflow and JavaScript page errors were checked. Minor byte-count and notice issues were corrected. See [UI guide](WORKSPACE_UI.md) and [evidence](evidence/2026-09-17-workspace-ui.md).

**Boundary:** no dataset review, analysis configuration, model report, generated dashboard or export UI yet. Responsive verification is not a comprehensive accessibility audit.

### Task 9 — Uploadable synthetic test dataset (SAMPLE-01)

**Status:** complete. **Commit:** [2bd549c](https://github.com/sharifh530/Data-to-Dashboard/commit/2bd549c).

Created [synthetic-sales-messy.csv](../samples/synthetic-sales-messy.csv): 245 data rows, 11 columns and 240 distinct order IDs. All records are fictional. It includes five exact duplicate rows, missing channel/delivery values, inconsistent region capitalization/spacing, currency-formatted prices and leading-zero customer IDs.

**Evidence:** standard CSV round-trip validation confirmed row/field counts, order IDs and positive revenue. This checked-in generated fixture was validated locally; no uploaded untrusted file was parsed. Revenue is a constructed arithmetic target and cannot establish meaningful predictive model quality. See [sample notes](../samples/README.md).

### Task 10 — Dedicated WSL2/gVisor environment (B01 infrastructure slice)

**Status:** runtime established; broader B01 remains partial. **Commit:** [afd74ce](https://github.com/sharifh530/Data-to-Dashboard/commit/afd74ce).

Docker Desktop became reachable but had no runsc. The user explicitly selected a separate project WSL2 environment. Created `dtd-sandbox` from a pinned Ubuntu 24.04 image, installed its own Docker 29.1.3 and signed gVisor/runsc 20260914.0 packages, and enabled systemd. Windows drive automount, fstab mounting and Windows executable interoperability were disabled in that distribution.

Existing Docker Desktop was not reconfigured. No unauthenticated Docker TCP endpoint was opened. Added an explicit WSL wrapper that transfers only reviewed probe sources, not credentials/uploads or host mounts. Pinned images and commands are recorded in the runbook.

**Problems resolved:** the first systemd start occurred before its configuration was written; corrected that configuration and restarted only the project distribution. Tightened the filesystem probe to require EROFS rather than accepting ordinary permission denial.

**Evidence:** eight real checks passed: non-root, read-only root, blocked IPv4/IPv6/metadata/DNS access, no runtime socket and no provider credentials. A writable-root negative control failed as expected; no probe containers remained. See [sandbox runbook](SANDBOX_WSL.md) and [evidence](evidence/2026-09-17-wsl-sandbox.md).

**Boundary:** local WSL development infrastructure shares host resources. It is not a production isolation certification or proof against every escape technique.

### Task 11 — Resource-limit and container termination acceptance (B01 testing slice)

**Status:** seven fixed resource tests complete; integration remains. **Commit:** [f638134](https://github.com/sharifh530/Data-to-Dashboard/commit/f638134).

Added a reviewed resource-exercise image and `sandbox:wsl resources` command. Tests use reduced budgets: 0.5 CPU, 256 MiB memory, 8 MiB scratch, 128 host tasks, 32 guest processes and 64 KiB retained output.

Verified actual scratch ENOSPC, guest fork EAGAIN, memory OOM kill, excess-output termination, CPU throttling observed in cgroup statistics, deadline termination, and cancellation of a parent with three busy children. Containers were removed and relevant cgroups were absent or empty after termination. The original eight isolation checks passed again under the final policy.

**Problems found and fixed:** a 32-task host limit killed gVisor rather than providing a controlled guest process limit. The policy now distinguishes host tasks from guest RLIMIT_NPROC. Stopping the output reader could leave Docker attach blocked after killing a flooding container; readers now drain/discard excess output while retaining only the bounded amount.

**Evidence:** final resource suite passed all seven cases; `npm run check` passed four protocol tests, 53 Python tests with 33 intentional PostgreSQL skips, lint/format/types/contracts/build. Database/browser suites were unchanged and not rerun for this runtime-only milestone. See [resource evidence](evidence/2026-09-17-resource-probes.md).

## 3. Verification summary without overstating coverage

| Check | Latest recorded result | Scope/date context |
| --- | --- | --- |
| Standard project check | Passed; 4 protocol tests, 53 Python passed/33 skipped | Repeated at resource milestone; also lint/types/contracts/build |
| Full PostgreSQL suite | 86 passed, no skips | Last run at workspace UI milestone, not rerun after runtime-only edits |
| Workspace browser journey | 1 passed | Real ephemeral API, desktop/mobile checks; UI milestone |
| Renderer isolation browser suite | 5 passed | Foundation milestone; unchanged later |
| Actual gVisor isolation | 8 checks passed | Repeated after final resource policy |
| Actual gVisor resource suite | 7 cases passed | Resource milestone |
| Read-only negative control | Correctly rejected writable root | Runtime establishment milestone |

Two upstream Python test-client warnings and a Docker legacy-builder warning remain recorded. Authored CI configuration is not evidence that remote CI passed. No paid provider call, hosted deployment, real model evaluation or generated-dashboard E2E success is claimed.

## 4. Remaining roadmap, in dependency order

| Task | Remaining work |
| --- | --- |
| B01 / B05 | Safe bounded input transfer, isolated CSV/SQLite inspection, hostile parser fixtures, validated result collection, broker-death recovery and application cancellation integration |
| B05 | Schema/table selection, parse diagnostics, immutable selected versions and preview UI |
| B07 | Deterministic profiling, validated artifact manifests and safe collection |
| B08 | Actual LangChain/LangGraph workflow, generated Pandas, bounded repair, provenance and injection tests |
| B09 | Classification/regression/skip handling, leakage-safe splits/preprocessing and baseline evaluation |
| B10 | Validated dashboard specification, bounded queries, filters and fallback UI |
| B11 | Isolated generated React compilation, renderer integration and generated/fallback E2E tests |
| B12 | Analysis configuration/progress, model/dashboard screens, exports and accessibility completion |
| B04H | Hosted identity, sign-in/recovery and abuse controls |
| B13–B14 | Retention/deletion, operational quotas, backup/restore, load/security/release acceptance |
| B15–B16 | Post-MVP natural-language revisions, multi-table joins and scale |

**Next concrete implementation:** the isolated CSV/SQLite inspector and safe broker transfer/result contract. Do not add more synthetic UI as a substitute for this core feature, and do not enable arbitrary execution merely because fixed probes pass.

## 5. Operational entry points and continuation

- Product workspace: `http://127.0.0.1:8000/`; reviewed renderer lab: port 4173 (isolated fixture origin also uses 4174).
- PostgreSQL: project-owned loopback port 55432. Local credentials and data live in ignored files, not this report.
- `npm run build:web`, `npm run dev:api`, and separately `npm run dev:worker` for synthetic jobs. Issue local tickets through `npm run auth:issue -- --subject your-name`.
- Runtime: `npm run sandbox:wsl -- sync`, then `preflight`, `probe --image <digest>` or `resources --image <digest>`. Use the runbook's pinned digests. Ordinary Windows Docker context still lacks runsc.
- Verify actual process/service liveness before reuse; historical PIDs are not reliable. Stop only project-owned services.
- Preserve raw bytes, ownership, bounded budgets and isolation. Never put tokens, private data or provider payloads in Git or memory.

For a fresh conversation, use [the compact handoff](../memory/CHAT_HANDOFF.md). It summarizes context without deleting this report or the append-only session history.
