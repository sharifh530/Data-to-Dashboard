# WSL sandbox establishment evidence

Final `npm run check` passed: JS lint/types, four protocol tests, Ruff/format/mypy, Python 53 passed/33 PostgreSQL skipped, contract drift checks and builds. PostgreSQL/browser suites were not repeated for this runtime-only change; prior evidence remains separate.

User selected creation of a project-specific WSL2 environment on 2026-09-17. Docker Desktop was now reachable, but initial `npm run sandbox:preflight` returned RUNSC_MISSING. Installed a separate dtd-sandbox distribution, Docker and gVisor, without changing Docker Desktop or other distributions.

Observed versions and setup are in [sandbox runbook](../SANDBOX_WSL.md). `npm run sandbox:wsl -- sync` copied only reviewed sources. `npm run sandbox:wsl -- preflight` passed registration detection with PROBES_REQUIRED and execution disabled.

Built probe image `sha256:9f2b04b20bd0ddaecaaece3052ba9f886186f8c725081716101d9d85c85e156f` from pinned Python base `sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285`. `npm run sandbox:wsl -- probe --image <that image>` passed all eight checks: non-root, read-only root, denied IPv4, IPv6, metadata and DNS, no runtime socket and no provider secret. Execution remained false.

Corrected the old root-write check, which could mistake permission denial for a read-only filesystem. The image now includes a world-writable test file; the probe requires EROFS specifically. A negative control ran the same trusted fixed probe without --read-only under runsc: it exited 1 and reported read_only_root false. Container inventory afterwards contained no dtd-probe containers.

`node scripts/python.mjs -m pytest tests/python/test_execution.py`: 9 passed. These are policy/preflight unit tests, separate from the actual runtime probe. No uploaded data or generated source was executed. B01 remains partial until resource/termination and adversarial execution checks are complete. Linux package installation and image build succeeded; Docker emitted a legacy-builder deprecation warning. This evidence does not establish escape resistance or hosted release readiness.
