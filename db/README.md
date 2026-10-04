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

## Row-level security

Policies are applied by the `2f4f3ed01359` migration to `payslips`,
`leave_requests`, `invoices`, `invoice_items`, `clients`, `team_members` and
`devices`. Verify them at any time with:

```bash
python db/verify_rls.py
```

### How identity reaches the database

`require_authentication` in `main.py` reads `sub` and `role` from the JWT and
publishes them through `app/core/identity.py`. An `after_begin` listener in
`app/core/database.py` then issues `set_config('app.user_id', ..., true)` on
every transaction the session opens, and the policies read it with
`current_setting`.

Three details that are easy to get wrong:

- **`require_authentication` must stay `async`.** As a sync dependency FastAPI
  runs it in a worker thread, where `ContextVar.set()` mutates that worker's
  copy of the context and the endpoint never sees it. Every insert was rejected
  by the policies until this was changed.
- **The identity is re-applied on every `begin`, not once per request.**
  `SET LOCAL` dies with its transaction, so a handler that calls `commit()` and
  then `refresh()` would otherwise run the refresh with no identity and, under
  RLS, see nothing.
- **`current_setting(..., true)` returns `''`, not `NULL`, once a
  transaction-local value has been set and the transaction has ended.** Policies
  therefore wrap it in `nullif(..., '')`; a policy testing `IS NULL` alone would
  not detect "no identity".

### Who bypasses

`dixpertia_owner` has a permissive `FOR ALL` policy on every protected table, so
migrations and maintenance scripts keep working under `FORCE ROW LEVEL
SECURITY`. It is scoped to that role by name rather than to a settable flag: a
GUC-based escape hatch could be flipped by `dixpertia_app` itself.

### `users` is not covered

Login, forgot-password and reset-password all read `users` with no authenticated
identity, so a policy there would break authentication outright. Covering it
needs `SECURITY DEFINER` lookup functions owned by a `BYPASSRLS` role, exposing
only the columns the auth path needs. Tracked separately.

## Business integrity constraints

The database enforces every single-row business rule. Verify at any time:

```bash
python db/verify_constraints.py
```

It attempts invalid writes inside a transaction that is always rolled back, so
it never modifies data. The audit's original run attempted 30 invalid writes
and **26 were accepted**, because the schema held zero CHECK constraints.

Rules now enforced:

| Table | Rule |
|---|---|
| `invoices` | amounts non-negative, TTC >= HT, due date >= issue date, author and amounts NOT NULL |
| `invoice_items` | quantity > 0, unit price >= 0, VAT between 0 and 100 |
| `leave_requests` | end >= start, no self-validation, a decided request names its validator, employee NOT NULL |
| `payslips` | net <= gross, both non-negative, `periode` pinned to the 1st so `uq_employee_periode` means one per month |
| `users` | role in (admin, employee, accountant), role and password hash NOT NULL, email unique case-insensitively |
| `devices` | price >= 0, serial number unique where present |
| `clients` | name unique case-insensitively |

The same rules are mirrored in the Pydantic input schemas, so the API answers
422 naming the field rather than letting the database raise and returning 500.
The database is the backstop, not the only check: `migrate_data.py` and
`insert_invoices.py` write directly and bypass the API entirely.

### Two rules deliberately not enforced here

Neither is a single-row rule, so neither can be a CHECK:

- **Overlapping leave requests** for one employee - needs an `EXCLUDE`
  constraint with `btree_gist`, or an application-level check.
- **Invoice header totals matching the sum of its lines** - needs a trigger, a
  generated column, or recomputation at issue time. The handler already
  computes totals server-side, so the header cannot disagree via the API; a
  direct write still could.

## Employees

