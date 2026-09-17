# API and persistence specification

Target `/api/v1` contracts. Implemented: health/capabilities, local authentication, projects, synthetic run submission/history/detail, SSE and cancellation. Remaining analysis/data/export/deletion endpoints below are planned. See [persistence/auth](PERSISTENCE_AND_AUTH.md) and [run processing](RUN_PROCESSING.md) for actual behavior; planned analysis contracts do not override the synthetic API.

## Common conventions

Opaque UUID resource IDs; UTC timestamps; authenticated same-site secure HttpOnly sessions; CSRF protection on mutations; explicit CORS allowlist. Authentication provider choice is open. All database lookups include owner/project scope. Foreign unauthorized resources return 404. Lists use cursor pagination with maximum page size 100.

Mutation idempotency keys are scoped to owner + route, retained 24 hours, and tied to a request hash; changed payload with same key returns 409. Errors use `{ "error": { "code": "...", "message": "...", "details": {}, "request_id": "...", "retryable": false } }`. Never return internal tracebacks, object credentials, or full data rows in errors.

## Endpoints

| Method/path | Request | Response / semantics |
| --- | --- | --- |
| POST /projects | name | 201 project |
| GET /projects | cursor | owned projects |
| GET /projects/{id} | — | owned, nondeleted project or 404 |
| POST /projects/{id}/datasets | streamed multipart file | 202 dataset in validating state; enforce streaming byte limit |
| GET /datasets/{id} | — | validation status, tables, warnings |
| POST /datasets/{id}/selection | table, optional CSV parse overrides | 202 immutable selected dataset version; reject selection changes during run by creating new version |
| GET /datasets/{id}/preview | version, cursor | capped preview and profile status |
| POST /projects/{id}/runs | dataset_version_id, question, model config, disclosure acknowledgment | 202 run; outbox enqueue |
| GET /runs/{id} | — | state, stage, warnings, pending question, artifact metadata |
| GET /projects/{id}/runs | cursor | immutable run history |
| GET /runs/{id}/events | Last-Event-ID | authenticated SSE progress stream |
| POST /runs/{id}/answers | question_id, typed answer | 202 resume; stale/already resolved question returns 409 |
| POST /runs/{id}/cancel | — | 202 cancelling or 200 already terminal |
| GET /runs/{id}/dashboard | — | validated spec, render mode, scoped bundle reference |
| POST /runs/{id}/queries | query_id, typed filters, cursor/sort | bounded dashboard data; ownership and field validation |
| GET /artifacts/{id}/download | — | authenticated streamed download; no permanent public URL |
| DELETE /datasets/{id} | — | 202 tombstone and cascade cleanup |
| DELETE /projects/{id} | — | 202 tombstone and cleanup of descendants |

Codes: 400 malformed request; 401 unauthenticated; 404 absent/unowned; 409 state conflict; 413 too large; 415 unsupported format; 422 invalid configuration; 429 quota exceeded with retry hint; 503 unavailable. Validation failures after upload appear as dataset status and structured reasons. Do not hold an HTTP request open for analysis execution.

Example run creation:

```json
{
  "dataset_version_id": "uuid",
  "question": "What drives order value?",
  "model": {"target": "order_value", "task": "regression", "split": "random", "exclude_columns": ["order_id"]},
  "disclosure_ack_version": "v1"
}
```

Setting `model` to null requests exploratory analysis only. A question does not implicitly authorize target selection.

## Entities

| Entity | Key fields / invariants |
| --- | --- |
| users | id, auth_subject (unique), created_at |
| projects | id, owner_id, name, deleted_at |
| datasets | id, project_id, raw_key, raw_sha256, format, status, deleted_at; raw reference lives here to avoid circular artifact linkage |
| dataset_versions | id, dataset_id, selected_table/parse_options, schema_hash, profile_ref; immutable |
| runs | id, project_id, dataset_version_id, config_json, status, stage, generation, cancellation_at, timestamps, budget_json |
| stage_attempts | id, run_id, stage, attempt_number, lease expiry, runtime_id, status; unique attempt identity |
| artifacts | id, project_id, run_id, kind, private_key, sha256, size_bytes, schema_version, validated_at, deletion_state; generated artifacts belong to a run |
| run_events | run_id, sequence, type, redacted payload, created_at; unique (run_id, sequence) |
| dashboards | id, run_id, spec_artifact_id, source_artifact_id, bundle_artifact_id, render_mode |
| pending_questions | id, run_id, typed payload, answered_at, expires_at |
| outbox | id, topic, payload reference, delivered_at, retry_count |
| idempotency_records | owner/route/key, request_hash, response_ref, expires_at |
| audit_events | actor, action, resource_id, timestamp, request_id; no raw content |

Provider-specific graph checkpoint tables are also managed/migrated and included in retention cleanup. Use FK constraints and transactional ownership consistency checks to prevent mismatched project/run/artifact references.

## State machines

Dataset: `uploading → validating → ready | rejected`; any nondeleted state may become `deleting → deleted`.

Run: `queued → running ↔ awaiting_input → succeeded | succeeded_with_warnings | failed`; queued/running/awaiting_input may enter `cancelling → cancelled`. Terminal states cannot resume; rerun creates a new run. Expired pending input transitions to failed with `INPUT_EXPIRED`. Lease recovery resumes the same logical stage with a new attempt. Publication transaction rejects cancellation, deletion, or a stale generation.

Event envelope: `schema_version`, `run_id`, `sequence`, `type`, `stage`, `timestamp`, `payload`. Types include stage_started, stage_completed, warning, input_required, budget_updated, run_finished. Do not expose hidden chain-of-thought; progress describes work performed and evidence.

Artifact manifest: input hash, configuration hash, source/prompt/schema/image versions, seed, artifact IDs/hashes, validation outcomes, warnings, timestamps. Storage paths use server-generated IDs such as `projects/{project_id}/runs/{run_id}/attempts/{attempt_id}/...`; never use filenames supplied by the model as authority.
