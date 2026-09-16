# Deployment and operations plan

Deployment provider and credentials are not selected. This plan defines requirements, not deployed infrastructure.

## Environments and rollout

Local: synthetic/trusted fixtures, fake provider by default, documented execution profile. Staging: production-equivalent isolation, separate secrets/storage, small quotas. Production pilot: authenticated users, no public sharing, hardened runtime, enforced disclosure/retention, and operational owner.

Build reviewed immutable images, generate dependency inventories, scan them, apply backwards-compatible database migrations, deploy API/worker/renderer with compatible schemas, run smoke checks, and then enable new run admission. Keep job image and prompt versions attached to each run. Drain or cancel incompatible in-flight work before destructive migrations. Roll back application images only when database/contract compatibility permits; use forward repair for incompatible schema changes.

## Observability

Correlate request_id, run_id, stage, attempt_id, and runtime_id. Log stage decisions/status and redacted error codes, not raw datasets or hidden reasoning. Capture queue age, job duration, stage failures, fallback rate, model skip reasons, runtime kills, cancellation latency, input/output sizes, provider latency/tokens, estimated spend, and deletion backlog. Store model traces only with explicit redaction and opt-in policy.

Initial alerts: no worker heartbeats for two minutes; oldest runnable job above five minutes; run failure rate above 20% over at least ten runs; any detected sandbox escape or cross-user access; purge backlog older than 24 hours; budget/queue saturation. Tune thresholds using measured traffic.

## Recovery playbooks

| Incident | Immediate response | Recovery evidence |
| --- | --- | --- |
| Provider outage/rate limit | Stop excess retries, preserve checkpoints, explain retryable failure | Resume/new-run behavior within budgets |
| Worker crash | Reclaim expired lease and resume validated stage | No duplicate publication |
| Suspected sandbox compromise | Disable new execution, isolate runtime hosts, revoke broker credentials, preserve redacted evidence | Root-cause review and rebuilt/patched runtime before re-enable |
| Generated UI regression | Force validated spec renderer and disable generated bundles | Browser tests and corrected bundle policy |
| Storage outage | Stop publication; retain retryable state | Hash/manifest consistency after restoration |
| Deletion failure | Keep tombstones active and retry cleanup | All derived objects/checkpoints removed |

## Backup and retention

Proposed pilot targets: database backup every 24 hours, seven-day backup retention, recovery point objective 24 hours and recovery time objective four hours. These are unverified targets until a restore rehearsal passes. Back up metadata and necessary artifacts consistently; retain hashes to detect missing objects. Restore into an isolated environment, apply deletion tombstones, verify ownership and artifact access, and only then reopen service. Do not restore deleted content into active access.

## Costs and capacity

Track per-run provider tokens, runtime CPU seconds, artifact storage, and queue occupancy. Dollar estimates require chosen provider/runtime prices and a versioned rate table. Enforce per-user concurrency and global queue depth before accepting work. Load-test the proposed five concurrent runs; raise limits only after measurements. Keep admission and code-execution kill switches independent so existing verified dashboards can remain readable during an execution incident.
