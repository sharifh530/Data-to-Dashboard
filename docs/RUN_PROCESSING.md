# Durable synthetic runs

Implemented 2026-09-17. This is the local orchestration milestone, not autonomous analysis. The only workflow uses fixed, reviewed sales aggregates. It accepts no uploaded data, Python source, JavaScript, provider calls, or prediction target. The existing React lab is independent; product run screens are B12.

## Start and submit

Start PostgreSQL and sign in using [local authentication](PERSISTENCE_AND_AUTH.md). Run `npm run db:migrate`, `npm run dev:api`, and, in another terminal, `npm run dev:worker`. The worker requires PostgreSQL and local mode. `npm run dev:worker -- --once` dispatches at most one message and processes at most one stage. Normal mode polls every 500 ms; Ctrl+C stops between stages. Stop only project-owned processes.

Using the authenticated cookie, exact Origin, CSRF header and an Idempotency-Key, POST `{}` to `/api/v1/projects/{project_id}/demo-runs`. The only optional field is `fixture: "sales-v1"`; unknown fields are rejected. A 202 response returns a run ID. GET `/api/v1/runs/{run_id}` for state, or `/api/v1/projects/{project_id}/runs` for cursor-paginated history. One unfinished run per owner is allowed; additional requests return 429. Reusing the original idempotency key returns the existing run for 24 hours.

Stages are `profile_fixture`, `summarize_fixture`, and `publish_fixture`. Expected final result is revenue 27200 and orders 176, explicitly marked synthetic. Dataset rows reference an internal fixture identifier; there is no corresponding uploaded object or downloadable artifact.

## Progress and cancellation

GET `/api/v1/runs/{run_id}/events` with the session cookie. Named SSE events carry JSON with schema_version, run_id, sequence, type and payload. Normal persisted events also carry a timestamp. `Last-Event-ID` resumes after an acknowledged integer sequence. A cursor ahead of the run returns 409; malformed cursors return 422. If older events are missing, a `snapshot` event provides current state and resets the cursor. There is no automatic retention job yet.

The stream checks ownership, session expiry/revocation, active owner and input tombstones on each poll. It emits keep-alive comments roughly every five seconds and ends after approximately 25 seconds; reconnect with the last received ID. Close the client EventSource after a terminal run event/snapshot. `access_revoked` requires closing the connection and signing in again if appropriate; `reconnect` indicates a temporary database failure. `follow=false` returns one finite replay batch (at most 100 events). Streaming and replay do not control worker execution.

POST `/api/v1/runs/{run_id}/cancel` requires Origin and CSRF and returns 200 with state. Queued work is cancelled immediately. Leased work enters `cancelling`; the active worker acknowledges, or another poll finalizes it once the five-second lease expires. An old worker cannot publish after cancellation wins the row lock. If publication commits first, cancellation returns the already successful run. Container termination is not implemented or tested by this fixture workflow.

## Persistence and recovery

Run creation, initial event, audit record and outbox message commit together. Dispatch inserts one work item per run and acknowledges its outbox message in the same transaction. Duplicate delivery is harmless. Workers claim run rows with PostgreSQL `FOR UPDATE SKIP LOCKED`, then assign a unique lease token and increment the generation. Checkpoints, stage status, events and publication commit atomically under the run lock.

Each lease lasts five seconds. Heartbeats extend valid leases; fixed stages complete immediately and need no heartbeat thread. Expired leases are reclaimed by the normal claim loop, with a maximum of three attempts per stage. Runs have a ten-minute deadline starting at their first claim. Completed checkpoints survive worker restarts. Late results require a matching generation, token and unexpired lease; publication also rechecks owner/input availability and the deadline. Fixed outputs are validated before checkpointing.

If the worker exits, restart the same command against the same migrated database. Database failures currently stop the worker; a process supervisor/restart policy is future operational work. Durable state and expired leases permit recovery. There is no Redis/Celery service, LangGraph workflow, external side effect, general retry scheduler, throughput benchmark or hosted-release claim.

Implementation references: [PostgreSQL row locking](https://www.postgresql.org/docs/17/sql-select.html) and [SSE event format](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events). Acceptance evidence is in [the milestone report](evidence/2026-09-17-run-processing.md).
