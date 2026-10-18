<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-010. -->

# TICKET-DB-008 — Invoice creation: admin only, initial status set, no duplicate on retry

## Context
`POST /api/invoices` is served by `app/routers/invoicing.py`. An older admin-only version in `main.py:393-423` is shadowed, because the router is registered first (`main.py:40`).

## Problem
1. The router allows `rh`, `admin` **and `accountant`**. The accountant can create the invoices she is meant to review, which breaks separation of duties.
2. `statut` is never set and stays NULL (nullable column, no default).
3. `InvoiceOut.statut` is required, so serialising the response fails **after** the commit. The invoice is saved, the client receives a 500, and a retry creates a **second invoice with a new legal number**.

## Current Behavior
Two attempts with the accountant's token returned **500** twice. The database then contained `FA-2026-0001` and `FA-2026-0002`, both with `statut = NULL` and `cree_par_id` = the accountant. Server log: `ResponseValidationError … ('response', 'statut') … input: None`.

## Expected Behavior
Only `admin` creates invoices. A new invoice starts as `BROUILLON`. One request creates at most one invoice, even when retried.

## Technical Analysis
- `invoicing.py:14` holds the router-wide role list; `:55-82` is the handler; `app/schemas/invoicing.py:54` makes the status required.
- **Positive:** totals are recomputed server-side, and header plus lines are saved in a single commit.

## Root Cause
Two competing implementations of the same route with different rules, the looser one winning by registration order. No initial status was ever defined.

## Impact
Duplicate invoices, each with its own legal number. In accounting, an issued invoice cannot be deleted, so every duplicate requires a credit note. No usable status.

## Proposed Solution
1. `require_roles("admin")` on `POST /invoices`, keeping read access for `accountant`.
2. `statut=InvoiceStatus.BROUILLON` in the constructor, plus `NOT NULL DEFAULT 'BROUILLON'` (in TICKET-DB-007).
3. Validate and build the response before committing, so that no serialisation error can follow a commit.
4. Optional, recommended: accept an `Idempotency-Key` header and store it with the invoice, `UNIQUE`.
5. Delete `main.py:393-423`.
6. Decide what to do with the 2 `AUDIT-TEST` invoices left by the audit.

## Acceptance Criteria
- [ ] Accountant token → **403** on `POST /api/invoices`.
- [ ] Admin token → **200**, `statut = brouillon`, exactly one row.
- [ ] The same request sent twice with the same `Idempotency-Key` creates one invoice.
- [ ] Only one `POST /api/invoices` handler exists.

## Evidence
Runtime tests T-B05.1, T-B05.2 and T-B05.db (2026-10-02), with the redacted server log excerpt.

## Related Findings
AUDIT-DB-010 (HIGH)

## Dependencies
TICKET-DB-001; TICKET-DB-006 (numbering); business confirmation that invoice creation is admin-only.

## Estimated Complexity
S (M with idempotency)
