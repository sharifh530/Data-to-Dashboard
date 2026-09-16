# Implementation roadmap and backlog

Status: B02 foundation scaffold is complete; B01 browser proof is partial and Python runtime verification is blocked by the unavailable engine. Other packages remain TODO; draft B03 schemas are seeded. See `memory/TASKS.md`. Priorities: P0 MVP, P1 later. Sequence is dependency-based, not a date commitment. Public deployment remains gated by security evidence.

| ID | Priority | Work package | Depends on | Exit evidence |
| --- | --- | --- | --- | --- |
| B01 | P0 | Runtime/renderer isolation proof of concept | — | Actual deployed Python egress/resource tests and iframe attack probes pass; ADR records provider/runtime choice |
| B02 | P0 | Repository/toolchain scaffold | — | Pinned frontend/backend deps, lint/type/test commands, CI, environment template, reproducible local setup |
| B03 | P0 | Contracts, metadata schema, migrations | B02 | Executable schemas and generated TS types; migrate clean DB and rollback/recovery check |
| B04 | P0 | Authentication/project ownership | B03 | Two-user isolation tests, secure session and CSRF handling |
| B05 | P0 | Upload, isolated CSV/SQLite inspection | B01–B04 | Supported/malformed fixtures, byte/row limits, table selection and preview |
| B06 | P0 | Queue/outbox, state machine, SSE, cancellation | B03–B04 | Reconnect, duplicate-delivery, restart, cancel/publication-race tests |
| B07 | P0 | Deterministic profiling and artifact pipeline | B05–B06 | Profile correctness, immutable manifest, safe collector tests |
| B08 | P0 | LangChain/LangGraph cleaning workflow | B01, B06–B07 | Generated Pandas execution, bounded repairs, provenance, injection tests |
| B09 | P0 | Baseline modeling | B08 | Classification/regression and skip cases; split/leakage checks; dummy comparison |
| B10 | P0 | Dashboard spec, query broker, fallback UI | B07 | Validated evidence-backed charts, filtering/paging caps, accessibility checks |
| B11 | P0 | Generated React compile/render pipeline | B01, B08, B10 | Offline build, iframe bridge/CSP tests, generated and fallback E2E |
| B12 | P0 | End-to-end product screens/history/export | B04–B11 | CSV/SQLite demo paths; safe exports; responsive UX |
| B13 | P0 | Deletion, retention, quotas, operational controls | B06–B12 | Revoked access, artifact/checkpoint purge, rate/resource caps, kill switch |
| B14 | P0 | Release hardening and documentation | B01–B13 | Acceptance report, load benchmark, restore rehearsal, clean-install walkthrough |
| B15 | P1 | Natural-language dashboard revisions | B14 | Versioned changes with same security gates and rollback |
| B16 | P1 | Multiple-table joins and larger datasets | B14 | New limits/semantics plus performance and modeling regression evidence |

## Milestones

M0, feasibility: B01–B03 establish security boundaries and runnable foundations. M1, ingestion: B04–B07 produce a reliable upload/profile workflow. M2, autonomous analysis: B08–B09 produce audited cleaning and baseline metrics. M3, generated experience: B10–B12 deliver the complete dashboard workflow. M4, release: B13–B14 validate privacy, operations, and user journeys.

For each task, create smaller implementation checklists only when work begins. Keep acceptance evidence with the task/session log rather than declaring a large work package complete based on a partial UI. Prefer vertical slices with synthetic fixtures and a deterministic fake provider before live LLM integration.

## First implementation session

Inspect installed tooling and Git status. Select compatible package versions and record them. Start B01 with tiny fixed Python jobs and a deliberately hostile sample React component; no real user data. In B02 scaffold the API/web/test harness and document actual commands. Decide hosting/provider only when runtime evidence and user constraints are available; do not block provider-independent foundation work.
