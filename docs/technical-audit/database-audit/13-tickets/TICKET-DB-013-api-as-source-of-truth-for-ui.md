<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-001, AUDIT-DB-023. À faire en dernier. -->

# TICKET-DB-013 — Make the API the source of truth for the UI (remove `localStorage` data and mock seeds)

## Context
The frontend makes exactly 5 API calls: login, create user, forgot password, reset password and invoice PDF. Everything else (invoices, leave requests, payslips, team, projects, users, notifications) is initialised from `src/data.ts` mock data, changed in React state and persisted in `localStorage`. `GET /api/data` is never called.

## Problem
- Business data is neither shared between users nor durable, and none of the server rules apply to it.
- The admin's invoices are invisible to the accountant.
- "Delete user" and "edit user" only change the browser.
- A "Switch to Admin View" button is offered to every role and loads admin screens on top of mock data. The server correctly keeps refusing admin actions.

## Current Behavior
Clearing the browser storage resets all business data to the mock seed. The PDF download only works when a mock id happens to match a `numero` in the database.

## Expected Behavior
Every view reads and writes through the API. `localStorage` keeps UI preferences only, plus the token for as long as it remains there.

## Technical Analysis
- Persistence: `src/App.tsx:74-196`.
- Local handlers: `:270-399` and `:485-493`.
- Mock data: `src/data.ts`.
- Role toggle: `Sidebar.tsx:154-159`, `App.tsx:248-267`.
- The frontend types (`src/types.ts`) do not match the API or the models: for example, `Payslip` has no employee link, and `Invoice.amount` has no VAT. They must follow the API contract decided in TICKET-DB-005.

## Root Cause
The frontend comes from a Google AI Studio prototype built on local data. The back end was added later, and the UI was never wired to it.

## Impact
The platform does not fulfil its purpose: a shared, durable and access-controlled business record.

## Proposed Solution
1. **Prerequisites:** TICKET-DB-002, 005, 006, 007 and 008. Wiring the UI to today's API would expose every proven defect at once.
2. Wire entity by entity, **invoices first** (the accountant's core need), then leave requests, payslips, users and team.
3. Derive the frontend types from the API schemas (for example by generating them from `openapi.json`).
4. Delete `src/data.ts` and every business `localStorage` key, and remove the role toggle.
5. If real data was entered in production browsers, provide a one-off export before the switch.

## Acceptance Criteria
- [ ] An invoice created by the admin is visible to the accountant from another browser.
- [ ] Clearing `localStorage` loses no business data.
- [ ] `grep -rn localStorage src` only finds the token and the theme preference.
- [ ] `src/data.ts` no longer exists.
- [ ] No role-switch control is shown to employees or to the accountant.

## Evidence
Exhaustive `fetch(` inventory of `src/` (5 calls); code references above; the database contained no business data before the audit.

## Related Findings
AUDIT-DB-001 (HIGH), AUDIT-DB-023 (LOW)

## Dependencies
TICKET-DB-002, 003, 005, 006, 007, 008; TICKET-DB-009 for the accountant screens.

## Estimated Complexity
XL
