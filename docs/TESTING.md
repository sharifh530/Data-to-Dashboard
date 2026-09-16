# Verification and acceptance plan

Foundation checks passed: 24 Python tests, 4 protocol tests, and 5 Chromium tests. See [evidence](evidence/2026-09-16-foundation.md). The full product matrix below remains required; foundation tests do not satisfy ingestion/modeling/public-release requirements.

## Test layers

- Unit: type/format inference, cleaning reconciliation, eligibility, split rules, query AST validation, budget arithmetic, state transitions.
- Integration: PostgreSQL migrations/ownership, object-store authorization, outbox/queue/checkpoint recovery, actual sandbox limits, offline UI compilation.
- Contract: API/schema compatibility, generated TS types, artifact manifests, bridge messages, provider structured outputs.
- End-to-end: upload → configuration → progress → dashboard → export → deletion in a real browser.
- Adversarial: Python/JS escapes, parser attacks, prompt injection, IDOR, CSRF, resource abuse, artifact path traversal.

Use a fake deterministic model provider for ordinary CI so tests do not depend on paid calls or unstable output. Add a small separately gated live-provider smoke suite with token/cost caps. Never send private fixtures externally.

## Fixture matrix

| Fixture | Expected behavior |
| --- | --- |
| Sales CSV with missing numbers, padded categories, date ambiguity, IDs | Conservative cleaning, preserved ambiguous values/IDs, reconciled report |
| Quoted delimiters/newlines, UTF-8 BOM, duplicate headers | Correct parse and canonical-name mapping |
| Broken encoding, ragged rows, empty file, oversized cell/file/table | Actionable rejection without silent loss or excessive resource use |
| SQLite with two ordinary tables | Explicit selection and valid profile |
| SQLite corrupt/virtual/view/WAL-dependent/expensive schema | Bounded rejection; no unsafe schema execution |
| Binary and multiclass classification | Valid partitioning, reference/candidate metrics, labeled confusion matrix |
| Regression with missing features | Training-only preprocessing and valid metrics |
| Constant target, rare classes, few labels, no usable features | Model skipped with reason; dashboard remains usable |
| Repeated entities or temporal data | Appropriate configured split; no entity/future overlap |
| Target proxy/high-cardinality text | Exclusion warning, feature/memory caps |
| Instruction-like cells and malicious labels | Treated as text; permissions unchanged |
| Invalid React/import/network request/infinite loop | Rejection or bounded recovery; trusted parent remains usable |

## Critical correctness checks

Reconcile every removed or changed row against provenance. Compare known synthetic aggregates exactly (floating-point metrics with declared tolerances). Introduce test-only category/extreme values to prove training preprocessing does not learn from held-out data. Verify target absent from features, group separation, chronological ordering, and reproducible split hashes. Dashboard totals must agree with artifacts before and after filters.

Simulate worker death before and after publication; ensure one committed artifact version and bounded retries. Cancel during upload, code execution, and publication. Delete while a run is active; verify no stale worker can resurrect outputs. Replay/stale MessageChannel requests and forged resource IDs must fail.

## Requirements traceability

| Requirement | Required evidence |
| --- | --- |
| FR-01 | Two-user API/SSE/download/query tests |
| FR-02–FR-04 | CSV/SQLite ingestion fixture report and limit probes |
| FR-05–FR-06 | Profile golden values and cleaning reconciliation |
| FR-07 | Model fixtures, split/preprocessing checks, skip reasons |
| FR-08–FR-09 | Browser generated/fallback/filter tests, metric comparisons |
| FR-10 | Queue/reconnect/restart/cancel fault injection |
| FR-11 | Export contents, hashes, formula neutralization |
| FR-12 | Disclosure, log redaction, deletion/restore tests |
| FR-13 | Immutable history/rerun tests |
| FR-14 | Narrative/metric reference validation |

## Release evidence template

Record commit, environment/runtime/image versions, test commands, pass/fail/skip counts, fixture hashes, provider/model and prompt versions, benchmark concurrency, p50/p95 duration, token/cost usage, known limitations, and blocker links. Skipped security gates block public release. Maintain a release checklist in the release PR and link the evidence from project memory.
