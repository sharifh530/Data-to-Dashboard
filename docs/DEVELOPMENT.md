# Development process

## Present state

Local foundation implemented. See [Getting started](GETTING_STARTED.md) for executable setup/checks. npm/uv lockfiles, a placeholder-only environment template, React fixture build, API, contracts, and CI configuration exist. Full product screens and analysis services remain planned.

## Planned prerequisites and configuration

Use Node with npm, Python with uv, and Linux for sandbox work. Node 24.20.0 and Python 3.13.7 are pinned. Git uses the supplied remote. A project-owned PostgreSQL 17.6 cluster now exists; Redis and object storage remain unconfigured. Actual database settings are `DTD_DATABASE_URL` and `DTD_APP_ORIGIN`; other keys below remain proposals.

Planned environment keys: `DATABASE_URL`, `REDIS_URL`, `OBJECT_STORE_ENDPOINT`, `OBJECT_STORE_BUCKET`, scoped storage credentials, `SESSION_SECRET`, auth provider settings, `LLM_PROVIDER`, `LLM_MODEL`, provider secret, `EXECUTION_BROKER_URL`, broker authentication, `RENDERER_ORIGIN`, upload/runtime limits, retention settings, telemetry opt-in. Commit only placeholder `.env.example` values once code defines the real configuration. Validate configuration at startup; reject unsafe hosted execution profiles.

## Build workflow

1. Read memory and select a backlog item with satisfied dependencies.
2. Write/confirm its contracts and acceptance cases; record architecture changes in an ADR.
3. Implement a small end-to-end slice using synthetic data and a fake provider where possible.
4. Run relevant formatting, lint, type, unit/integration/browser checks; do not substitute compilation for security testing.
5. Update docs and memory with real outcomes, limitations, and next action.
6. Review the diff for secrets, unrelated changes, dependency drift, and unsafe execution paths.

Proposed checks to wire into CI: frontend formatting/lint/typecheck/build; Python formatting/lint/typecheck; unit/contract suites; database migrations and integration suite; browser E2E; dependency and secret scanning. Security-runtime tests run on an isolated Linux runner capable of enforcing the actual runtime policy. No privileged hostile-code tests on a shared general-purpose CI runner.

## Definition of done

A task is done when its acceptance behavior works, relevant checks pass with recorded commands, API/schema changes are synchronized, ownership and failure cases are covered, operational implications are documented, and memory reflects the current state. UI work includes empty/error/loading states and keyboard behavior. AI work includes malformed output, budget exhaustion, timeout, and deterministic fallback/skip behavior.

## Change and decision management

Use focused commits and short feature branches when Git is initialized; never initialize or rewrite remote history implicitly. PR descriptions explain the concrete behavior and validation. New dependencies, isolation changes, external data disclosure, and storage/contract changes require an ADR update as part of normal review. No special approval ceremony is implied for routine reversible implementation.

Requirements are the product source of truth; ADRs explain tradeoffs; memory records what exists. If these disagree, inspect implementation/evidence, resolve explicitly, and update all affected documents. Task IDs remain stable. Dates are ISO 8601; technical event timestamps use UTC.
