# Tickets

> 2026-10-02 · **brouillons, non encore publiés sur GitHub.** Ils sont rédigés en anglais
> parce qu'ils sont destinés à GitHub, conformément à la convention du dépôt.
>
> Les 24 findings sont regroupées en **14 tickets** par cause racine et par
> chantier, auxquels s'ajoute le **ticket parent** TICKET-DB-000.
>
> **Avant publication :** les tickets renvoient à des preuves qui vivent dans ce
> dossier. Les éléments clés sont résumés dans chaque ticket, pour qu'il
> reste compréhensible sans le dossier. Trois tickets recoupent des issues
> existantes, et doivent leur être **rattachés** plutôt que publiés en doublon :
> - TICKET-DB-005 ↔ #37 ;
> - TICKET-DB-006 ↔ #38 / #39 ;
> - TICKET-DB-004 ↔ #43.

## Ticket parent

- [TICKET-DB-000](TICKET-DB-000-parent-audit.md) — [AUDIT] End-to-End Database & Data Architecture Audit — **publié : #53**

## Tickets de remédiation, par phase

| Phase | Ticket | Titre | Findings | Sévérité max | Complexité | Issue existante |
|---|---|---|---|---|---|---|
| 0 | [TICKET-DB-002](TICKET-DB-002-enforce-authn-authz-remove-api-data.md) | Require authentication on every route, enforce roles, remove `/api/data` | 002, 003, 020 | **CRITICAL** | M | — |
| 0 | [TICKET-DB-004](TICKET-DB-004-secrets-db-privileges-logging.md) | Secrets, least-privilege DB role, safe logging | 006, 007, 008, 021 | HIGH | M | #43 |
| 1 | [TICKET-DB-001](TICKET-DB-001-alembic-baseline.md) | Alembic baseline migration | 015 | MEDIUM | S | — |
| 1 | [TICKET-DB-014](TICKET-DB-014-tests-docker-env-docs.md) | API tests, Dockerfile, `.env.example`, docs | 022 | LOW | M | — |
| 1 | [TICKET-DB-005](TICKET-DB-005-unify-data-model.md) | Unify the data model, rewrite routes, remove dead code | 013, 019 | HIGH | L | **#37** |
| 1 | [TICKET-DB-006](TICKET-DB-006-db-generated-ids-invoice-numbering.md) | DB-generated ids, reliable invoice numbering | 012 | HIGH | M | #38, #39 |
| 2 | [TICKET-DB-007](TICKET-DB-007-integrity-constraints.md) | Integrity constraints | 014, (016) | HIGH | M | — |
| 2 | [TICKET-DB-008](TICKET-DB-008-fix-invoice-creation.md) | Invoice creation: admin only, status, no duplicates | 010 | HIGH | S–M | — |
| 2 | [TICKET-DB-011](TICKET-DB-011-complete-data-model.md) | Employee entity, device ↔ invoice, `ON DELETE`, relationships | 016 | MEDIUM | L | — |
| 2 | [TICKET-DB-012](TICKET-DB-012-indexes-and-query-patterns.md) | Indexes, pagination, N+1 | 018 | LOW | S | — |
| 3 | [TICKET-DB-003](TICKET-DB-003-account-lifecycle.md) | Account lifecycle: deactivation, revocation, safe tokens | 004, 005, 009, 024 | HIGH | L | #44 (lié) |
| 3 | [TICKET-DB-010](TICKET-DB-010-audit-trail.md) | Audit trail | 017 | MEDIUM | M | — |
| 3 | [TICKET-DB-009](TICKET-DB-009-accounting-workflow.md) | Accountant workflow: review, notifications, filters | 011 | HIGH | XL | #40, #41, #42 |
| 4 | [TICKET-DB-013](TICKET-DB-013-api-as-source-of-truth-for-ui.md) | API as the UI's source of truth | 001, 023 | HIGH | XL | — |

## Couverture des findings

| Finding | Ticket(s) |
|---|---|
| 001 | 013 |
| 002, 003, 020 | 002 |
| 004, 005, 009, 024 | 003 |
| 006, 007, 008, 021 | 004 |
| 010 | 008 |
| 011 | 009 |
| 012 | 006 |
| 013, 019 | 005 |
| 014 | 007 |
| 015 | 001 |
| 016 | 011 (et 007 pour les `NOT NULL`) |
| 017 | 010 |
| 018 | 012 |
| 022 | 014 |
| 023 | 013 |

Les 24 findings sont couvertes, chacune par au moins un ticket.
