<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-017. -->

# TICKET-DB-010 — Add an audit trail for sensitive actions

## Context
Nothing records who did what. There are no audit tables and no `updated_by` columns. `leave_requests.valide_par_id` exists but is never set by live code, and PostgreSQL logs neither connections nor statements.

## Problem
Approvals, invoice creation and changes, role changes, deactivations and password resets cannot be attributed or reconstructed.

## Current Behavior
- An anonymous leave approval returned 200 and left no trace of any kind.
- The settings `log_connections`, `log_disconnections` and `log_statement` are all off.

## Expected Behavior
Every sensitive action produces an append-only audit event with actor, time, entity, and before/after values.

## Technical Analysis
No table matches `audit_*` or `*_history`, and no column `updated_at` or `updated_by` exists. The application logger has no handler.

## Root Cause
Traceability was never specified as a requirement.

## Impact
Abuse enabled by other findings (anonymous writes, retained access after "deletion") can be neither detected nor investigated. Internal control over payroll and accounting cannot be demonstrated.

## Proposed Solution
1. `audit_events(id bigserial, occurred_at timestamptz default now(), actor_id FK users, action text, entity text, entity_id text, before jsonb, after jsonb)`.
2. A single service `record_event(...)`, called from:
   - invoice create, submit, approve, reject, issue and cancel;
   - leave decisions;
   - user create, update, deactivate and role change;
   - password reset and activation.
3. Grant only `INSERT` and `SELECT` on `audit_events` to the application role: no `UPDATE`, no `DELETE`.
4. Add `created_at` / `created_by` / `updated_at` / `updated_by` to business tables.
5. Enable `log_connections` on shared servers.
6. Define the retention period and who may read the log.

## Acceptance Criteria
- [ ] Every listed action writes exactly one audit event.
- [ ] The application role cannot update or delete audit events.
- [ ] An admin-only endpoint lists events with filters (actor, entity, date).
- [ ] The retention period is documented.

## Evidence
Catalog inventory of 2026-10-02 (no audit structure); server settings (Q-SEC-006); runtime test T-B09.

## Related Findings
AUDIT-DB-017 (MEDIUM)

## Dependencies
TICKET-DB-001, TICKET-DB-004 (privileges of the application role).

## Estimated Complexity
M
