# Persistence and local authentication

Implemented on 2026-09-17: B03 and the local scope of B04. Hosted identity is tracked separately as B04H and remains a release prerequisite.

## Database setup

PostgreSQL stores application metadata; uploaded SQLite files will be parsed separately in isolated runtimes. SQLAlchemy models and Alembic revision `a0ae31772253` define 15 application tables. Composite foreign keys prevent dataset-version/run/artifact/dashboard references from crossing projects or runs. Raw upload keys/hashes live directly on dataset rows to avoid circular artifact references. Worker-related tables are storage contracts, not functioning workers.

PostgreSQL 17.6 is installed locally. The helper creates only `.local/postgres/data`, uses loopback port 55432, and creates `dtd` and `dtd_test`. It does not modify the system PostgreSQL service. Generated credentials stay in ignored `.local` and `.env`; do not publish them.

```powershell
node scripts/python.mjs scripts/local-postgres.py --bin 'C:\Program Files\PostgreSQL\17\bin'
npm run db:migrate
npm run db:check
npm run dev:api
```

Stop only this cluster with:

```powershell
node scripts/python.mjs scripts/local-postgres.py --bin 'C:\Program Files\PostgreSQL\17\bin' --stop
```

On another machine, configure `DTD_DATABASE_URL` in ignored `.env` for an isolated PostgreSQL database, then migrate. Production needs separate migration and least-privilege application roles; the helper account is a local development owner. The API does not create tables automatically and rejects startup when a configured database is not at the current revision. Without a database URL, health/lab still work and protected APIs return 503. Analysis readiness remains 503 regardless of database availability.

## Sign-in flow

Run `npm run auth:issue -- --subject alice` locally. This operator-only command prints a five-minute, single-use secret token. No public provisioning endpoint exists. Submit it in the JSON body of `POST /api/v1/auth/exchange` with the exact `DTD_APP_ORIGIN` (default `http://127.0.0.1:8000`). The exchange atomically consumes the token and issues an eight-hour server-side session plus a CSRF token.

`GET /api/v1/auth/session` returns the current user ID and CSRF token. Mutations require the session cookie, exact Origin, and `X-CSRF-Token`. `POST /api/v1/auth/logout` revokes the session and clears the cookie. Re-login rotates the presented session; disabled users are rejected. Tokens contain 256 random bits and only hashes persist. Validation errors do not echo token inputs.

Cookies are host-only, HttpOnly, Path=/, SameSite=Strict. HTTPS uses Secure `__Host-dtd_session`; loopback HTTP uses `dtd_local_session` without Secure for local development only. Hosted startup remains disabled. CSRF checks are independent of SameSite, following [OWASP session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html).

No sign-in UI exists yet. After issuing a token, use this PowerShell example to exercise the API without embedding the token in shell history:

```powershell
$loginToken = Read-Host 'Paste the single-use token'
$authReply = Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/auth/exchange' -ContentType 'application/json' -Headers @{Origin='http://127.0.0.1:8000'} -Body (@{token=$loginToken} | ConvertTo-Json) -SessionVariable dashboardSession
Remove-Variable loginToken
$projectHeaders = @{Origin='http://127.0.0.1:8000'; 'X-CSRF-Token'=$authReply.csrf_token; 'Idempotency-Key'=[guid]::NewGuid().ToString()}
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/projects' -ContentType 'application/json' -Headers $projectHeaders -Body '{"name":"Sales analysis"}' -WebSession $dashboardSession
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/v1/projects' -WebSession $dashboardSession
```

## Ownership and replay

Create/list/read projects are implemented. Ownership comes from the session, never a user-ID header. Foreign IDs/cursors and tombstoned projects return 404. Lists use UUID-ordered cursors and limits of 1–100; they are not chronological.

Creation requires `Idempotency-Key`. Same owner/route/key and normalized payload replay the project for 24 hours; a different payload returns 409. Unique constraints plus rollback prevent concurrent duplicate projects. Keys are independent across users. Before adding project editing, store immutable response snapshots if exact replay must survive edits; current projects cannot be edited through the API.

Deletion/renaming, hosted OIDC, authentication throttling, session cleanup, and the remaining data-resource endpoints are future work. Audit records contain action/resource IDs, not tokens or raw data.

## Tests

```powershell
npm run check
npm run test:postgres
npm run db:check
```

Default checks run SQLite cases and explicitly skip PostgreSQL cases when no test URL is set. `test:postgres` derives only the dedicated local `dtd_test` URL, or uses an explicit `DTD_TEST_DATABASE_URL`. Tests create/drop randomly named schemas, never a database or existing schema. Upgrade/downgrade/upgrade recovery runs only on these disposable schemas; it does not replace production backups. CI provides an ephemeral PostgreSQL service. See [evidence](evidence/2026-09-17-persistence-auth.md).
