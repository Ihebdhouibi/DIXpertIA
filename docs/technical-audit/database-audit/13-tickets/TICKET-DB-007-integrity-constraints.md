<!-- Brouillon destiné à GitHub (en anglais). Non encore publié. Findings : AUDIT-DB-014 ; partie NOT NULL d'AUDIT-DB-016. -->

# TICKET-DB-007 — Add database integrity constraints for every single-row business rule

## Context
The database enforces primary keys, 6 foreign keys and 3 unique constraints, and **nothing else**: there are 0 CHECK constraints. Several mandatory columns are nullable, and defaults exist on the Python side only. The API does not validate these rules either (for example, `prix_unitaire` accepts negative values).

## Problem
A probe ran 30 invalid writes inside a transaction that was always rolled back. **26 were accepted.** The 4 rejections were exactly the 4 constraints that exist.

| Area | Accepted examples |
|---|---|
| Invoices | amount −500; due date before issue date; TTC < HT; no status; no amount; no author; header inconsistent with its lines |
| Invoice lines | quantity −4; VAT 99.99 %; VAT −19 %; unit price −10 |
| Leave requests | no employee; end before start; self-validation; approved without a validator; overlapping requests |
| Payslips | net > gross; negative amounts; **two payslips in the same month** (unique constraint is on a date, not a month) |
| Users | role `superadmin`; no role and no password hash; `PROBE@x` next to `probe@x`; `isActive` NULL when omitted |
| Devices and clients | duplicate serial number; price −99.99 and status "Volé"; case-variant duplicate client names |

## Current Behavior
Invalid financial and payroll data is stored silently, and can then be rendered to PDF and sent.

## Expected Behavior
The database rejects every row that violates a single-row business rule. The API validates the same rules first, to return clear 422 messages.

## Technical Analysis
- Catalog: 0 CHECK (Q-DISC-006). Nullability and defaults per column: Q-SCH-001.
- Defaults such as `isActive=True`, `taux_tva=19` and `statut=EN_ATTENTE` exist only in SQLAlchemy, so any write outside the ORM produces NULLs.
- The header ↔ lines consistency cannot be a CHECK. Either stop storing `montant_ht` / `montant_ttc` (compute them in a view or a generated column), or freeze them at issue time within a recomputing transaction.

## Root Cause
`create_all()` from models that declare types only. No business rule was ever translated into a constraint.

## Impact
Accounting and payroll records can be wrong without any error or alert.

## Proposed Solution
One Alembic revision, applied after checking the existing data with the audit's integrity queries. Draft:

```sql
ALTER TABLE invoices
  ALTER COLUMN statut SET NOT NULL, ALTER COLUMN statut SET DEFAULT 'BROUILLON',
  ALTER COLUMN montant_ht SET NOT NULL, ALTER COLUMN montant_ttc SET NOT NULL,
  ALTER COLUMN cree_par_id SET NOT NULL,
  ADD CONSTRAINT ck_invoices_amounts CHECK (montant_ht >= 0 AND montant_ttc >= montant_ht),
  ADD CONSTRAINT ck_invoices_dates   CHECK (date_echeance >= date_emission);
ALTER TABLE invoice_items
  ADD CONSTRAINT ck_items_qty   CHECK (quantite > 0),
  ADD CONSTRAINT ck_items_price CHECK (prix_unitaire >= 0),
  ADD CONSTRAINT ck_items_vat   CHECK (taux_tva BETWEEN 0 AND 100);
ALTER TABLE leave_requests
  ALTER COLUMN employee_id SET NOT NULL,
  ALTER COLUMN statut SET NOT NULL, ALTER COLUMN statut SET DEFAULT 'EN_ATTENTE',
  ADD CONSTRAINT ck_leave_dates CHECK (date_fin >= date_debut),
  ADD CONSTRAINT ck_leave_no_self_validation CHECK (valide_par_id IS NULL OR valide_par_id <> employee_id),
  ADD CONSTRAINT ck_leave_decision_has_validator CHECK (statut = 'EN_ATTENTE' OR valide_par_id IS NOT NULL);
ALTER TABLE payslips
  ADD CONSTRAINT ck_payslip_amounts CHECK (montant_brut >= 0 AND montant_net >= 0 AND montant_net <= montant_brut),
  ADD CONSTRAINT ck_payslip_month   CHECK (extract(day FROM periode) = 1);
ALTER TABLE users
  ALTER COLUMN role SET NOT NULL, ALTER COLUMN "hashedPassword" SET NOT NULL,
  ALTER COLUMN "isActive" SET NOT NULL, ALTER COLUMN "isActive" SET DEFAULT true,
  ADD CONSTRAINT ck_users_role CHECK (role IN ('admin','employee','accountant'));
CREATE UNIQUE INDEX ux_users_email_ci  ON users (lower(email));
CREATE UNIQUE INDEX ux_devices_serial  ON devices ("serialNumber") WHERE "serialNumber" IS NOT NULL;
ALTER TABLE devices ADD CONSTRAINT ck_devices_price CHECK (price >= 0);
```

Mirror these rules in the Pydantic input schemas (`condecimal(ge=0)`, date validators, and so on).

## Acceptance Criteria
- [ ] Re-running the audit's constraint probe rejects every case, except those explicitly waived by a business decision.
- [ ] Each CHECK has a matching Pydantic validation that returns 422 before reaching the database.
- [ ] Existing data passes the migration, as checked beforehand with the integrity queries.
- [ ] Defaults that matter (`isActive`, `statut`, `taux_tva`, `quantite`) exist on the database side.

## Evidence
Constraint probe of 2026-10-02: 26/30 invalid writes accepted, 0 residual rows after rollback. Catalog queries Q-DISC-006, Q-SCH-001 and Q-SCH-003.

## Related Findings
AUDIT-DB-014 (HIGH); the nullable-FK part of AUDIT-DB-016

## Dependencies
- TICKET-DB-001.
- Business decisions:
  - one account per person (case-insensitive e-mail);
  - whether leave overlaps are forbidden (if yes: `btree_gist` + `EXCLUDE` constraint);
  - whether `rh` is a real role, since `ck_users_role` would reject it.
- The audit's `AUDIT-TEST` invoices with a NULL status must be cleaned up first.

## Estimated Complexity
M
