# Résultats — 04-performance.sql

- **Généré le :** 2026-10-02T11:34:10
- **Cible :** `postgresql://localhost:5432/dixpertia` (identifiants masqués)
- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)
- **Source :** `docs/technical-audit/database-audit/01-requests/sql/04-performance.sql`

- **Lecture seule confirmée par le serveur :** `on`

## Q-PERF-001

**Objectif :** Statistiques d'accès par table : parcours séquentiels vs parcours d'index depuis le dernier redémarrage.

**Résultat attendu :** indicatif seulement sur une base de développement fraîchement redémarrée.

```sql
SELECT relname AS table_name, seq_scan, seq_tup_read, idx_scan, n_live_tup, n_dead_tup, last_analyze, last_autoanalyze
FROM pg_stat_user_tables ORDER BY relname;
```

**Résultat observé :** 9 ligne(s)

| table_name | seq_scan | seq_tup_read | idx_scan | n_live_tup | n_dead_tup | last_analyze | last_autoanalyze |
|---|---|---|---|---|---|---|---|
| clients | 5 | 0 | 0 | 0 | 0 | NULL | NULL |
| devices | 8 | 0 | 0 | 0 | 0 | NULL | NULL |
| invoice_items | 6 | 0 | 0 | 0 | 0 | NULL | NULL |
| invoices | 12 | 0 | 0 | 0 | 0 | NULL | NULL |
| leave_requests | 10 | 0 | 0 | 0 | 0 | NULL | NULL |
| payslips | 9 | 0 | 0 | 0 | 0 | NULL | NULL |
| services | 4 | 0 | 0 | 0 | 0 | NULL | NULL |
| team_members | 7 | 0 | 0 | 0 | 0 | NULL | NULL |
| users | 20 | 67 | 15 | 4 | 0 | NULL | NULL |

## Q-PERF-002

