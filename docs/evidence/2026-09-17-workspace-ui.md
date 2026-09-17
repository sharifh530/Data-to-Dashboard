# B12 local workspace UI slice

2026-09-17. Implemented same-origin reviewed React shell with local ticket sign-in, projects, raw uploads/downloads, paginated datasets/history, sample stage polling/cancellation and logout. Added owner-scoped paginated dataset listing. Generated code is not served in this origin. CSP and exact static asset allowlist are enforced by the API. ADR-019 records the choice.

Validation:

- `npm run contracts:generate`: OpenAPI/TypeScript updated.
- `npm run check`: passed lint/types, four protocol tests, Ruff/mypy, Python (53 passed/33 PostgreSQL skipped), contract checks and builds.
- `npm run test:postgres`: 86 passed, no skips; two existing upstream test-client warnings.
- `npm run test:web`: one Chromium journey passed against a real ephemeral SQLite API. Sign-in, create project, raw upload/download, reload persistence, queue/cancel, responsive overflow and logout checked; no page JavaScript errors.
- Desktop 1280px and mobile 390px screenshots inspected. Minor byte-count display and success-notice fixes followed; lint/types and browser journey passed again.
- Project-owned PostgreSQL verified and API restarted at 127.0.0.1:8000 with the new UI. No login credential was included in Git or browser URLs.

Browser test traces are disabled to avoid collecting sign-in codes; its temporary ticket file is ignored. CI now includes test:web, but remote CI results are not claimed. Renderer isolation fixtures were unchanged, so their separate suite was not rerun. This is not a comprehensive accessibility audit or a generated-dashboard acceptance test. UI polls active runs rather than consuming SSE. Inspection remains blocked by the unavailable hardened execution runtime.
