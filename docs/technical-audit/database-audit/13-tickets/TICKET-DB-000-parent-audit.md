<!--
  Ticket parent, publié sur GitHub : #53 (2026-10-03). En anglais, selon la
  convention du dépôt. Il est fermé par la PR qui livre ce dossier ; la
  remédiation est suivie par la milestone dédiée.
-->

# [AUDIT] End-to-End Database & Data Architecture Audit

## Objective

Perform a complete end-to-end audit of the DI Xpertia database architecture, data model, relationships, ORM mappings, integrity constraints, access controls, security, performance and business rules.

## Scope

- Database schema
- Tables and columns
- Primary and foreign keys
- Relationships
- ORM models
- Migrations
- Constraints
- Indexes
- Data integrity
- RBAC and data access
- Security
- Performance
- Transactions
- Business rules
- Database/application consistency

## Deliverables

- Complete database inventory
- Relationship analysis
- ORM/database consistency analysis
- Data integrity analysis
- Security analysis
- Performance analysis
- Confirmed findings
- Evidence and reproducible queries
- Recommendations
- Remediation tickets
- Final audit report

## Technical Documentation

All audit material must be stored under:

`docs/technical-audit/database-audit/`

## Acceptance Criteria

- [x] Database schema fully inventoried
- [x] Models audited
- [x] Relationships audited
- [x] Constraints audited
- [x] Indexes audited
- [x] Data integrity checked
- [x] Access control checked
- [x] Security risks documented
- [x] Performance risks documented
- [x] Business rules reviewed
- [x] Findings classified
- [x] Evidence stored
- [x] Remediation tickets created
- [x] Final audit report completed

## Outcome (2026-10-02)

Audit completed against `develop` @ `34453a4` and a local PostgreSQL 17 database:
- 69 read-only catalog queries;
- 30 constraint probes, run in a transaction that is always rolled back;
- 20 runtime API tests;
- a full reading of the back end, and of the front end as a data consumer.

**24 confirmed findings: 1 critical, 10 high, 5 medium, 8 low.** They are grouped into 14 remediation tickets, tracked in the remediation milestone (not here):

- TICKET-DB-002 — Require authentication on every route, enforce roles, remove `/api/data` (**critical**)
- TICKET-DB-004 — Secrets, least-privilege database role, safe logging
- TICKET-DB-001 — Alembic baseline migration
- TICKET-DB-014 — API tests, Dockerfile, `.env.example`, setup docs
- TICKET-DB-005 — Unify the data model (implements #37)
- TICKET-DB-006 — Database-generated ids, reliable invoice numbering (#38, #39)
- TICKET-DB-007 — Integrity constraints
- TICKET-DB-008 — Invoice creation fixes
- TICKET-DB-011 — Complete the data model
- TICKET-DB-012 — Indexes and query patterns
- TICKET-DB-003 — Account lifecycle
- TICKET-DB-010 — Audit trail
- TICKET-DB-009 — Accountant workflow (#40, #41, #42)
- TICKET-DB-013 — Make the API the UI's source of truth

## Related

- #37 — decision: reconcile the split data model (API camelCase vs ORM French schema)
- #38 – #42 — Data integrity & schema milestone
- #43, #44 — Security hardening milestone
