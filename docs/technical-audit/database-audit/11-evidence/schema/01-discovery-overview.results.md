# Résultats — 01-discovery-overview.sql

- **Généré le :** 2026-10-02T11:32:21
- **Cible :** `postgresql://localhost:5432/dixpertia` (identifiants masqués)
- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)
- **Source :** `docs/technical-audit/database-audit/01-requests/sql/01-discovery-overview.sql`

- **Lecture seule confirmée par le serveur :** `on`

## Q-DISC-001

**Objectif :** Identifier le SGBD et sa version exacte.

**Résultat attendu :** PostgreSQL 17.x (installé en local le 2026-09-28).

```sql
SELECT version() AS server_version, current_setting('server_version_num') AS version_num;
```

**Résultat observé :** 1 ligne(s)

| server_version | version_num |
|---|---|
| PostgreSQL 17.11 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit | 170011 |

## Q-DISC-002

**Objectif :** Confirmer la base, le rôle connecté, l'encodage, le fuseau horaire et la collation.

**Résultat attendu :** base dixpertia, encodage UTF8.

```sql
SELECT current_database() AS database, current_user AS connected_role,
       pg_encoding_to_char(d.encoding) AS encoding, d.datcollate AS collation,
       current_setting('TimeZone') AS server_timezone
FROM pg_database d WHERE d.datname = current_database();
```

**Résultat observé :** 1 ligne(s)

| database | connected_role | encoding | collation | server_timezone |
|---|---|---|---|---|
| dixpertia | postgres | UTF8 | French_Tunisia.1252 | Africa/Lagos |

## Q-DISC-003

**Objectif :** Vérifier si l'application se connecte en superutilisateur (principe du moindre privilège).

**Résultat attendu :** un rôle applicatif dédié, non superutilisateur. Un superutilisateur ici constitue une finding.

```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls
FROM pg_roles WHERE rolname = current_user;
```

**Résultat observé :** 1 ligne(s)

| rolname | rolsuper | rolcreaterole | rolcreatedb | rolbypassrls |
|---|---|---|---|---|
| postgres | True | True | True | True |

## Q-DISC-004

**Objectif :** Lister les schémas non système.

**Résultat attendu :** public uniquement.

```sql
SELECT nspname AS schema FROM pg_namespace
WHERE nspname NOT IN ('pg_catalog','information_schema','pg_toast') AND nspname NOT LIKE 'pg_temp%' AND nspname NOT LIKE 'pg_toast_temp%'
ORDER BY 1;
```

**Résultat observé :** 1 ligne(s)

| schema |
|---|
| public |

## Q-DISC-005

**Objectif :** Inventaire des tables avec nombre de colonnes, nombre exact de lignes et taille.

**Résultat attendu :** 9 tables créées par tables.py le 2026-10-01 ; seule users contient des lignes.

```sql
SELECT c.relname AS table_name,
       (SELECT count(*) FROM information_schema.columns ic WHERE ic.table_schema='public' AND ic.table_name=c.relname) AS columns,
       (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM public.%I', c.relname), false, true, '')))[1]::text::int AS row_count,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY 1;
```

**Résultat observé :** 9 ligne(s)

| table_name | columns | row_count | total_size |
|---|---|---|---|
| clients | 5 | 0 | 24 kB |
| devices | 7 | 0 | 24 kB |
| invoice_items | 6 | 0 | 16 kB |
| invoices | 9 | 0 | 32 kB |
| leave_requests | 10 | 0 | 24 kB |
| payslips | 7 | 0 | 32 kB |
| services | 6 | 0 | 24 kB |
| team_members | 8 | 0 | 24 kB |
| users | 13 | 4 | 64 kB |

## Q-DISC-006

**Objectif :** Compter les contraintes par type et par table (p=PK, f=FK, u=UNIQUE, c=CHECK).

**Résultat attendu :** chaque table a une PK ; une FK existe partout où les modèles déclarent ForeignKey().

