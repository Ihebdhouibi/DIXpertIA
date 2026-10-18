<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-016. -->

# TICKET-DB-011 — Complete the data model: employee entity, device ↔ invoice link, explicit `ON DELETE`, ORM relationships

## Context
The schema has 9 tables and 6 foreign keys. Three tables (`team_members`, `devices`, `services`) are isolated. Several relationships the business needs do not exist.

## Problem
1. **No employee entity distinct from the login account.** The unmounted routers rely on `User.employee_profile`, and `EmployeeOut` (job title, hire date, leave balance), but no such table exists. Payroll and leave hang off the login account, and the leave balance is stored nowhere.
2. **`team_members` duplicates `users`** (names, e-mail, "role") with no foreign key.
3. **No device ↔ invoice link,** although #18 ("device management linked to invoices") is closed. The "Sold" status lives in dead code.
4. **Nullable mandatory foreign keys:** `leave_requests.employee_id`, and `invoices.cree_par_id` (nullable on purpose, `app/models/invoicing.py:45`).
5. **All 6 foreign keys are implicit `NO ACTION`.** The `Invoice.items` cascade exists in the ORM only: a direct SQL delete is refused, while an ORM delete removes the lines.
6. **No `relationship()`** for the 4 foreign keys to `users`, and no back-references on `User`.

## Current Behavior
The constraint probe accepted an invoice without an author and a leave request without an employee. It rejected a direct SQL delete of an invoice that has lines (FK `NO ACTION`).

## Expected Behavior
- Each business concept is represented once.
- Mandatory relationships are `NOT NULL`.
- Each foreign key has a deliberately chosen delete behaviour, identical in the ORM and in the database.

## Technical Analysis
Logical ERD, per-relationship analysis and the list of missing relationships (M1 to M6): audit document `05-relations/relations-and-erd.md`.

## Root Cause
The model was derived from the original JSON collections, each autonomous. The planned employee model was never implemented.

## Impact
Device sales cannot be traced. Payroll history is tied to the login account, which must eventually be deactivated. A person's identity can diverge between two tables.

## Proposed Solution
**Business decisions required first:** a separate employee entity, the leave balance rules, and whether a device can be sold more than once.
1. `employees(id, user_id UNIQUE FK, job_title, hired_on, leave_balance, employment_status)`. Re-attach `payslips` and `leave_requests` to `employees`, and fold `team_members` into it (or link it by foreign key).
2. `devices.invoice_id FK NULL UNIQUE` if a device is sold once; otherwise an `invoice_devices` junction table with `UNIQUE(device_id)`.
3. `NOT NULL` on `leave_requests.employee_id` and `invoices.cree_par_id` (with TICKET-DB-007).
4. Explicit `ondelete`:
   - `RESTRICT` towards people and clients;
   - `CASCADE` for `invoice_items → invoices`, mirrored in the database.

   Prefer soft deletion (`archived_at`) for business entities.
5. Add `relationship()` and back-references for the foreign keys to `users` / `employees`.

## Acceptance Criteria
- [ ] Every foreign key has an explicit `ON DELETE` (catalog check) that matches the ORM cascade settings.
- [ ] An invoice without an author and a leave request without an employee are rejected.
- [ ] Selling an already-sold device is rejected.
- [ ] Payslips and leave requests reference an employee record; deactivating a user keeps its history intact.
- [ ] No duplicate person data remains between `team_members` and `users` / `employees`.

## Evidence
Catalog queries Q-SCH-003 and Q-SCH-004 (6 FKs, all `NO ACTION`); constraint probe P-06, P-12 and P-28; code references above.

## Related Findings
AUDIT-DB-016 (MEDIUM)

## Dependencies
TICKET-DB-001, TICKET-DB-005 (decision on #37), business decisions.

## Estimated Complexity
L
