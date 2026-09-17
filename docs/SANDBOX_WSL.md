# Dedicated local gVisor sandbox

Provisioned and basic probes verified 2026-09-17 after the user selected a separate project WSL2 environment. This is a local development runtime, not a production security certification. Generated execution and uploaded-file inspection are still disabled pending resource/termination tests and broker integration.

## Installed environment

- Distribution: `dtd-sandbox`, Ubuntu 24.04, stored in ignored `.local/wsl/dtd-sandbox`.
- Bootstrap: official Ubuntu image `sha256:69cecf4bbf72d2d44a9eef1b71fb98c7fb973d78af11399deccef19beb008ad9`, exported without running the container, then imported using WSL2.
- Kernel observed: `6.6.87.2-microsoft-standard-WSL2`.
- Docker Engine: Ubuntu package 29.1.3. gVisor: official signed APT repository, `runsc 20260914.0`.
- systemd enabled. Windows drive automount, fstab mounting and Windows executable interoperability disabled in this distribution's `/etc/wsl.conf`. Observed mounts contain the WSL read-only driver share, not C:/H: drives. This configuration is defense in depth; WSL distributions share host infrastructure and are not a substitute for a production dedicated host.
- Docker Desktop was not reconfigured; its default context still lacks runsc. The dedicated daemon is accessed only through explicit `wsl -d dtd-sandbox` commands. No unauthenticated TCP Docker socket was opened.

Installed packages include systemd/systemd-sysv, docker.io, ca-certificates, curl, gnupg, python3 and runsc. Official installation instructions: [gVisor installation](https://gvisor.dev/docs/user_guide/install/), [Docker runtime registration](https://gvisor.dev/docs/user_guide/quick_start/docker/), [WSL per-distribution settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config). Registration used `runsc install` followed by `systemctl reload docker` inside this new distribution only. A first systemd start failed before wsl.conf was written; writing the configuration and terminating/restarting only dtd-sandbox corrected it.

## Repeat verified probes

From the repository on Windows:

```powershell
wsl -d dtd-sandbox -u root --cd / -- systemctl start docker
npm run sandbox:wsl -- sync
npm run sandbox:wsl -- preflight
wsl -d dtd-sandbox -u root --cd /opt/dtd -- docker build --build-arg BASE_IMAGE=python@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285 --iidfile /opt/dtd/probe-image-id sandbox/probe
$probeImage = (wsl -d dtd-sandbox -u root --cd / -- cat /opt/dtd/probe-image-id).Trim()
npm run sandbox:wsl -- probe --image $probeImage
```

The pinned Python image was pulled into the dedicated daemon before building. The wrapper transfers only reviewed probe sources through an in-memory tar stream to `/opt/dtd`; no project credentials, uploaded datasets or host directories are mounted. These commands require the previously provisioned distribution; they do not install one automatically. `sync` overwrites only the listed probe source paths.

The original `npm run sandbox:preflight` inspects the current Windows Docker context and therefore still returns RUNSC_MISSING. Use the WSL command for this runtime. A successful WSL preflight reports PROBES_REQUIRED with execution false; a successful probe also leaves execution false. No flag bypasses application admission.

To stop just this runtime, use `wsl --terminate dtd-sandbox`. This stops any work in that distribution. Start it again with an explicit WSL command. Do not use global WSL shutdown or unregister the distribution as routine cleanup. Keep its ignored virtual disk intact while needed; removal would destroy images/runtime state. It contains no application database or uploaded data.

## Remaining gate

Basic probes cover non-root, genuinely read-only root, IPv4/IPv6/metadata/DNS denial, no Docker socket and no provider keys. A writable-root negative control was rejected. Probe containers were removed. CPU, RAM, PID, scratch/output exhaustion, timed-out/cancelled process cleanup, adversarial parsers and actual data transfer/result validation remain to be tested. Next work must implement those tests, then isolated CSV/SQLite inspection; do not enable arbitrary code based on these basic checks alone.
