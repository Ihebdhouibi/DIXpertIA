<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-022. À démarrer tôt (phase 1). -->

# TICKET-DB-014 — Add API tests, fix the Dockerfile, rewrite `.env.example` and the setup documentation

## Context
The repository has no automated tests: no `tests/` directory, and neither pytest nor vitest is declared. Several high-severity defects found by the database audit would have been caught by a single test per route: unauthenticated routes, routes that always return 500, broken user creation.

## Problem
- **No tests at all.** CI runs ruff and `tsc` only.
- **The `Dockerfile` cannot start the API:** `uvicorn app.main:app`, while the module is `main:app` at the repository root. It uses Python 3.12 while CI runs 3.11, and installs Pango/Cairo for WeasyPrint although PDFs are produced with ReportLab.
- **`.env.example` lists none of the real variables.** It only has `GEMINI_API_KEY` and `APP_URL` from AI Studio. In particular, `SECRET_KEY` is missing, which makes the insecure JWT fallback the default (TICKET-DB-004).
- **`docs/DOCUMENTATION.MD` describes the former JSON backend.**
- `server.ts` spawns `python3`, usually absent on Windows, and is not used by any npm script.
- Unused dependencies: `@google/genai`, `mailtrap`.

## Current Behavior
A new developer, or a deployment, following the repository either fails to start, or starts without `SECRET_KEY`.

## Expected Behavior
- CI runs an API test suite against a throw-away PostgreSQL.
- The image starts.
- A new setup succeeds by following the documentation alone.

## Technical Analysis
The audit's runtime test script already encodes 20 scenarios: anonymous, employee, accountant, admin and inactive account, on every sensitive route. They can be ported to pytest + `TestClient` almost directly.

## Root Cause
Prototype heritage that was never updated.

## Impact
Every future fix can silently break another route. Deployments are error-prone and insecure by default.

## Proposed Solution
1. `tests/` with pytest, a PostgreSQL service in GitHub Actions, and `alembic upgrade head` per run. Include:
   - an **authorisation matrix test**: every route × {anonymous, employee, accountant, admin, inactive};
   - one regression test per audit finding fixed.
2. Add a `test` job to `.github/workflows/lint.yml`.
3. `Dockerfile`: `python:3.11-slim`, `CMD ["uvicorn", "main:app", ...]`, without the WeasyPrint system packages.
4. `.env.example`: `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_URL`, `SMTP_HOST/PORT/USER/PASSWORD/FROM`, each with an obviously fake value.
5. Rewrite the setup section of the documentation: PostgreSQL install, `.venv`, `.env`, `alembic upgrade head`, the seed script, then running the back end and the front end.
6. Remove `server.ts` (or document it) and the unused dependencies.

## Acceptance Criteria
- [ ] `pytest` runs in CI and fails on any unauthenticated non-public route.
- [ ] `docker build` and `docker run` start the API and answer on `/openapi.json`.
- [ ] `.env.example` contains every variable read by `app/core/config.py`.
- [ ] A fresh clone can be set up by following the documentation only.

## Evidence
`git ls-files` shows no test files; `Dockerfile:1`, `:14`; `.env.example`; `docs/DOCUMENTATION.MD:42`. The Dockerfile was not executed (Docker is not installed on the audit machine), so its failure is derived from the code.

## Related Findings
AUDIT-DB-022 (LOW)

## Dependencies
None. **Start early:** the authorisation tests protect every other remediation ticket.

## Estimated Complexity
M
