<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-011. Recoupe #40 (entrantes/sortantes), #41 (statut de traitement), #42 (période comptable). -->

# TICKET-DB-009 — Design and implement the accountant workflow: review states, decisions, notifications, filters

## Context
The core accountant use case is to be notified of pending invoices, approve or reject them, and filter them by day, month and client. Today it is supported by **no layer**: not the data model, not the API, not the UI.

## Problem

| Need | Data model | API | UI |
|---|---|---|---|
| Approve / reject | no review state (`BROUILLON, ENVOYEE, PAYEE, EN_RETARD, ANNULEE`) | none | none |
| Who decided, when, why | none | none | none |
| Pending notifications | no table | none | role-based, `localStorage` only |
| Filters by day / month / client | columns exist, **no usable index** | no query parameters | status and text search only |
| Controlled status transitions | none | none | status picked freely at creation |
| Incoming vs outgoing | none (#40) | none | none |

`Overdue` is entered by hand, although it can be derived from the due date and the payment state.

## Current Behavior
The accountant cannot perform her job in the platform. Approvals happen outside it, with no trace.

## Expected Behavior
- An admin submits an invoice; the accountant is notified, filters, and approves or rejects with a comment.
- Every decision is stored with its author and time.
- A rejected invoice can be corrected and resubmitted, and the history is kept.

## Technical Analysis
Query plans with sequential scans disabled still return `Seq Scan` for `ORDER BY date_emission`, `WHERE client_id = ?` and the month range: there is no usable index. The model has no place to store a decision.

## Root Cause
The invoice model was designed for issuing, not for review.

## Impact
The platform's main accounting purpose is unmet, and separation of duties cannot be demonstrated.

## Proposed Solution
**Step 0, with the business:** freeze the states, transitions and roles. Proposal:
`BROUILLON → SOUMISE → APPROUVEE | REJETEE → ENVOYEE → PAYEE`, plus `ANNULEE`. A rejected invoice returns to `BROUILLON`. Separation of duties: the reviewer is never the creator.

Then:
1. Extend the status ENUM, or move to a status reference table.
2. `invoice_reviews(id, invoice_id FK, reviewer_id FK, decision, comment, decided_at)`.
3. `notifications(id, user_id FK, type, ref_type, ref_id, created_at, read_at)`, written on submit.
4. Endpoints:
   - `GET /api/invoices?status=&from=&to=&client_id=&page=&size=`;
   - `POST /api/invoices/{id}/submit` (admin);
   - `POST /api/invoices/{id}/approve` and `/reject` (accountant, `reviewer ≠ creator`);
   - `GET /api/notifications`.
5. Indexes `(statut, date_emission)` and `(client_id, date_emission)` (see TICKET-DB-012).
6. Compute `overdue` instead of storing it.
7. Record every transition in `audit_events` (TICKET-DB-010).

## Acceptance Criteria
- [ ] States and transitions are approved by the business and documented.
- [ ] An invalid transition (for example `BROUILLON → PAYEE`) is rejected by the API.
- [ ] The accountant cannot approve an invoice she created.
- [ ] Submitting creates a notification for every accountant; reading it sets `read_at`.
- [ ] Filtering by month, by client and by status uses an index (`EXPLAIN` shows an index condition).
- [ ] Each decision is stored in `invoice_reviews` and in the audit log.

## Evidence
Catalog inventory (9 tables, no review structure); ENUM values (Q-SCH-009); index probes Q-PERF-013 to 015; business rules matrix R-FAC-02, 03, 04 and 08.

## Related Findings
AUDIT-DB-011 (HIGH)

## Dependencies
TICKET-DB-001, 005, 006, 007, 008, 010 and 012; issues #40, #41 and #42; business workshop.

## Estimated Complexity
XL
