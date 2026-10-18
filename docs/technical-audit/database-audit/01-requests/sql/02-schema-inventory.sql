-- Phase 2 — Inventaire détaillé du schéma.
-- Requêtes de catalogue uniquement, en lecture seule. Aucune ligne applicative n'est lue.

-- @id: Q-SCH-001
-- @purpose: Toutes les colonnes de toutes les tables : position, type, longueur/précision, nullabilité, valeur par défaut.
-- @expected: types cohérents avec les modèles ORM ; colonnes obligatoires en NOT NULL.
SELECT c.table_name, c.ordinal_position AS pos, c.column_name,
       CASE WHEN c.data_type = 'USER-DEFINED' THEN c.udt_name ELSE c.data_type END AS type,
       COALESCE(c.character_maximum_length::text, CASE WHEN c.numeric_precision IS NOT NULL AND c.data_type='numeric' THEN c.numeric_precision||','||c.numeric_scale END) AS size,
       c.is_nullable AS nullable, c.column_default AS default_value
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;

-- @id: Q-SCH-002
-- @purpose: Colonnes dont le nom exige des guillemets (majuscules) : impact sur le SQL écrit à la main et sur les outils.
-- @expected: aucune, si la convention snake_case était respectée.
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema='public' AND column_name <> lower(column_name)
ORDER BY 1, 2;

-- @id: Q-SCH-003
-- @purpose: Toutes les contraintes avec leur définition exacte (PK, FK, UNIQUE, CHECK).
-- @expected: PK partout ; FK conformes aux modèles ; CHECK métier (montants, dates) — aucune n'est déclarée dans les modèles.
SELECT conrelid::regclass AS table_name, conname AS constraint_name,
       CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY' WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK' WHEN 'x' THEN 'EXCLUDE' ELSE contype::text END AS type,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY 1::text, 3, 2;

-- @id: Q-SCH-004
-- @purpose: Clés étrangères avec comportements ON DELETE / ON UPDATE et caractère différable.
-- @expected: un comportement choisi explicitement par relation (CASCADE / RESTRICT / SET NULL). NO ACTION partout signifie qu'aucun choix n'a été fait.
SELECT conrelid::regclass AS child_table,
       (SELECT string_agg(a.attname, ', ') FROM unnest(conkey) k JOIN pg_attribute a ON a.attrelid=conrelid AND a.attnum=k) AS child_columns,
       confrelid::regclass AS parent_table,
       (SELECT string_agg(a.attname, ', ') FROM unnest(confkey) k JOIN pg_attribute a ON a.attrelid=confrelid AND a.attnum=k) AS parent_columns,
       CASE confdeltype WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT' WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END AS on_delete,
       CASE confupdtype WHEN 'a' THEN 'NO ACTION' WHEN 'r' THEN 'RESTRICT' WHEN 'c' THEN 'CASCADE' WHEN 'n' THEN 'SET NULL' WHEN 'd' THEN 'SET DEFAULT' END AS on_update,
       condeferrable AS deferrable, conname
FROM pg_constraint
WHERE contype='f' AND connamespace='public'::regnamespace
ORDER BY 1::text, 2;

-- @id: Q-SCH-005
-- @purpose: Tous les index avec leur définition, leur unicité et leur taille.
-- @expected: index PK, UNIQUE et index explicites des modèles (index=True) ; repérer les doublons (ex. PK + index=True sur la même colonne).
SELECT t.relname AS table_name, i.relname AS index_name, ix.indisunique AS is_unique, ix.indisprimary AS is_primary,
       pg_get_indexdef(ix.indexrelid) AS definition, pg_size_pretty(pg_relation_size(ix.indexrelid)) AS size
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_class t ON t.oid = ix.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname='public'
ORDER BY 1, 2;

-- @id: Q-SCH-006
-- @purpose: Index redondants : plusieurs index sur exactement les mêmes colonnes, dans le même ordre.
-- @expected: aucun. `primary_key=True, index=True` crée typiquement un doublon de l'index de PK.
SELECT t.relname AS table_name,
       string_agg(i.relname, ', ' ORDER BY i.relname) AS indexes_on_same_columns,
       ix.indkey::text AS column_numbers
