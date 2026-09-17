# Real resource and termination probes

Executed inside the dedicated dtd-sandbox WSL2 gVisor runtime on 2026-09-17. These are fixed reviewed workloads, never uploaded or LLM-generated code. Resource image: `sha256:8378a2a2d99e2b5e531ade78fe170583681ecf6452f6e9a45517fca712a2f4c3`, built from the same pinned Python base recorded in the sandbox runbook.

The test profile deliberately uses smaller limits than planned analysis jobs: 0.5 CPU, 256 MiB RAM with equal swap limit, 8 MiB scratch, 128 host tasks, 32 guest processes, 64 KiB retained output. All jobs retain runsc, no network, non-root, read-only root, dropped capabilities and no host mounts.

| Case | Evidence required and observed |
| --- | --- |
| Scratch | A bounded 16 MiB write hit ENOSPC against the 8 MiB tmpfs |
| Guest processes | Bounded fork loop returned EAGAIN before 32 children; reaped children |
| Memory | A bounded 512 MiB allocation was stopped; Docker reported OOMKilled and nonzero exit |
| Output | Excess output triggered termination; retained output stayed at exactly 65,536 bytes |
| CPU | Four busy processes ran; host cgroup v2 cpu.stat recorded throttling |
| Deadline | Busy parent/children reached readiness; three-second deadline killed the container |
| Cancellation | After parent and three children were running, external kill stopped the whole container |

For CPU/deadline/cancellation, the host cgroup was absent or contained no processes after termination. Every case force-removed only its generated container and verified absence. No dtd-probe containers remained after the suite. Seven cases passed in the final policy configuration; the original eight isolation checks passed again.

Failures found and corrected: a host PID cap of 32 caused the gVisor runtime to exit, rather than yielding a useful guest fork-limit result. Guest tasks and runtime host threads are distinct, so the reviewed policy now sets a 128-task host cgroup cap and guest RLIMIT_NPROC 32. Under output flooding, stopping the reader could leave the Docker attach client blocked even after container kill. Readers now discard excess bytes while continuing to drain; retained data remains capped.

Interpretation follows the [gVisor resource model](https://gvisor.dev/docs/architecture_guide/resources/): guest processes need not correspond one-to-one with host tasks. This is measured local behavior, not proof of every resource side channel or container escape resistance. Abrupt broker death/reaper recovery, API-triggered cancellation integration, hostile parsers and data/result collection remain separate work. The resource harness is not yet a production broker. Application execution remains disabled.

Commands: `npm run sandbox:wsl -- sync`, pinned Docker build from sandbox/resources, `npm run sandbox:wsl -- resources --image <resource digest>`, and the normal `probe --image <basic probe digest>`. Full application checks are recorded in the session log. No application database or UI behavior changed.
