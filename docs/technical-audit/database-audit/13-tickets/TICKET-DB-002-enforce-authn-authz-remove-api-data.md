<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-002 (CRITICAL), AUDIT-DB-003, AUDIT-DB-020. Priorité : phase 0. -->

# TICKET-DB-002 — Require authentication on every route, enforce role checks, and remove `GET /api/data`

## Context
Authentication is declared route by route in `main.py`. Four write routes have none at all, and `GET /api/data` returns every table to any logged-in user. The `invoicing` router, on the other hand, enforces its roles correctly (403 for an employee).

## Problem
1. **Anonymous writes**, verified at runtime:
   - `POST /api/team-members` creates a row with no token;
   - `POST /api/leave-requests/{id}/approve` and `/reject` run with no token;
   - `POST /api/leave-requests` takes `employeeId` from the request body.
2. **Over-exposure:** `GET /api/data` returns all users, all invoices, all leave requests (including sick leave and its reason), all devices and all team members to **any** role. The 403 on `/api/invoices` for employees is therefore bypassed.
3. Output is built from `obj.__dict__` minus a deny-list, so any new sensitive column is exposed by default.

## Current Behavior

| Request | Result |
|---|---|
| `POST /api/team-members`, no token | **201**, row created |
| `POST /api/leave-requests/{id}/approve`, no token, existing id | **200** "approved successfully" |
| `POST /api/leave-requests/999999/approve`, no token | **404**: the handler ran without authentication |
| `POST /api/leave-requests`, no token | **500** (no auth, then a crash, see TICKET-DB-005) |
| `GET /api/data` with an **employee** token | **200** with all 7 user accounts |
| `GET /api/data` (employee-level token) | response includes invoices `FA-2026-0001` and `FA-2026-0002` |

## Expected Behavior
- Every route requires a valid token, except an explicit public allow-list: `/api/login`, `/api/forgot-password`, `/api/reset-password`.
- Leave decisions and team member creation require `admin`.
- A leave request is always created for `current_user`.
- No endpoint returns data outside the caller's rights. Every response uses an explicit Pydantic `response_model`.

## Technical Analysis
- The unauthenticated handlers are in `main.py:335-391`.
- `get_data` is in `main.py:492-518`; `_row()` and `_PRIVATE_COLUMNS` are in `main.py:116-129`.
- The frontend **never calls** any of these routes: its 5 API calls are login, user creation, forgot password, reset password and invoice PDF. Locking them down has no visible regression.
- **Ordering constraint:** the leave decision routes currently write to non-existent attributes (`leave.status` instead of `statut`), so the anonymous approval writes nothing **today**. Fixing those attribute names (TICKET-DB-005) **before** this ticket would make anonymous approval effective. Ship this ticket first, or both together.

## Root Cause
Opt-in authentication per route, no automated test enumerating routes, and a legacy "load everything" endpoint kept from the JSON storage era.

## Impact
Anyone who can reach the API can write staff data. Any employee can read the company's invoices and every colleague's leave history. The access rules from #10, #12 and #47 are enforced in the UI only.

## Proposed Solution
1. Move the `main.py` routes into routers declared with `dependencies=[Depends(get_current_user)]`, and keep a short explicit list of public routes.
2. Add `require_roles("admin")` to the leave decision and team member routes. Derive `employee_id` from `current_user`.
3. Delete `GET /api/data` and `_row()`. Add per-entity read endpoints with explicit response models as the UI needs them (TICKET-DB-013).
4. Add a test that iterates over `app.routes` and fails for any non-public route without an authentication dependency.

## Acceptance Criteria
- [ ] Every route in `main.py:335-391` returns **401** without a token.
- [ ] Leave decisions and team member creation return **403** for `employee` and `accountant`.
- [ ] `POST /api/leave-requests` ignores any `employeeId` in the body.
- [ ] `GET /api/data` no longer exists.
- [ ] No endpoint serialises `obj.__dict__`; every read endpoint declares a `response_model`.
- [ ] An automated test fails if a new non-public route has no authentication dependency.

## Evidence
Runtime tests T-A01, T-A02, T-A03, T-B01, T-B07, T-B08 and T-B09, run against `develop` @ `34453a4` on 2026-10-02. Example (T-B09): an anonymous `POST /api/leave-requests/7/approve` returned 200 with "Leave request approved successfully", while the row stayed `EN_ATTENTE` in the database.

## Related Findings
AUDIT-DB-002 (CRITICAL), AUDIT-DB-003 (HIGH), AUDIT-DB-020 (LOW)

## Dependencies
None. **Must not be preceded by** the leave attribute fix in TICKET-DB-005.

## Estimated Complexity
M
