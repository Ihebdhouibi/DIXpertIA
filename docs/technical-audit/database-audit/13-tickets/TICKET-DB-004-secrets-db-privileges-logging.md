<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-006, 007, 008, 021. Priorité : phase 0. Recoupe l'issue #43. -->

# TICKET-DB-004 — Remove secret fallbacks, rotate exposed credentials, use a least-privilege database role, and stop leaking secrets to logs

## Context
The application starts without any environment configuration because secrets have hard-coded fallbacks. It connects as the PostgreSQL superuser, and unhandled database errors print full SQL parameters to the server log.

## Problem
1. **Hard-coded fallbacks.** `main.py:58` and `app/core/config.py:9` fall back to the same public `SECRET_KEY`. `app/core/config.py:8` falls back to a `DATABASE_URL` that contains the `postgres` superuser password. `.env.example` does not mention `SECRET_KEY` at all, so a deployment that follows the repository ends up on the public key, and anyone can then forge an admin token.
2. **`db.json` is versioned** since `4cec208`. It holds 3 bcrypt hashes of real accounts (2 admins, 1 accountant) and 1 password-reset token. These stay in git history.
3. **Superuser connection.** The app role `postgres` has `rolsuper`, `rolcreaterole`, `rolcreatedb` and `rolbypassrls`. Any application flaw becomes full control of the database server, and the RLS planned in #43 would be bypassed.
4. **Secrets in logs.**
   - The engine has no `hide_parameters=True`, so an `IntegrityError` prints every bound parameter, including the new user's e-mail and the **bcrypt hash of the temporary password**. Because user creation currently always fails (TICKET-DB-006), this happens on every attempt.
   - `tables.py:28` prints the full `DATABASE_URL`, password included.
5. **Server settings.** Connections and DDL are not logged, and `statement_timeout` and `idle_in_transaction_session_timeout` are 0.

## Current Behavior
- The app starts with no `.env` and silently uses the public key.
- Server log during user creation (redacted): `[parameters: {'id': 'USR-008', 'email': '<EMAIL>', …, 'hashedPassword': '<BCRYPT REDACTED>', …}]`.
- `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user` → `true, true`.

## Expected Behavior
- The app refuses to start without `SECRET_KEY` (at least 32 characters) and `DATABASE_URL`.
- It connects as a dedicated non-superuser role with only the privileges it needs.
- No secret, hash or e-mail ever reaches the logs.

## Technical Analysis
- A token forged with the fallback key was **rejected locally** (401), only because the local `.env` sets `SECRET_KEY`. The risk is entirely deployment-dependent, and the repository makes the unsafe configuration the default.
- `.env` itself was never committed: `git log --all -- .env` is empty.
- No raw SQL exists in the code base, so there is no known injection vector today. The superuser connection is an amplifier, not a direct exploit.
- `pg_hba.conf` only allows `127.0.0.1` and `::1`, with `scram-sha-256` everywhere. `listen_addresses = *` is compensated locally.

## Root Cause
Convenience defaults for local development that became the de facto configuration, and the default superuser of the installer.

## Impact
Full application compromise on any environment without `SECRET_KEY`. Full database server compromise from any application flaw. Password hashes and e-mails in logs.

## Proposed Solution
1. **Immediately, outside the code:**
   - rotate the `postgres` password on any environment that uses the repository value;
   - reset the passwords of the 3 accounts present in `db.json`.
2. Remove both fallbacks (`os.environ[...]`, validate the key length at startup). `main.py` must use `settings.SECRET_KEY` instead of its own copy.
3. Replace `db.json` with a seed script that contains no real hashes. Decide with the repository admin whether to rewrite history: this is destructive and breaks existing clones.
4. Create `dixpertia_migrator` (schema owner) and `dixpertia_app` (`LOGIN NOSUPERUSER NOBYPASSRLS`; `SELECT, INSERT, UPDATE` plus `USAGE` on sequences; `DELETE` only where a deletion is designed). Set `ALTER ROLE dixpertia_app SET statement_timeout = '30s'`.
5. Add `hide_parameters=True` to `create_engine`. Catch `IntegrityError` in write endpoints and return 409.
6. Make `tables.py` print host, port and database only.
7. Rewrite `.env.example` with the real variables and obviously fake values.
8. Add a secret scanner (`gitleaks` or `detect-secrets`) to pre-commit and CI.
9. For shared and production servers, enable `log_connections`, `log_disconnections`, `log_statement = 'ddl'` and `idle_in_transaction_session_timeout`.

## Acceptance Criteria
- [ ] `git grep -E 'getenv\("(SECRET_KEY|DATABASE_URL)",'` returns nothing.
- [ ] Starting without `SECRET_KEY` fails with an explicit error.
- [ ] A token signed with the former fallback key gets 401 on every environment.
- [ ] `db.json` contains no password hash or token, or no longer exists.
- [ ] The application role has `rolsuper = false` and `rolbypassrls = false`; `TRUNCATE` is refused for it.
- [ ] A forced duplicate-key error produces no `[parameters:` line in the log.
- [ ] `python tables.py` prints no password.
- [ ] `.env.example` lists `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL` and the `SMTP_*` variables.
- [ ] A secret scanner runs in CI.

## Evidence
- Catalog queries Q-DISC-003 and Q-SEC-001 to Q-SEC-003 (superuser, only login role, all privileges).
- Runtime test T-A08 (forged token rejected only thanks to the local `.env`).
- Redacted server log of 2026-10-02, line 434 (parameters printed on `IntegrityError`).
- `git grep` of the fallbacks. All values are redacted in the audit material.

## Related Findings
AUDIT-DB-006 (HIGH), AUDIT-DB-007 (HIGH), AUDIT-DB-008 (MEDIUM), AUDIT-DB-021 (LOW)

## Dependencies
Role split coordinated with TICKET-DB-001: migrations must run as the owner role. Overlaps #43 (least-privilege role, RLS): implement the role here, and RLS there.

## Estimated Complexity
M
