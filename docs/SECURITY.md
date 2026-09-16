# Security and privacy design

This is a release-blocking specification, not a claim of an audited implementation.

## Threat model

| Threat | Required controls | Verification |
| --- | --- | --- |
| Host compromise from Python/parser/build tools | Independent hardened runtime; no privileged mode, host mounts, runtime socket, or secrets; restricted syscalls/capabilities | Escape probes and runtime policy inspection |
| Resource exhaustion | CPU, memory, process, file, disk, output, and wall-clock limits; bounded queue/user quotas | Infinite loop, fork, disk fill, large stdout, parser-bomb fixtures |
| Network exfiltration | Deny job egress including DNS, metadata endpoints, IPv4/IPv6; no provider key in jobs | Network probes from inside actual runtime |
| Prompt injection in data | Label data as data; minimize context; no data-directed permission changes; tool authorization outside prompts | Malicious cells/table names cannot expand tools or fetch secrets |
| Generated browser code steals session/data | Separate untrusted site, opaque-origin sandbox, CSP, no credentials; restricted data broker | DOM/cookie/storage/network/navigation attempts |
| Cross-user artifact access | Server-side owner scoping on all endpoints and object-key resolution | Two-user ID substitution suite |
| Uploaded SQLite attacks | Isolated parsing, read-only immutable mode, no extensions/virtual tables/attachments, bounded queries | Crafted schema, corrupt file, expensive query fixtures |
| Malicious output promotion | Schema/size/type checks, safe paths, no symlink following, bounded JSON parsing | Traversal, symbolic links, misleading MIME fixtures |
| Sensitive data disclosure | Minimized/masked provider context, no raw telemetry, retention controls | Egress-payload and log inspection |

## Python and compiler policy

Starting per-job limits: 2 vCPU, 2 GiB RAM, 64 processes, 512 MiB scratch, 20 MiB stdout/stderr combined, 120 seconds for cleaning/modeling, 30 seconds for parsing and UI compilation. The ten-minute run deadline still applies. Adjust only through measured ADR changes. Terminate the whole process group/runtime on timeout or cancellation.

Use a non-root UID, read-only root filesystem, per-attempt temporary filesystem, dropped capabilities, no-new-privileges, a restrictive seccomp policy where supported, and independently enforced network denial. Install dependencies only when building reviewed images; never install a dependency chosen by the LLM. Destroy job storage after artifact collection. Do not deserialize generated pickle/joblib objects in trusted services; MVP exports reports and code rather than executable model binaries.

Static Python/JS policy checks improve diagnostics but are not security boundaries. A Python import allowlist does not make `exec` safe. gVisor or a microVM reduces host exposure but still requires patching, workload policies, and operational testing; see [gVisor security model](https://gvisor.dev/docs/architecture_guide/security/).

## Generated React policy

Host generated content on a separate site without application cookies. Embed with `sandbox="allow-scripts"` only; do not add `allow-same-origin`, navigation, forms, popups, or downloads. This follows the isolation concerns documented for [iframes](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/iframe).

Compile a single component against vendored React/dashboard-kit in an isolated offline build. Forbid arbitrary imports, runtime eval/Function, HTML injection, URL-bearing user content, and raw CSS; accept design tokens/classes from the kit. Enforce response CSP using per-artifact script hashes: default deny, connect none, object none, base none, form-action none; permit only required hashed scripts and reviewed styles. No remote images/fonts or arbitrary frame navigation. Prototype CSP compatibility before promising full generated-code support.

The parent initializes a MessageChannel after validating the iframe window and a per-instance nonce. Opaque-origin messages cannot be authenticated by origin alone. Transfer only the dedicated port, then accept versioned, schema-checked messages with run binding, request IDs, limits, and stale-instance rejection. The server independently authorizes the parent request. The renderer receives bounded aggregated results, no raw credentials, signed URLs, arbitrary queries, or unrestricted row access. A hung iframe has an outer reset/fallback control; test browser responsiveness because iframe isolation does not guarantee CPU isolation.

## Privacy and lifecycle

Before first external-model use, show provider identity, context categories, and whether masked samples are included. Default to schema/statistics and mask likely identifiers; masking is best-effort, not guaranteed anonymization. Do not send entire files. Sensitive-category datasets are out of scope for the initial hosted pilot. Provider retention/residency terms must be reviewed when choosing the provider; no zero-retention promise is implied here.

Default proposed raw/derived retention: 30 days; redacted operational logs: 14 days. User deletion immediately tombstones data and revokes access, cancels runs, then purges uploads, artifacts, checkpoints, queued payload references, and caches within 24 hours. Keep a minimal non-content deletion audit. Backup copies expire within the configured backup window (initial target: seven days); restoration must replay deletion tombstones before reopening access. Explain backup expiry in the UI.

## Public release gates

- Verify enforced isolation, egress denial, cleanup, cancellation, and resource caps on the deployed runtime.
- Pass ownership and renderer attack tests; prove generated content cannot access application tokens.
- Review dependencies/images and patch policy; ensure secrets never enter runtime jobs or client bundles.
- Test provider disclosure, log redaction, deletion, backup restore, and stale artifact revocation.
- Assign an incident owner and document a kill switch that disables new code execution.
