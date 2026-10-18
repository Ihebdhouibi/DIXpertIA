<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-018. -->

# TICKET-DB-012 — Indexes for real access paths, drop redundant indexes, paginate lists, fix the N+1

## Context
The tables are almost empty, so nothing is slow yet. But the structure cannot serve the planned accounting queries efficiently, and every table carries a redundant index.

## Problem
- **5 of 6 foreign keys have no index:** `invoices.client_id`, `invoices.cree_par_id`, `invoice_items.invoice_id`, `leave_requests.employee_id`, `leave_requests.valide_par_id`.
- **No usable index**, even with sequential scans disabled, for: invoices ordered by `date_emission`, invoices of a client, invoices of a month, the lines of an invoice.
- **9 redundant indexes** `ix_<table>_id` duplicate each primary key (`primary_key=True, index=True` in every model). The planner even picks `ix_users_id` over `users_pkey`.
- `numero LIKE 'FA-YYYY-%'` scans the whole unique index: the collation `French_Tunisia.1252` is non-C.
- `GET /api/invoices` lazy-loads `items` per invoice (1 + N queries).
- No list endpoint is paginated or filtered.

## Current Behavior
Plans with sequential scans disabled still show `Seq Scan` at a cost of about 10¹⁰ for the queries above.

## Expected Behavior
Every frequent access path uses an index. Lists are paginated and filtered in the database. Invoice listing uses a constant number of queries.

## Technical Analysis
Audit documents `07-performance/explain-plans-analysis.md` and `performance-static-analysis.md`.

## Root Cause
Indexes were declared by default on primary keys instead of being derived from the real queries. PostgreSQL never indexes foreign keys automatically.

## Impact
None today. Accounting screens (by month, by client, pending) will slow down as history grows, and the redundant indexes double the primary key write cost.

## Proposed Solution
```sql
DROP INDEX ix_users_id, ix_clients_id, ix_devices_id, ix_invoice_items_id, ix_invoices_id,
           ix_leave_requests_id, ix_payslips_id, ix_services_id, ix_team_members_id;
CREATE INDEX ix_invoices_client_date  ON invoices (client_id, date_emission DESC);
CREATE INDEX ix_invoices_status_date  ON invoices (statut, date_emission DESC);
CREATE INDEX ix_invoices_date         ON invoices (date_emission DESC);
CREATE INDEX ix_invoice_items_invoice ON invoice_items (invoice_id);
CREATE INDEX ix_leave_employee        ON leave_requests (employee_id, date_debut);
CREATE INDEX ix_invoices_creator      ON invoices (cree_par_id);
CREATE INDEX ix_leave_validator       ON leave_requests (valide_par_id);
```
- Remove `index=True` from every primary key in the models, **in the same revision**: otherwise autogenerate recreates the indexes.
- `selectinload(Invoice.items)` in the list query.
- `limit` / `offset` (with a cap) and filter parameters on list endpoints.
- Invoice numbering moves to a counter table (TICKET-DB-006), which removes the `LIKE`.

## Acceptance Criteria
- [ ] The catalog shows no two indexes on the same columns.
- [ ] Every foreign key column is the leading column of an index.
- [ ] With sequential scans disabled, the month, client and status filters show an `Index Cond`.
- [ ] `GET /api/invoices` issues 2 queries regardless of the number of invoices.
- [ ] Every list endpoint accepts pagination, with a maximum page size.

## Evidence
Catalog queries Q-SCH-005 to Q-SCH-007; plans Q-PERF-004 and Q-PERF-013 to 017 (2026-10-02).

## Related Findings
AUDIT-DB-018 (LOW, rising to MEDIUM once TICKET-DB-009 is built)

## Dependencies
TICKET-DB-001. Should land **before** TICKET-DB-009.

## Estimated Complexity
S
