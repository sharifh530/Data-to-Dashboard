# Foundation verification — 2026-09-16

## Environment

Windows; Node 24.20.0; npm 11.19.0; Python 3.13.7; uv 0.12.15. React 19.3.0, TypeScript 5.9.3, Playwright 1.63.0, FastAPI 0.141.1. Lockfiles contain all resolved dependencies. No Git commit, remote CI run, or deployment exists.

## Evidence

| Check | Result |
| --- | --- |
| `npm run check` | Passed: ESLint, TypeScript, Ruff lint/format, mypy, tests, schema drift, fixture compilation |
| Python tests | 24 passed: health/readiness, hosted rejection, disabled execution, configuration, preflight and probe validation |
| TypeScript tests | 4 passed: instance binding, input rejection, replay/budget caps, disposal |
| `npm run test:browser` | 5 passed in Chromium: filters/reset, boundary probes, response policy, fallback, forged messages |
| HTTP smoke | Lab 200; API liveness ok; uploads/execution/persistence explicitly disabled |
| `npm run sandbox:preflight` | Blocked, exit 2: `DOCKER_UNAVAILABLE` |
| Actual Python container probes | NOT RUN: Linux engine unavailable |
| npm installation audit | Zero known vulnerabilities reported at installation; not a security audit |

The browser test independently checks a server counter to confirm synthetic exfiltration never reached the server. Parent DOM, cookies, local storage, and eval attempts fail in the actual iframe. Only reviewed fixed React and synthetic aggregates are used.

An initial filter test failed on an exact label lookup; an explicit accessible name fixed it and the full browser suite passed. TypeScript 7 was rejected due to the generator peer range; 5.9.3 is pinned without bypassing dependency checks. Two upstream Python test-client deprecation warnings remain (httpx compatibility and an AnyIO alias).

## Limits

- Docker's engine was unreachable initially and after a hidden startup attempt. No daemon configuration or hostile Python execution occurred.
- A registered runsc name alone does not prove enforcement. The synthetic launcher is unexecuted against a real runtime; its checks are unit-level only.
- CPU/memory/PID/disk abuse, escapes, actual cleanup under faults, parser attacks, and UI infinite-loop recovery remain unverified.
- No authentication, database, queue, uploads, LLM, training, generated-source compilation, or deployment exists.
- Two loopback hostnames test origin/cookie separation; production needs a separate untrusted-content site.
- Browser coverage is Chromium only. Broader accessibility/responsive and other browsers remain later work.

Next gate: working dedicated Linux with runsc or an evaluated microVM backend, fixed synthetic probe execution, then resource/cancellation/escape tests. Provider-independent database and product work can proceed while this runtime dependency is resolved.
