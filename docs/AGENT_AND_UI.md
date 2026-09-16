# Agent workflow and generated dashboard contract

## Workflow

Use LangChain for provider/tool integration and LangGraph for explicit state transitions. The workflow is bounded rather than an unrestricted REPL agent.

`validate_input → profile → plan_cleaning → execute_cleaning → validate_cleaning → [train_and_evaluate | skip_model] → plan_dashboard → generate_react → compile_validate → publish`

Branches: unresolved table/target/cleaning ambiguity enters `awaiting_input`; generated UI failure enters `publish_spec_fallback`; model failure preserves cleaned analysis with a warning; unsafe/invalid cleaning fails the run rather than building from unverified data. Any active stage may transition to cancellation or failure. A paused run expires after 24 hours with an actionable reason.

Checkpoint state contains run/tenant IDs, input version, configuration, stage, attempt counts, artifact references, warnings, prompt/schema versions, budget ledger, and pending question. Store no raw data frames or credentials. Persist checkpoints durably. Resume with stable run-bound identifiers; side effects around replay must be idempotent. See [LangGraph interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) for replay behavior.

## Tool surface

| Tool | Inputs | Outputs / restriction |
| --- | --- | --- |
| get_profile | authorized dataset version | bounded statistics, masked examples |
| submit_python | source, fixed job kind, input artifact reference | execution ID; broker attaches limits, never model-specified privilege |
| get_execution_result | current run's execution ID | redacted diagnostics and artifact references |
| validate_artifact | current run reference and schema version | typed checks and findings |
| submit_ui_build | source plus dashboard spec | build result from offline isolated compiler |
| request_input | typed reason and bounded choices | durable pause; no arbitrary permission escalation |

No shell/network/file browsing tool is exposed directly to the model. Resource ownership and job policy are enforced outside model output. Repair feedback includes short errors and relevant schemas, never infrastructure secrets or unrestricted logs.

## Budgets and completion

Initial limits: 12 model calls per run, at most two repair calls for Python and two for React within that total, 60,000 total provider tokens, ten-minute active deadline. Reserve expected maximum tokens before calling; stop if remaining budget cannot cover the request. Monetary caps depend on a versioned price configuration and are disabled as a claim until pricing is configured accurately. Provider retries count toward attempt/time budgets; uncertain charges remain visible in telemetry.

Validate structured responses with Pydantic/JSON Schema. Unknown keys, oversized source, missing artifact references, and policy violations produce bounded repair or terminal/fallback results. UI source cap: 100 KiB. The model never directly changes run status or publishes an artifact.

## Dashboard specification v1

Required fields: `schema_version`, `dataset_version_id`, `title`, `summary`, `kpis`, `charts`, `filters`, `table`, `warnings`, `model_report_ref` (nullable). Each KPI references a metric; charts reference a typed aggregate query ID, chart type, axes/units, title, and text summary. Allow bar, line, scatter, and histogram only initially. Limit six charts, six KPIs, and four filters. Chart selection must match data types; a date-free dataset cannot receive a fabricated time series.

Each filter declares a known column, type (category/range/date), and allowed operators. The server computes capped results with an allowlisted query AST, never generated SQL or Python from iframe messages. Enforce 500 returned points per chart and 100 rows per table page. Show explicit aggregation/sampling indicators.

## React contract

Generate a single default-exported `Dashboard` component using typed props from the approved dashboard kit. Inputs are data and display callbacks, not credentials or arbitrary URLs. Validate imports and disallowed syntax, compile offline, then smoke-render with empty/null/long-label fixtures under the actual iframe policy. If any gate fails after repair budget, use the deterministic renderer for the same validated spec.

Interactions send typed filter/page/sort requests through the parent bridge. Parent UI owns downloads, report navigation, and run commands. Version every spec, source bundle, and bridge protocol. Preserve the last validated output if a later independent rendering attempt fails. The generated UI is a core MVP deliverable; the fallback is recovery and an earlier milestone, not a replacement for implementing generated React.