FROM pg_index ix
JOIN pg_class i ON i.oid=ix.indexrelid
JOIN pg_class t ON t.oid=ix.indrelid
JOIN pg_namespace n ON n.oid=t.relnamespace
WHERE n.nspname='public'
GROUP BY t.relname, ix.indrelid, ix.indkey::text
HAVING count(*) > 1
ORDER BY 1;

-- @id: Q-SCH-007
-- @purpose: Colonnes de clé étrangère non couvertes par un index dont elles sont la première colonne.
-- @expected: aucune. PostgreSQL n'indexe pas automatiquement les FK : jointures et suppressions du parent font alors des parcours complets.
SELECT c.conrelid::regclass AS table_name,
       (SELECT string_agg(a.attname, ', ') FROM unnest(c.conkey) k JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attnum=k) AS fk_columns,
       c.confrelid::regclass AS references
FROM pg_constraint c
WHERE c.contype='f' AND c.connamespace='public'::regnamespace
  AND NOT EXISTS (
      SELECT 1 FROM pg_index ix
      WHERE ix.indrelid=c.conrelid AND ix.indkey[0] = c.conkey[1]
  )
ORDER BY 1::text, 2;

-- @id: Q-SCH-008
-- @purpose: Génération des clés primaires : séquences, colonnes identity, ou clés fournies par l'application.
-- @expected: PK entières sur séquence (SERIAL) ; PK VARCHAR sans défaut = générées par l'application (count()+1).
SELECT c.table_name, c.column_name, c.data_type, c.column_default, c.is_identity,
       pg_get_serial_sequence('public.'||quote_ident(c.table_name), c.column_name) AS sequence
FROM information_schema.columns c
JOIN information_schema.key_column_usage k
  ON k.table_schema=c.table_schema AND k.table_name=c.table_name AND k.column_name=c.column_name
JOIN information_schema.table_constraints tc
  ON tc.constraint_name=k.constraint_name AND tc.table_schema=k.table_schema AND tc.constraint_type='PRIMARY KEY'
WHERE c.table_schema='public'
ORDER BY 1;

-- @id: Q-SCH-009
-- @purpose: Colonnes utilisant un type ENUM, et valeurs autorisées par type.
-- @expected: invoices.statut, leave_requests.type_conge, leave_requests.statut.
SELECT c.table_name, c.column_name, c.udt_name AS enum_type,
       (SELECT string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid WHERE t.typname=c.udt_name) AS allowed_values
FROM information_schema.columns c
WHERE c.table_schema='public' AND c.data_type='USER-DEFINED'
ORDER BY 1, 2;

-- @id: Q-SCH-010
-- @purpose: Types de date et d'horodatage par colonne (avec ou sans fuseau horaire).
-- @expected: une seule convention (timestamptz recommandé) ; dates métier en DATE.
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('date','timestamp without time zone','timestamp with time zone','time without time zone')
ORDER BY data_type, table_name, column_name;

-- @id: Q-SCH-011
-- @purpose: Colonnes monétaires et numériques : type et précision.
-- @expected: NUMERIC à précision fixe pour tout montant ; jamais de double precision (float) pour de l'argent.
SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('numeric','double precision','real','integer','bigint','smallint')
ORDER BY table_name, column_name;

-- @id: Q-SCH-012
-- @purpose: Colonnes texte sans longueur maximale (VARCHAR sans limite).
-- @expected: OBSERVATION seulement — non bloquant en PostgreSQL, mais révèle l'absence de règle de validation côté base.
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('character varying','text') AND character_maximum_length IS NULL
ORDER BY 1, 2;

-- @id: Q-SCH-013
-- @purpose: Commentaires de documentation sur les tables et les colonnes.
-- @expected: inconnu. Leur absence est une OBSERVATION (aucune documentation de schéma dans la base).
SELECT c.relname AS table_name, a.attname AS column_name, d.description
FROM pg_description d
JOIN pg_class c ON c.oid=d.objoid
LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=d.objsubid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public'
ORDER BY 1, 2;
