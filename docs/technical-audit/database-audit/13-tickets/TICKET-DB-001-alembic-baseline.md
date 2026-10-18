<!-- Brouillon destiné à GitHub (en anglais, convention du dépôt). Non encore publié. Findings : AUDIT-DB-015. -->

# TICKET-DB-001 — Create an Alembic baseline migration and stop using `create_all()` for schema changes

## Context
The schema is created by `Base.metadata.create_all()` (`tables.py:33`, `migrate_data.py:12`). Alembic is installed and wired to the models (`alembic/env.py`), but `alembic/versions/` is empty. Almost every other remediation ticket from the database audit changes an existing schema, so this is the prerequisite for all of them.

## Problem
There is no versioned schema history. `create_all()` creates missing tables but never alters existing ones, so any model change silently diverges from databases that already exist.

## Current Behavior
- `alembic/versions/` contains no revision.
- The database has no `alembic_version` table.
- Schema changes can only be applied by hand, per environment, with no record and no rollback.

## Expected Behavior
Every schema change is an Alembic revision, reviewed in a PR and applied with `alembic upgrade head`. Every database reports its revision with `alembic current`.

## Technical Analysis
- `alembic/env.py:8-13` imports the settings and every model module, and sets `sqlalchemy.url` from `DATABASE_URL`: autogenerate is ready to use.
- `app/models/__init__.py` is empty, so model registration depends on manual imports in each script. A missing import produced an empty schema without any error before PR #35.
- Autogenerate does not handle existing PostgreSQL ENUM types well (`invoicestatus`, `leavestatus`, `leavetype`). The baseline must be reviewed by hand.

## Root Cause
The schema was bootstrapped with `create_all()` during the JSON → PostgreSQL migration, without an initial revision.

## Impact
No safe way to deliver the constraint, index, role and model fixes from the audit. Environments may already differ, and there is no way to tell.

## Proposed Solution
1. `alembic revision --autogenerate -m "baseline schema"`, then review it: ENUMs, indexes, constraint names.
2. On every existing database, `alembic stamp head` after checking that its schema matches. **Never** upgrade an existing database with the baseline.
3. Import all models in `app/models/__init__.py`, and import that package from `alembic/env.py` and `tables.py`.
4. Restrict `tables.py` to throw-away environments, or replace it with `alembic upgrade head` in the setup docs.
5. Run migrations with an owner role, not with the application role (see TICKET-DB-004).

## Acceptance Criteria
- [ ] `alembic/versions/` contains a reviewed baseline revision.
- [ ] `alembic current` shows the baseline on every existing database.
- [ ] `alembic check` reports no difference between the models and a database.
- [ ] A fresh database created with `alembic upgrade head` has the same tables, columns, constraints and indexes as the current local one.
- [ ] Setup documentation uses `alembic upgrade head` instead of `python tables.py`.

## Evidence
- Catalog query on 2026-10-02: no `alembic_version` table in `public`. Only the 6 sequences of the integer primary keys exist besides the 9 tables.
- `alembic/versions/` is empty in `develop` @ `34453a4`.

## Related Findings
AUDIT-DB-015

## Dependencies
None. **Do this first.**

## Estimated Complexity
S
