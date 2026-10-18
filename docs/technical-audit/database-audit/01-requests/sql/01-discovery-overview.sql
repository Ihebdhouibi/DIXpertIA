-- Phase 1 — Discovery : vue d'ensemble de la base.
-- Uniquement des requêtes de catalogue en lecture seule (pg_catalog / information_schema).
-- Aucune requête ne lit le contenu des lignes applicatives : seulement des comptages et des métadonnées.

-- @id: Q-DISC-001
-- @purpose: Identifier le SGBD et sa version exacte.
-- @expected: PostgreSQL 17.x (installé en local le 2026-09-28).
SELECT version() AS server_version, current_setting('server_version_num') AS version_num;

-- @id: Q-DISC-002
-- @purpose: Confirmer la base, le rôle connecté, l'encodage, le fuseau horaire et la collation.
-- @expected: base dixpertia, encodage UTF8.
SELECT current_database() AS database, current_user AS connected_role,
       pg_encoding_to_char(d.encoding) AS encoding, d.datcollate AS collation,
       current_setting('TimeZone') AS server_timezone
FROM pg_database d WHERE d.datname = current_database();

-- @id: Q-DISC-003
-- @purpose: Vérifier si l'application se connecte en superutilisateur (principe du moindre privilège).
-- @expected: un rôle applicatif dédié, non superutilisateur. Un superutilisateur ici constitue une finding.
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
FROM pg_roles WHERE rolname = current_user;

-- @id: Q-DISC-004
-- @purpose: Lister les schémas non système.
-- @expected: public uniquement.
SELECT nspname AS schema FROM pg_namespace
WHERE nspname NOT IN ('pg_catalog','information_schema','pg_toast') AND nspname NOT LIKE 'pg_temp%' AND nspname NOT LIKE 'pg_toast_temp%'
ORDER BY 1;

-- @id: Q-DISC-005
-- @purpose: Inventaire des tables avec nombre de colonnes, nombre exact de lignes et taille.
-- @expected: 9 tables créées par tables.py le 2026-10-01 ; seule users contient des lignes.
SELECT c.relname AS table_name,
       (SELECT count(*) FROM information_schema.columns ic WHERE ic.table_schema='public' AND ic.table_name=c.relname) AS columns,
       (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM public.%I', c.relname), false, true, '')))[1]::text::int AS row_count,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY 1;

-- @id: Q-DISC-006
-- @purpose: Compter les contraintes par type et par table (p=PK, f=FK, u=UNIQUE, c=CHECK).
-- @expected: chaque table a une PK ; une FK existe partout où les modèles déclarent ForeignKey().
SELECT conrelid::regclass AS table_name,
       count(*) FILTER (WHERE contype='p') AS pk,
       count(*) FILTER (WHERE contype='f') AS fk,
       count(*) FILTER (WHERE contype='u') AS uniq,
       count(*) FILTER (WHERE contype='c') AS checks
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
GROUP BY 1 ORDER BY 1::text;

-- @id: Q-DISC-007
-- @purpose: Compter les index par table.
-- @expected: au moins un index (celui de la PK) par table.
SELECT tablename AS table_name, count(*) AS indexes
FROM pg_indexes WHERE schemaname='public' GROUP BY 1 ORDER BY 1;

-- @id: Q-DISC-008
-- @purpose: Lister les types ENUM PostgreSQL créés par les colonnes SQLAlchemy Enum.
-- @expected: invoicestatus, leavetype, leavestatus.
SELECT t.typname AS enum_type, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS labels
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname='public'
GROUP BY 1 ORDER BY 1;

-- @id: Q-DISC-009
-- @purpose: Vérifier la présence d'une table d'historique des migrations (Alembic) et d'objets hors modèles (vues, séquences, tables étrangères).
-- @expected: alembic_version présente si des migrations ont déjà été appliquées.
SELECT c.relname, c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND (c.relkind IN ('v','m','S','f') OR c.relname='alembic_version')
ORDER BY 1;

-- @id: Q-DISC-010
-- @purpose: Vérifier triggers et row-level security sur les tables applicatives.
-- @expected: inconnu. La RLS fait l'objet du ticket ouvert #43.
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
       (SELECT count(*) FROM pg_trigger tg WHERE tg.tgrelid=c.oid AND NOT tg.tgisinternal) AS user_triggers
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' ORDER BY 1;

-- @id: Q-DISC-011
-- @purpose: Lister les extensions installées.
-- @expected: plpgsql uniquement sur une base fraîche.
SELECT extname, extversion FROM pg_extension ORDER BY 1;
