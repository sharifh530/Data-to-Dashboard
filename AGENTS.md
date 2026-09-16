# Repository working instructions

## Start each session

Read `memory/STATE.md`, `memory/TASKS.md`, and the relevant specification before editing. Consult `docs/DECISIONS.md` before changing architecture. Inspect existing code and actual tool availability; never assume planned services exist.

## Project invariants

- Deliver the user's core features: generated Pandas code, a valid baseline model when data supports it, and generated React UI.
- Never execute generated Python in the API process or on the developer host. Never execute generated JavaScript in the authenticated application origin.
- Treat uploads, column names, cells, model output, and generated artifacts as untrusted input.
- Preserve immutable raw data and transformation provenance. Split modeling data before fitting preprocessing.
- Enforce ownership in every API, event subscription, artifact download, and renderer data request.
- Do not put credentials, real private data, tokens, or raw LLM payloads in Git or memory files.
- Use bounded retries, timeouts, resource budgets, and validated structured outputs. Fail closed on missing sandbox enforcement.
- Documentation defaults are design proposals until tested. Record limitations accurately.

## Working process

Pick a task from `memory/TASKS.md`, mark it in progress, and implement a small reviewable slice. Update affected docs and ADRs when decisions change. Run relevant checks; record exact commands and outcomes. Do not claim tests passed if they were not run. Do not add application scaffolding solely to make a planned directory tree appear complete.

## End each session

The user authorized pushing to `https://github.com/sharifh530/Data-to-Dashboard.git` after every completed major task (2026-09-17). After relevant checks and documentation/memory updates, commit the completed milestone and push to the configured remote. Inspect remote changes first, preserve existing history, never force-push, and verify the pushed commit. Do not request permission again for routine milestone pushes. If authentication or branch protection blocks a push, report the concrete blocker and retain the local commit.

Update `memory/STATE.md` with current status, actual changes, validation, blockers, and the next concrete action. Update task statuses and append a dated entry to `memory/SESSION_LOG.md`. Keep state concise; move historical detail into the session log. Do not overwrite prior history or mark a milestone complete without its acceptance evidence.
