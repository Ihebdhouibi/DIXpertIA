<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-013, AUDIT-DB-019. C'est l'issue existante #37 : à publier comme commentaire ou sous-tâche de #37, pas comme doublon. -->

# TICKET-DB-005 — Unify the data model across API and ORM, rewrite legacy routes on the real models, remove dead code (implements #37)

## Context
Issue #37 asks to reconcile the split data model. The database audit measured the consequences of that split at runtime. This ticket turns the decision into concrete work, and should be attached to #37 rather than filed as a duplicate.

## Problem
The legacy API (`main.py`) and the frontend use camelCase English fields. The ORM models for leave requests, invoices and payslips use snake_case French columns. The code builds or updates objects with attributes that do not exist:

| Route / code | Defect | Runtime result |
|---|---|---|
| `POST /api/leave-requests` (`main.py:338-348`) | `LeaveRequest(employeeId=…, employeeName=…, dates=…)` | **500**: `TypeError: 'employeeId' is an invalid keyword argument for LeaveRequest` |
| `…/approve`, `…/reject` (`main.py:359`, `:368-369`) | sets `leave.status` and `leave.rejectionReason` (the columns are `statut` and `commentaire_validation`) | **200 "approved successfully", nothing written** |
| `GET/POST/PUT/DELETE /api/devices` (`main.py:429-475`) | `current_user['role']` on a `User` object | **500**: `'User' object is not subscriptable`, even for admin |
| `POST /api/invoices` (`main.py:393-423`) | `Invoice(id=str, client=…, amount=…, deviceIds=…)` | dead code, shadowed by the router |
| `migrate_data.py:40-46` | `Payslip(period=…, grossPay=…)` | crashes (documented in #35) |
| `app/schemas/user.py:5` | imports a non-existent `RoleEnum` | module cannot be imported |
| `app/routers/{auth,leaves,payroll,services}.py` | not mounted; use `User.employee_profile`, `hashed_password`, `first_name` | dead code |
| `PayslipOut.employee_id`, `LeaveRequestOut.employee_id` | typed `int` for `VARCHAR` `USR-NNN` columns | would fail once mounted |

Two JWT and auth stacks exist (`main.py:58-114` and `app/core/security.py` / `deps.py`). Only `TeamMember` has the same shape in every layer.

Smaller representation issues to settle in the same pass (from AUDIT-DB-019):
- `devices.price` is `double precision`;
- timestamps mix naive `timestamp` (from `utcnow`) and `timestamptz`, and invoice dates use the server's local `date.today()`;
- ENUMs are stored by **name** (`BROUILLON`) while the API exposes values (`brouillon`) and the UI shows `Draft`;
- 14 camelCase columns require quoting in SQL;
- `team_members.role` means *job title* while `users.role` means *permission*;
- a phantom role `rh` is accepted by `require_roles` but exists nowhere else.

## Current Behavior
Leave creation and every device route crash. Leave decisions report success without writing anything. Payslips have no working route except the over-exposed `/api/data` (removed by TICKET-DB-002).

## Expected Behavior
One vocabulary from database to API. Every route works on the real columns, with explicit Pydantic input and output schemas. A single auth stack, and no dead code.

## Technical Analysis
Full field-by-field mapping per entity: audit document `04-models/orm-api-frontend-mapping.md`, summarised above. The frontend calls none of these routes today, so they can be rewritten without UI regressions, but also without any usage-based validation. Tests are required (TICKET-DB-014).

## Root Cause
The JSON → PostgreSQL migration introduced a French snake_case schema without adapting the API that consumes it. The routers written for that schema were never mounted.

## Impact
Leave management and device management are non-functional, and leave decisions silently do nothing. A large part of the back end is dead code that looks like protection but never runs.

## Proposed Solution
1. **Decide #37.** Recommendation: snake_case in the database. Keep French domain names if the team prefers, but in one convention. Expose stable camelCase names to the frontend through Pydantic aliases if desired.
2. Rewrite the `main.py` routes as routers on the existing models (`date_debut`, `date_fin`, `type_conge`, `statut`, `valide_par_id`, `commentaire_validation`…), with per-route schemas. Set `valide_par_id` on decisions.
3. Mount the corrected `leaves` and `payroll` routers, or delete them. Decide on `employee_profile` (TICKET-DB-011).
4. Keep one auth stack (`app/core/`), and delete the copies in `main.py`.
5. Delete `main.py:393-423`, `migrate_data.py`, and `app/schemas/user.py` (or fix it).
6. In the same migration series:
   - `devices.price` → `NUMERIC(10,2)`;
   - timestamps → `timestamptz`, with an explicit business time zone (`Africa/Tunis`) for invoice dates;
   - `Enum(..., values_callable=...)` if values should be stored;
   - rename `team_members.role` → `job_title`;
   - decide whether `rh` is a real role.

## Acceptance Criteria
- [ ] #37 has a written decision.
- [ ] `POST /api/leave-requests` (authenticated) creates a row; approve and reject change `statut` and set `valide_par_id`.
- [ ] Every `/api/devices` route works for admin, and returns 403 for others.
- [ ] `python -c "import app.schemas.user"` succeeds, or the module is gone.
- [ ] Exactly one `get_current_user`, `create_access_token` and password hasher exist.
- [ ] No unmounted router remains in `app/routers/`.
- [ ] No `double precision` money column, no naive timestamp column.

## Evidence
Runtime tests T-A03, T-A05 and T-B09, with root causes confirmed in the server log (2026-10-02). Catalog queries Q-SCH-002, Q-SCH-009, Q-SCH-010 and Q-SCH-011.

## Related Findings
AUDIT-DB-013 (HIGH), AUDIT-DB-019 (LOW)

## Dependencies
TICKET-DB-001. **TICKET-DB-002 must ship first, or together:** fixing the leave attribute names would otherwise make anonymous approvals effective.

## Estimated Complexity
L