An `employees` record is distinct from the `users` login account (#60). Payroll
and leave hang off the employee, so a login can be deactivated without taking
the payroll history with it.

```
users (login)  1 --- 0..1  employees  1 --- *  payslips
                                      1 --- *  leave_requests
```

`team_members` is gone. It duplicated names, e-mail and a free-text role from
`users` with no foreign key, so the two tables could describe the same person
differently.

### Leave balance is derived, never stored

Balance = `annual_entitlement_days` minus approved leave in the current
calendar year. **No carry-over** - the balance resets annually. A stored column
would drift out of step with the leave table the moment a request was approved,
and nothing would record why.

`annual_entitlement_days` has no default on purpose: it is a per-person
contractual term, and a company-wide guess would bake an invented figure into
every record.

### Delete behaviour

Every foreign key states its `ON DELETE` explicitly; none are left implicit.

| From | To | On delete | Why |
|---|---|---|---|
| `employees` | `users` | RESTRICT | a login owning payroll history must not vanish |
| `payslips` | `employees` | RESTRICT | payroll history outlives the person record |
| `leave_requests` | `employees` | RESTRICT | same |
| `leave_requests.valide_par_id` | `users` | RESTRICT | who approved must remain answerable |
| `invoices` | `clients` | RESTRICT | a client with invoices is not deletable |
| `invoices.cree_par_id` | `users` | RESTRICT | authorship of an issued invoice survives |
| `invoice_items` | `invoices` | CASCADE | lines belong to their invoice |

The `invoice_items` cascade previously existed in the ORM only, so an ORM
delete removed the lines while a direct SQL delete was refused - the same
operation with two different outcomes depending on the code path.

### Self-validation is enforced by a trigger

An employee must not approve their own leave. This was a CHECK comparing
`valide_par_id` to `employee_id`, which stopped being meaningful once they
referenced different tables. `trg_leave_no_self_validation` resolves the
employee's `user_id` and rejects the match.

## Indexes

Every index is justified by a measured query plan rather than by convention.
The procedure is reproducible on any environment:

```bash
# Fill the tables; --scale multiplies the volumes
python db/seed_perf_data.py --scale 10

# Print the plan the planner chooses for each access path
python db/measure_indexes.py

# Remove the fixtures again
python db/seed_perf_data.py --clear
```

`measure_indexes.py` flags any path still falling back to a sequential scan.
One is expected and deliberate: filtering `leave_requests` by `statut` has only
three distinct values, so an index saves about 7% and is not worth the write
cost. Everything else uses an index.

Measuring matters because an empty database cannot answer the question. With no
rows, PostgreSQL scans sequentially whatever indexes exist, because reading
nothing is cheaper than consulting an index -- so on an empty database every
index looks equally useless, and every plan looks the same.

### What a measurement changed

Three decisions came out differently than they would have by convention:

- `ix_users_email` looks redundant beside `ux_users_email_ci`, but is not. That
  index covers `lower(email)` and cannot serve `WHERE email = ?`. Dropping it
  turned login into a sequential scan, so it was kept.
- `payslips.employee_id` has no index of its own and needs none:
  `uq_employee_periode` is `(employee_id, periode)`, and a btree already serves
  lookups on its leading column.
- The invoice list index is ascending although the list reads newest first.
  PostgreSQL scans a btree backward at the same cost, so one ascending index
  serves both that and the accountant's ascending month range.

### Indexes that serve no query

`invoices.cree_par_id` and `leave_requests.valide_par_id` are indexed although
nothing selects on them. Both are `ON DELETE RESTRICT`, so deleting a user
makes PostgreSQL search the child table to check for references. Proving that
*no* row references the user means reading the whole table -- 1.7 ms against
20k invoices, while holding locks. With the index it is 0.045 ms.

### Redundant indexes

A primary key and a `UNIQUE` constraint each create an index already. The
models originally declared `index=True` on every primary key as well, which
produced a second, identical index on eight tables -- paid for on every insert
and update, and never chosen by the planner. Do not add `index=True` to a
primary key or to a column that already carries `unique=True`.

## Pagination

List endpoints take `limit` (default 50, maximum 200) and `offset`, and report
the unpaginated total in the `X-Total-Count` header. The cap is enforced by the
API, not left to the caller.

Ordering always ends in a unique tie-break, normally `id`. Without one, rows
that share a sort value have no defined order between queries, and a client
paging through the list sees some rows twice and never sees others. Walking 40
pages of the seeded invoices ordered by `date_emission` alone returned 123
duplicated rows out of 1000; adding `id` returned zero.
