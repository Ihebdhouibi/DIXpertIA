# Database setup

## Provisioning an environment from scratch

Run these four steps in order. They are safe to re-run.

```bash
# 1. Create the database (as a PostgreSQL superuser)
python -c "import psycopg2; from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT as A; \
c=psycopg2.connect(host='localhost',port=5432,user='postgres',password='PASS',dbname='postgres'); \
c.set_isolation_level(A); c.cursor().execute('CREATE DATABASE dixpertia')"

# 2. Create the least-privilege roles, and record the two URLs it prints in .env
python db/setup_roles.py --superuser-url postgresql://postgres:PASS@localhost:5432/dixpertia

# 3. Build the schema
alembic upgrade head

# 4. Re-run step 2 so the table-level DELETE grants apply
#    (on a fresh database the tables did not exist yet in step 2)
python db/setup_roles.py --superuser-url postgresql://postgres:PASS@localhost:5432/dixpertia \
  --app-password <the one from step 2> --owner-password <the one from step 2>

# 5. Create the first administrator
python seed_users.py --email admin@example.tn
```

## Schema changes

**Never edit the database by hand, and never use `Base.metadata.create_all()`.**
`create_all()` creates missing tables but silently ignores changes to existing
ones: add a column to a model and nothing happens. It also leaves no version
history and no way back. `tables.py`, which did exactly this, was removed in
favour of Alembic.

```bash
# After editing a model in app/models/
alembic revision --autogenerate -m "short description"
# Read the generated file in alembic/versions/ before applying it.
# Autogenerate is a draft, not an authority: it misses CHECK constraints,
# some index changes, and anything it cannot infer from the models.
alembic upgrade head      # apply
alembic downgrade -1      # roll back one revision
alembic check             # fail if the models and the database have drifted
alembic current           # show the applied revision
```

## The two connections

| Variable | Role | Can |
|---|---|---|
| `DATABASE_URL` | `dixpertia_app` | SELECT / INSERT / UPDATE, DELETE on `devices` and `services` only |
| `SCHEMA_DATABASE_URL` | `dixpertia_owner` | CREATE / ALTER - used by Alembic only |

The application role is deliberately `NOSUPERUSER NOBYPASSRLS`: a superuser
bypasses row-level security entirely, which would make the policies in #43
silently inert.

## Supported version

PostgreSQL **17.x**. The audit in `docs/technical-audit/` was performed against
17.11 and the baseline migration was generated against it.
