# User experience specification

## Screens

| Screen | Required content | States |
| --- | --- | --- |
| Projects | project cards, create action, recent runs | empty, loading, error, populated |
| Upload | accepted formats/limits, file picker/drop zone, privacy summary | uploading, validating, rejected, ready |
| Dataset review | table selector, preview, types, quality warnings | selection needed, invalid parse, ready |
| Configure analysis | optional question, optional target, task/split/exclusions, provider disclosure | exploratory-only, modeling eligible/ineligible |
| Run progress | stage timeline, elapsed time, warnings, cancel, pending question | queued, running, paused, cancelling, failed |
| Dashboard | title, provenance, KPI cards, charts, filters, table, model tab, downloads | generated, fallback, partial result, unavailable |
| Run history | dataset version, start time, status, configuration | empty, list, deleted resource |
| Dataset settings | retention date, delete action and scope | confirming deletion, deleting, deleted |

## Interaction rules

Upload failure preserves configuration where safe and explains how to repair the file. A SQLite table selector shows row-count estimates as estimates until counted. Users see the target and evaluation split before starting. Disclosures use plain language and name the configured provider; consent/version is recorded.

Progress is stage-based, not a fabricated percentage. Show completed evidence and next stage, with reconnect status if SSE drops. Refreshing the page rehydrates the run. Pending questions explain their effect and offer a conservative option when possible. Cancellation shows `Cancelling` until compute is actually stopped.

Dashboard filters visibly identify active selections and provide Reset. Filter changes update related charts/KPIs consistently; model evaluation metrics remain tied to the original evaluation set and are labeled accordingly. Empty filtered results show a useful no-results message. Model reports explain target, excluded rows, split, reference comparison, metrics, and limitations. Cleaning report supports before/after comparison and source inspection as escaped text.

Fallback mode displays a small factual notice that a standard layout was used. Failed modeling displays its reason without hiding successful exploratory results. A full failure offers a new run with preserved configuration and a request ID; it must not imply that unvalidated artifacts are usable.

## Accessibility and responsive behavior

Use semantic headings, labeled inputs, visible focus, keyboard-operable filters, announced status updates, and sufficient contrast. Charts need text summaries and tabular alternatives. Never encode meaning only in color. Use responsive single-column cards on phones; contain wide data tables in their own scroll region. Keep chart labels legible and truncate long fields only with an accessible full-name option. Respect reduced motion. Error/reset controls remain in the trusted parent even if the generated iframe is broken.

## Demo scenarios

1. Messy sales CSV → regression target → cleaning report → dashboard filters → export.
2. SQLite with multiple tables → selection → exploratory-only dashboard.
3. Small/constant-target data → modeling skipped with explanation.
4. Deliberately invalid generated React → working fallback dashboard.
5. Cancel a slow run, reconnect to another, then delete an old dataset.
