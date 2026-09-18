# Local workspace interface

Implemented 2026-09-17 as the first B12 slice. Build with `npm run build:web`, migrate with `npm run db:migrate`, start `npm run dev:api`, then open http://127.0.0.1:8000/. Use the origin configured in DTD_APP_ORIGIN exactly; localhost and 127.0.0.1 are different origins. The older port-4173 renderer isolation lab remains separate.

Issue a five-minute local ticket using `npm run auth:issue -- --subject your-name` and paste it into the password-style one-time access field. Tickets are not placed in URLs or browser storage. Sign-in exchanges the ticket for the existing HttpOnly session; a reload recovers that session. Sign out revokes it.

Create/select projects in the sidebar. Choose a file and its declared CSV/SQLite format, then Store dataset. Uploads preserve the original bytes, retain an idempotency key for retries, and show awaiting-inspection status. The original filename is only displayed locally while selected; stored files use their ID and declared format because filenames are not retained by the API. Checksums/IDs and original downloads are available in the stored-file list. The new GET `/projects/{id}/datasets` endpoint is owner-scoped and paginated; synthetic fixture references are excluded.

Try a sample run to exercise the fixed workflow. Start `npm run dev:worker` separately to process it. Without the worker it stays queued and can be cancelled. Active run status is polled every two seconds; the SSE backend remains available, but this first UI does not use it. History supports pagination and rehydrates after refresh. This sample does not inspect uploads, generate code or train models.

The application is reviewed React bundled by esbuild and served from the same API origin. CSP permits only same-origin scripts/styles/connections, disallows frames and inline/eval scripts, and has no external font dependency. Generated JavaScript is never included here. The separately isolated renderer is not yet integrated into the product shell.

Desktop and phone layouts use labeled controls, keyboard-visible native focus, status/error regions and real loading/empty states. This is not a completed accessibility audit. `npm run test:web` runs a Chromium journey against an ephemeral SQLite test API on 4180, exercising real sign-in, project creation, upload/download, reload, cancellation and logout. Test tickets live only in ignored local storage; browser traces are disabled for this test. It never connects to the normal local database. `npm run test:postgres` separately tests API ownership and pagination against PostgreSQL.

September 18 addition: **Inspect dataset** queues fixed CSV/SQLite parsing in gVisor. The owner-only preview shows table choice, row/column/empty counts and five rows. A later slice added optional CSV delimiter selection and **Use this table**, which stores a versioned table choice for later analysis. Changing the delimiter runs inspection again and clears the prior choice. See [setup and limits](INSPECTION.md). The browser acceptance suite can exercise real inspection when `DTD_TEST_INSPECTION_IMAGE` is configured.

Remaining B12 work: persistent dataset configuration, analysis progress, dashboard/model views, exports, recovery refinements and comprehensive accessibility checks. Hosted sign-in and analysis execution remain disabled.
