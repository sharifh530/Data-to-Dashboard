# Project memory

These version-controlled files provide continuity across sessions; they are not a background service or automatic external memory.

- [STATE.md](STATE.md): concise current truth, validation, and next action.
- [TASKS.md](TASKS.md): stable work IDs and status ledger.
- [SESSION_LOG.md](SESSION_LOG.md): append-only history of completed work and evidence.

Read state/tasks at session start. Update them after meaningful work and before ending a session. Keep planned work separate from implemented work. Use TODO, IN_PROGRESS, BLOCKED, or DONE; blocked entries must name the missing condition and next action. Store architecture in `docs/DECISIONS.md`, not only in a log. Never store secrets or private sample rows here.