```sql
SELECT conrelid::regclass AS table_name,
       count(*) FILTER (WHERE contype='p') AS pk,
       count(*) FILTER (WHERE contype='f') AS fk,
       count(*) FILTER (WHERE contype='u') AS uniq,
       count(*) FILTER (WHERE contype='c') AS checks
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
GROUP BY 1 ORDER BY 1::text;
```

**Résultat observé :** 9 ligne(s)

| table_name | pk | fk | uniq | checks |
|---|---|---|---|---|
| users | 1 | 0 | 0 | 0 |
| services | 1 | 0 | 0 | 0 |
| team_members | 1 | 0 | 0 | 0 |
| clients | 1 | 0 | 0 | 0 |
| devices | 1 | 0 | 0 | 0 |
| payslips | 1 | 1 | 1 | 0 |
| leave_requests | 1 | 2 | 0 | 0 |
| invoices | 1 | 2 | 1 | 0 |
| invoice_items | 1 | 1 | 0 | 0 |

## Q-DISC-007

**Objectif :** Compter les index par table.

**Résultat attendu :** au moins un index (celui de la PK) par table.

```sql
SELECT tablename AS table_name, count(*) AS indexes
FROM pg_indexes WHERE schemaname='public' GROUP BY 1 ORDER BY 1;
```

**Résultat observé :** 9 ligne(s)

| table_name | indexes |
|---|---|
| clients | 2 |
| devices | 2 |
| invoice_items | 2 |
| invoices | 3 |
| leave_requests | 2 |
| payslips | 3 |
| services | 2 |
| team_members | 2 |
| users | 3 |

## Q-DISC-008

**Objectif :** Lister les types ENUM PostgreSQL créés par les colonnes SQLAlchemy Enum.

**Résultat attendu :** invoicestatus, leavetype, leavestatus.

```sql
SELECT t.typname AS enum_type, string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) AS labels
FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid
JOIN pg_namespace n ON n.oid = t.typnamespace WHERE n.nspname='public'
GROUP BY 1 ORDER BY 1;
```

**Résultat observé :** 3 ligne(s)

| enum_type | labels |
|---|---|
| invoicestatus | BROUILLON, ENVOYEE, PAYEE, EN_RETARD, ANNULEE |
| leavestatus | EN_ATTENTE, APPROUVE, REFUSE |
| leavetype | PAYE, MALADIE, SANS_SOLDE |

## Q-DISC-009

**Objectif :** Vérifier la présence d'une table d'historique des migrations (Alembic) et d'objets hors modèles (vues, séquences, tables étrangères).

**Résultat attendu :** alembic_version présente si des migrations ont déjà été appliquées.

```sql
SELECT c.relname, c.relkind
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND (c.relkind IN ('v','m','S','f') OR c.relname='alembic_version')
ORDER BY 1;
```

**Résultat observé :** 6 ligne(s)

| relname | relkind |
|---|---|
| clients_id_seq | S |
| invoice_items_id_seq | S |
| invoices_id_seq | S |
| leave_requests_id_seq | S |
| payslips_id_seq | S |
| services_id_seq | S |

## Q-DISC-010

**Objectif :** Vérifier triggers et row-level security sur les tables applicatives.

**Résultat attendu :** inconnu. La RLS fait l'objet du ticket ouvert #43.

```sql
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
       (SELECT count(*) FROM pg_trigger tg WHERE tg.tgrelid=c.oid AND NOT tg.tgisinternal) AS user_triggers
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' ORDER BY 1;
```

**Résultat observé :** 9 ligne(s)

| table_name | rls_enabled | rls_forced | user_triggers |
|---|---|---|---|
| clients | False | False | 0 |
| devices | False | False | 0 |
| invoice_items | False | False | 0 |
| invoices | False | False | 0 |
| leave_requests | False | False | 0 |
| payslips | False | False | 0 |
| services | False | False | 0 |
| team_members | False | False | 0 |
| users | False | False | 0 |

## Q-DISC-011

**Objectif :** Lister les extensions installées.

**Résultat attendu :** plpgsql uniquement sur une base fraîche.

```sql
SELECT extname, extversion FROM pg_extension ORDER BY 1;
```

**Résultat observé :** 1 ligne(s)

| extname | extversion |
|---|---|
| plpgsql | 1.0 |

