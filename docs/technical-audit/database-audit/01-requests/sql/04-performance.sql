-- Phase 7 — Performance.
-- Lecture seule. EXPLAIN sans ANALYZE : le plan est calculé, la requête n'est pas exécutée.
--
-- LIMITE : au 2026-10-01 les tables sont vides ou presque. Sur une table vide, le planificateur
-- choisit presque toujours un parcours séquentiel, quel que soit l'index disponible. Ces plans
-- servent donc à établir QUELS index sont utilisables, pas à mesurer des temps. Les requêtes
-- reproduisent celles que le code émet réellement (référence en commentaire).

-- @id: Q-PERF-001
-- @purpose: Statistiques d'accès par table : parcours séquentiels vs parcours d'index depuis le dernier redémarrage.
-- @expected: indicatif seulement sur une base de développement fraîchement redémarrée.
SELECT relname AS table_name, seq_scan, seq_tup_read, idx_scan, n_live_tup, n_dead_tup, last_analyze, last_autoanalyze
FROM pg_stat_user_tables ORDER BY relname;

-- @id: Q-PERF-002
-- @purpose: Index jamais utilisés depuis le dernier redémarrage (candidats à la suppression s'ils sont aussi redondants).
-- @expected: indicatif seulement — une base de développement redémarrée n'a pas d'historique d'usage.
SELECT s.relname AS table_name, s.indexrelname AS index_name, s.idx_scan, pg_size_pretty(pg_relation_size(s.indexrelid)) AS size
FROM pg_stat_user_indexes s ORDER BY s.relname, s.indexrelname;

-- @id: Q-PERF-003
-- @purpose: Plan de la connexion — recherche d'un utilisateur par e-mail (main.py:198).
-- @expected: index unique sur email utilisable (ix_users_email).
EXPLAIN SELECT * FROM users WHERE email = 'nobody@example.invalid';

-- @id: Q-PERF-004
-- @purpose: Plan de la résolution du jeton à chaque requête authentifiée (main.py:111, deps.py:28).
-- @expected: index de PK sur users.id.
EXPLAIN SELECT * FROM users WHERE id = 'USR-000';

-- @id: Q-PERF-005
-- @purpose: Plan de la liste des factures (app/routers/invoicing.py:52) — sans LIMIT ni filtre.
-- @expected: aucun index sur date_emission : tri complet en mémoire à chaque appel.
EXPLAIN SELECT * FROM invoices ORDER BY date_emission DESC;

-- @id: Q-PERF-006
-- @purpose: Plan du filtre comptable « factures d'un client » (besoin métier, non implémenté).
-- @expected: aucun index sur invoices.client_id : parcours complet.
EXPLAIN SELECT * FROM invoices WHERE client_id = 1 ORDER BY date_emission DESC;

-- @id: Q-PERF-007
-- @purpose: Plan du filtre comptable « factures d'un mois » (besoin métier, non implémenté).
-- @expected: aucun index sur date_emission : parcours complet.
EXPLAIN SELECT * FROM invoices WHERE date_emission >= DATE '2026-09-01' AND date_emission < DATE '2026-10-01';

-- @id: Q-PERF-008
-- @purpose: Plan du chargement des lignes d'une facture (relation Invoice.items, lazy select, invoicing.py:109).
-- @expected: aucun index sur invoice_items.invoice_id : parcours complet par facture.
EXPLAIN SELECT * FROM invoice_items WHERE invoice_id = 1;

-- @id: Q-PERF-009
-- @purpose: Plan de la génération du numéro de facture (invoicing.py:37) — LIKE sur numero puis count.
-- @expected: l'index unique sur numero n'est utilisable pour un LIKE préfixe qu'avec une collation C ou un opclass text_pattern_ops.
EXPLAIN SELECT count(*) FROM invoices WHERE numero LIKE 'FA-2026-%';

-- @id: Q-PERF-010
-- @purpose: Plan du filtre des bulletins d'un employé (main.py:509).
-- @expected: l'index unique (employee_id, periode) est utilisable car employee_id en est la première colonne.
EXPLAIN SELECT * FROM payslips WHERE employee_id = 'USR-000';

-- @id: Q-PERF-011
-- @purpose: Plan des congés d'un employé (app/routers/leaves.py:19 — non monté, mais requête cible du besoin).
-- @expected: aucun index sur leave_requests.employee_id.
EXPLAIN SELECT * FROM leave_requests WHERE employee_id = 'USR-000' ORDER BY created_at DESC;

-- @id: Q-PERF-012
-- @purpose: Coût de /api/data (main.py:498-509) : 6 lectures intégrales par appel, sans pagination.
-- @expected: 6 parcours complets ; le volume renvoyé croît linéairement avec chaque table.
EXPLAIN SELECT * FROM leave_requests;

-- ---------------------------------------------------------------------------
-- Ajout du 2026-10-02 : sur des tables vides, le planificateur choisit toujours un
-- parcours séquentiel. Pour savoir si un index est UTILISABLE, on désactive les
-- parcours séquentiels pour la durée de la requête (SET LOCAL, annulé au rollback).
-- Si le plan reste un « Seq Scan » malgré tout, AUCUN index ne peut servir la requête.

-- @id: Q-PERF-013
-- @purpose: Un index peut-il servir le tri de la liste des factures (ORDER BY date_emission) ?
-- @expected: Seq Scan forcé = aucun index sur date_emission.
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices ORDER BY date_emission DESC;

-- @id: Q-PERF-014
-- @purpose: Un index peut-il servir le filtre « factures d'un client » ?
-- @expected: Seq Scan forcé = aucun index sur invoices.client_id.
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices WHERE client_id = 1;

-- @id: Q-PERF-015
-- @purpose: Un index peut-il servir le filtre « factures d'un mois » ?
-- @expected: Seq Scan forcé = aucun index sur date_emission.
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoices WHERE date_emission >= DATE '2026-09-01' AND date_emission < DATE '2026-10-01';

-- @id: Q-PERF-016
-- @purpose: Un index peut-il servir le chargement des lignes d'une facture ?
-- @expected: Seq Scan forcé = aucun index sur invoice_items.invoice_id.
SET LOCAL enable_seqscan = off; EXPLAIN SELECT * FROM invoice_items WHERE invoice_id = 1;

-- @id: Q-PERF-017
-- @purpose: L'index unique sur numero peut-il servir le LIKE préfixe de la numérotation, avec la collation French_Tunisia.1252 ?
-- @expected: avec une collation non-C, un LIKE 'préfixe%' ne peut pas utiliser un index btree standard : on attend un parcours complet de l'index ou de la table, sans « Index Cond » sur numero.
SET LOCAL enable_seqscan = off; EXPLAIN SELECT count(*) FROM invoices WHERE numero LIKE 'FA-2026-%';
