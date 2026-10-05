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

## Invoice status: two axes, not one

Invoices carry two independent status columns, and conflating them loses
information the accountant needs (#41).

| Column | Describes | Moves because |
|---|---|---|
| `statut` | the commercial state the client sees | the client relationship: issued, paid, overdue |
| `processing_status` | the accountant's workflow state | the monthly close: booked, reconciled, archived |

An invoice is routinely `PAYEE` and `pending` at the same time: the client has
paid, but nobody has entered it in the books yet. The reverse happens too. A
single enum could not express either, and "paid but not yet booked" is the
normal state of most invoices mid-month.

### What each processing state means

| State | Meaning |
|---|---|
| `pending` | It exists, nobody has handled it. The state on creation. |
| `processed` | Entered in the books. |
| `completed` | Booked **and** matched against an actual payment. |
| `archived` | The month it belongs to has been closed. |

`processed` and `completed` are deliberately distinct. Booking an invoice and
reconciling it against a bank line are separate acts, often days apart, and the
gap between them is what the accountant chases at month end.

### Archived is final, and the database enforces it

Once an invoice is archived, the trigger `invoice_archived_is_final` refuses:

- any change to `processing_status` -- it cannot move back
- any change to `numero`, `client_id`, `date_emission`, `date_echeance`,
  `montant_ht` or `montant_ttc`
- deletion of the row

A mistake found after the close is corrected by issuing a new document in the
open month, never by editing a closed one. That is what makes a closed month's
totals final, and it is the assumption the gapless-numbering rule in #38 is
built on.

`statut` is deliberately **not** frozen. A client can pay in November an invoice
archived with October's books, and the commercial state must still record it.
Needing exactly that is why the two axes are separate columns.

The rule lives in a trigger rather than in the API so that it holds for a direct
SQL write too. `db/verify_constraints.py` probes all six refusals, plus two
writes that must still be **accepted**: marking an archived invoice paid, and
moving an open invoice forward.

### Transitions are not otherwise constrained

Before archiving, an invoice moves freely between `pending`, `processed` and
`completed`, so the accountant can correct their own work while the month is
still open. Only the step into `archived` is one-way. If the accountant later
wants a stricter forward-only progression, it belongs in the same trigger.

The close itself -- which invoices get archived and when -- is owned separately
and is not implemented here.


## Invoice numbering is gapless

The accountant requires invoice numbers to start at 1 and increase by exactly 1,
with no gaps and no duplicates (#38). The series **restarts each year**, keeping
the `FA-YYYY-NNNN` format: `FA-2026-0001` follows `FA-2025-0184`.

### Why a counter table and not a sequence

A PostgreSQL sequence is deliberately **not** gapless. It does not roll back
when a transaction fails, precisely so concurrent writers never block each
other. An invoice number is a legal artefact, so the opposite trade-off is the
one wanted here.

`invoice_sequences` holds one row per year, and allocation happens inside the
transaction that creates the invoice:

```sql
UPDATE invoice_sequences SET last_number = last_number + 1
WHERE year = :year RETURNING last_number
```

That row lock is held until commit, which buys both properties:

- two concurrent creates **serialise**, so neither can take the same number
- a failed create **rolls the counter back with it**, so no number is burned

Invoice creation therefore serialises on one row per year. That is a deliberate
choice: a gapless counter and high write concurrency are fundamentally in
tension, and this company issues a few invoices a day. If volume ever makes the
lock hurt, the answer is to allocate at *issue* time rather than at draft
creation, not to drop the lock.

### What this replaced

The number came from `COUNT(*) + 1`, which broke three ways:

| | |
|---|---|
| Deleting an invoice | the next create computed a number that already existed, hit `invoices_numero_key` and returned 500 — and kept failing until someone worked out why |
| Two concurrent creates | both read the same count, both computed the same number, one failed |
| A failed transaction | left a hole nobody detected |

Measured after the change: 8 concurrent creates produced 8 distinct numbers with
zero failures.

### An invoice is never deleted

`invoice_is_never_deleted` refuses **every** delete, not only the archived ones
#41 protects. Deleting any invoice leaves a hole in the series, which is the
thing the accountant asked to be impossible.

An invoice issued in error is **cancelled**, keeping its row and its number with
`statut = ANNULEE`, and corrected by a credit note. That is the standard
accounting answer and the same shape as the correction rule for a closed month.

### The series is enforced, not just generated

`invoice_number_is_sequential` refuses an inserted number that is not exactly
one more than the highest already issued for its year, so a direct SQL write
cannot quietly break the series either.

**Scope, stated honestly:** the rule applies only to numbers matching
`FA-YYYY-NNNN`. That is the legal series; a fixture using another prefix (the
seeder uses `PERF-`) is outside it. The API never lets a caller choose a number —
it is generated server-side — so the only writer this governs is a direct SQL
insert, where the operator is already the database owner.

### Finding a gap

With no deletes and a transactional counter, a gap cannot occur. To check
anyway:

```sql
SELECT year, expected
FROM (
    SELECT substring(numero from 4 for 4)::int AS year,
           generate_series(1, max(substring(numero from 9)::int)) AS expected
    FROM invoices
    WHERE numero ~ '^FA-[0-9]{4}-[0-9]+$'
    GROUP BY 1
) s
WHERE NOT EXISTS (
    SELECT 1 FROM invoices
    WHERE numero = 'FA-' || s.year || '-' || lpad(s.expected::text, 4, '0')
);
```

An empty result means the series is intact.


## The monthly accounting period

The accountant works the books a month at a time. `accounting_periods` holds one
row per month (#42).

A table, not a month derived from `date_emission`, because closing is an **event**
rather than a property of the invoices: it has an actor, a moment and a result.
Deriving the month would record none of those, so nobody could answer "who closed
January, and when".

| Column | Meaning |
|---|---|
| `periode` | a `DATE` standing for the month, pinned to the 1st (same convention as `payslips.periode`) |
| `state` | `OPEN` or `CLOSED` |
| `closed_at`, `closed_by_id` | who closed it and when; null while open |
| `invoice_count`, `total_ht`, `total_ttc` | what the close counted, recorded as it ran |

`ck_period_close_is_complete` keeps those consistent: an open period carries no
close details, and a closed one carries all of them. A row can never claim to be
closed by nobody.

The totals are worth keeping because the invoices are frozen afterwards, so a
recount at any later date should still match. A mismatch means something
bypassed the rules.

### Closing refuses while the books are unfinished

`POST /api/periods/{YYYY-MM}/close` returns **409 with the list of invoices
blocking it** if any invoice in the month is not `completed`.

That is the decided rule rather than a convenience. Archived is terminal (#41),
so closing over unfinished work would freeze invoices nobody had booked, and
they could never be booked afterwards. Refusing gives the accountant a worklist
instead of a silent outcome.

`GET /api/periods/{YYYY-MM}` previews the same figures and the same blocking
list without closing anything, because the close cannot be undone.

### A closed month admits no further invoices

This is the rule that gives the close its meaning. The trigger
`invoice_period_is_open` refuses any invoice inserted into, or moved into, a
closed month.

Without it, closing would change nothing: an invoice dated into January could
still appear after January had been reported as final, and the totals recorded
on the period row would quietly stop matching the invoices they counted.

It is a trigger rather than an API check because `migrate_data.py` and
`insert_invoices.py` write to this database directly.

### There is no reopen, and that is a decision

A closed month stays closed. Its figures never change afterwards, which is what
makes them reportable. A mistake found later is corrected by issuing a new
document in the open month, referencing the original -- never by editing a
closed one.

A reopen could not do what it appears to do anyway: the #41 trigger refuses to
un-archive an invoice, so a reopened period would be able to gain new invoices
while its existing ones stayed frozen, and its recorded totals would be wrong
either way.

If the accountant turns out to need an escape hatch, it belongs here with an
audit record, not as a column someone edits by hand. Watch for anyone asking to
"just fix it in the database" -- that is the signal.

### Who may close

Admin and accountant. `rh` is excluded, exactly as it is for an invoice's
processing status: this is bookkeeping, not a commercial act. Enforced by the
router dependency and again by the `accounting_periods_write` policy, so a
direct connection as the application role cannot bypass it.

Every signed-in role may **read** the periods -- an employee filing an expense
has a legitimate reason to know which months are open. With no identity at all,
the table reads as empty.


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