**Objectif :** Index jamais utilisés depuis le dernier redémarrage (candidats à la suppression s'ils sont aussi redondants).

**Résultat attendu :** indicatif seulement — une base de développement redémarrée n'a pas d'historique d'usage.

```sql
SELECT s.relname AS table_name, s.indexrelname AS index_name, s.idx_scan, pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s ORDER BY s.relname, s.indexrelname;
```

**Résultat observé :** 21 ligne(s)

| table_name | index_name | idx_scan | size |
|---|---|---|---|
| clients | clients_pkey | 0 | 8192 bytes |
| clients | ix_clients_id | 0 | 8192 bytes |
| devices | devices_pkey | 0 | 8192 bytes |
| devices | ix_devices_id | 0 | 8192 bytes |
| invoice_items | invoice_items_pkey | 0 | 8192 bytes |
| invoice_items | ix_invoice_items_id | 0 | 8192 bytes |
| invoices | invoices_numero_key | 0 | 8192 bytes |
| invoices | invoices_pkey | 0 | 8192 bytes |
| invoices | ix_invoices_id | 0 | 8192 bytes |
| leave_requests | ix_leave_requests_id | 0 | 8192 bytes |
| leave_requests | leave_requests_pkey | 0 | 8192 bytes |
| payslips | ix_payslips_id | 0 | 8192 bytes |
| payslips | payslips_pkey | 0 | 8192 bytes |
| payslips | uq_employee_periode | 0 | 8192 bytes |
| services | ix_services_id | 0 | 8192 bytes |
| services | services_pkey | 0 | 8192 bytes |
| team_members | ix_team_members_id | 0 | 8192 bytes |
| team_members | team_members_pkey | 0 | 8192 bytes |
| users | ix_users_email | 9 | 16 kB |
| users | ix_users_id | 6 | 16 kB |
| users | users_pkey | 0 | 16 kB |

## Q-PERF-003

**Objectif :** Plan de la connexion — recherche d'un utilisateur par e-mail (main.py:198).

**Résultat attendu :** index unique sur email utilisable (ix_users_email).

```sql
EXPLAIN SELECT * FROM users WHERE email = 'nobody@example.invalid';
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Index Scan using ix_users_email on users  (cost=0.14..8.16 rows=1 width=306) |
|   Index Cond: ((email)::text = 'nobody@example.invalid'::text) |

## Q-PERF-004

**Objectif :** Plan de la résolution du jeton à chaque requête authentifiée (main.py:111, deps.py:28).

**Résultat attendu :** index de PK sur users.id.

```sql
EXPLAIN SELECT * FROM users WHERE id = 'USR-000';
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Index Scan using ix_users_id on users  (cost=0.14..8.16 rows=1 width=306) |
|   Index Cond: ((id)::text = 'USR-000'::text) |

## Q-PERF-005

**Objectif :** Plan de la liste des factures (app/routers/invoicing.py:52) — sans LIMIT ni filtre.

**Résultat attendu :** aucun index sur date_emission : tri complet en mémoire à chaque appel.

```sql
EXPLAIN SELECT * FROM invoices ORDER BY date_emission DESC;
```

**Résultat observé :** 3 ligne(s)

| QUERY PLAN |
|---|
| Sort  (cost=32.50..33.55 rows=420 width=162) |
|   Sort Key: date_emission DESC |
|   ->  Seq Scan on invoices  (cost=0.00..14.20 rows=420 width=162) |

## Q-PERF-006

**Objectif :** Plan du filtre comptable « factures d'un client » (besoin métier, non implémenté).

**Résultat attendu :** aucun index sur invoices.client_id : parcours complet.

```sql
EXPLAIN SELECT * FROM invoices WHERE client_id = 1 ORDER BY date_emission DESC;
```

**Résultat observé :** 4 ligne(s)

| QUERY PLAN |
|---|
| Sort  (cost=15.26..15.27 rows=2 width=162) |
|   Sort Key: date_emission DESC |
|   ->  Seq Scan on invoices  (cost=0.00..15.25 rows=2 width=162) |
|         Filter: (client_id = 1) |

## Q-PERF-007

**Objectif :** Plan du filtre comptable « factures d'un mois » (besoin métier, non implémenté).

**Résultat attendu :** aucun index sur date_emission : parcours complet.

```sql
EXPLAIN SELECT * FROM invoices WHERE date_emission >= DATE '2026-09-01' AND date_emission < DATE '2026-10-01';
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on invoices  (cost=0.00..16.30 rows=2 width=162) |
|   Filter: ((date_emission >= '2026-09-01'::date) AND (date_emission < '2026-10-01'::date)) |

## Q-PERF-008

**Objectif :** Plan du chargement des lignes d'une facture (relation Invoice.items, lazy select, invoicing.py:109).

**Résultat attendu :** aucun index sur invoice_items.invoice_id : parcours complet par facture.

```sql
EXPLAIN SELECT * FROM invoice_items WHERE invoice_id = 1;
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on invoice_items  (cost=0.00..11.62 rows=1 width=566) |
|   Filter: (invoice_id = 1) |

## Q-PERF-009

**Objectif :** Plan de la génération du numéro de facture (invoicing.py:37) — LIKE sur numero puis count.

**Résultat attendu :** l'index unique sur numero n'est utilisable pour un LIKE préfixe qu'avec une collation C ou un opclass text_pattern_ops.

```sql
EXPLAIN SELECT count(*) FROM invoices WHERE numero LIKE 'FA-2026-%';
```

**Résultat observé :** 3 ligne(s)

| QUERY PLAN |
|---|
| Aggregate  (cost=15.26..15.27 rows=1 width=8) |
|   ->  Seq Scan on invoices  (cost=0.00..15.25 rows=2 width=0) |
|         Filter: ((numero)::text ~~ 'FA-2026-%'::text) |

## Q-PERF-010

**Objectif :** Plan du filtre des bulletins d'un employé (main.py:509).

**Résultat attendu :** l'index unique (employee_id, periode) est utilisable car employee_id en est la première colonne.

```sql
EXPLAIN SELECT * FROM payslips WHERE employee_id = 'USR-000';
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Index Scan using uq_employee_periode on payslips  (cost=0.14..8.16 rows=1 width=596) |
|   Index Cond: ((employee_id)::text = 'USR-000'::text) |

## Q-PERF-011

**Objectif :** Plan des congés d'un employé (app/routers/leaves.py:19 — non monté, mais requête cible du besoin).

**Résultat attendu :** aucun index sur leave_requests.employee_id.

```sql
EXPLAIN SELECT * FROM leave_requests WHERE employee_id = 'USR-000' ORDER BY created_at DESC;
```

**Résultat observé :** 4 ligne(s)

| QUERY PLAN |
|---|
| Sort  (cost=15.51..15.52 rows=2 width=156) |
|   Sort Key: created_at DESC |
|   ->  Seq Scan on leave_requests  (cost=0.00..15.50 rows=2 width=156) |
|         Filter: ((employee_id)::text = 'USR-000'::text) |

## Q-PERF-012

**Objectif :** Coût de /api/data (main.py:498-509) : 6 lectures intégrales par appel, sans pagination.

**Résultat attendu :** 6 parcours complets ; le volume renvoyé croît linéairement avec chaque table.

```sql
EXPLAIN SELECT * FROM leave_requests;

-- ---------------------------------------------------------------------------
-- Ajout du 2026-10-02 : sur des tables vides, le planificateur choisit toujours un
-- parcours séquentiel. Pour savoir si un index est UTILISABLE, on désactive les
-- parcours séquentiels pour la durée de la requête (SET LOCAL, annulé au rollback).
-- Si le plan reste un « Seq Scan » malgré tout, AUCUN index ne peut servir la requête.
```

**Résultat observé :** 1 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on leave_requests  (cost=0.00..14.40 rows=440 width=156) |

## Q-PERF-013

**Objectif :** Un index peut-il servir le tri de la liste des factures (ORDER BY date_emission) ?

**Résultat attendu :** Seq Scan forcé = aucun index sur date_emission.

```sql
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices ORDER BY date_emission DESC;
```

**Résultat observé :** 3 ligne(s)

| QUERY PLAN |
|---|
| Sort  (cost=10000000032.50..10000000033.55 rows=420 width=162) |
|   Sort Key: date_emission DESC |
|   ->  Seq Scan on invoices  (cost=10000000000.00..10000000014.20 rows=420 width=162) |

## Q-PERF-014

**Objectif :** Un index peut-il servir le filtre « factures d'un client » ?

**Résultat attendu :** Seq Scan forcé = aucun index sur invoices.client_id.

```sql
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices WHERE client_id = 1;
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on invoices  (cost=10000000000.00..10000000015.25 rows=2 width=162) |
|   Filter: (client_id = 1) |

## Q-PERF-015

**Objectif :** Un index peut-il servir le filtre « factures d'un mois » ?

**Résultat attendu :** Seq Scan forcé = aucun index sur date_emission.

```sql
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices WHERE date_emission >= DATE '2026-09-01' AND date_emission < DATE '2026-10-01';
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on invoices  (cost=10000000000.00..10000000016.30 rows=2 width=162) |
|   Filter: ((date_emission >= '2026-09-01'::date) AND (date_emission < '2026-10-01'::date)) |

## Q-PERF-016

**Objectif :** Un index peut-il servir le chargement des lignes d'une facture ?

**Résultat attendu :** Seq Scan forcé = aucun index sur invoice_items.invoice_id.

```sql
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoice_items WHERE invoice_id = 1;
```

**Résultat observé :** 2 ligne(s)

| QUERY PLAN |
|---|
| Seq Scan on invoice_items  (cost=10000000000.00..10000000011.62 rows=1 width=566) |
|   Filter: (invoice_id = 1) |

## Q-PERF-017

**Objectif :** L'index unique sur numero peut-il servir le LIKE préfixe de la numérotation, avec la collation French_Tunisia.1252 ?

**Résultat attendu :** avec une collation non-C, un LIKE 'préfixe%' ne peut pas utiliser un index btree standard : on attend un parcours complet de l'index ou de la table, sans « Index Cond » sur numero.

```sql
SET LOCAL enable_seqscan = off; EXPLAIN SELECT count(*) FROM invoices WHERE numero LIKE 'FA-2026-%';
```

**Résultat observé :** 4 ligne(s)

| QUERY PLAN |
|---|
| Aggregate  (cost=21.50..21.51 rows=1 width=8) |
|   ->  Bitmap Heap Scan on invoices  (cost=6.25..21.50 rows=2 width=0) |
|         Filter: ((numero)::text ~~ 'FA-2026-%'::text) |
|         ->  Bitmap Index Scan on invoices_numero_key  (cost=0.00..6.25 rows=420 width=0) |

