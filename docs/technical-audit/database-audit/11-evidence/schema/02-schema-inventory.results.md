# Résultats — 02-schema-inventory.sql

- **Généré le :** 2026-10-02T11:32:21
- **Cible :** `postgresql://localhost:5432/dixpertia` (identifiants masqués)
- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)
- **Source :** `docs/technical-audit/database-audit/01-requests/sql/02-schema-inventory.sql`

- **Lecture seule confirmée par le serveur :** `on`

## Q-SCH-001

**Objectif :** Toutes les colonnes de toutes les tables : position, type, longueur/précision, nullabilité, valeur par défaut.

**Résultat attendu :** types cohérents avec les modèles ORM ; colonnes obligatoires en NOT NULL.

```sql
SELECT c.table_name, c.ordinal_position AS pos, c.column_name,
       CASE WHEN c.data_type = 'USER-DEFINED' THEN c.udt_name ELSE c.data_type END AS type,
       COALESCE(c.character_maximum_length::text, CASE WHEN c.numeric_precision IS NOT NULL AND c.data_type='numeric' THEN c.numeric_precision||','||c.numeric_scale END) AS size,
       c.is_nullable AS nullable, c.column_default AS default_value
FROM information_schema.columns c
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position;
```

**Résultat observé :** 71 ligne(s)

| table_name | pos | column_name | type | size | nullable | default_value |
|---|---|---|---|---|---|---|
| clients | 1 | id | integer | NULL | NO | nextval('clients_id_seq'::regclass) |
| clients | 2 | nom | character varying | 150 | NO | NULL |
| clients | 3 | email | character varying | 100 | YES | NULL |
| clients | 4 | telephone | character varying | 30 | YES | NULL |
| clients | 5 | adresse | text | NULL | YES | NULL |
| devices | 1 | id | character varying | NULL | NO | NULL |
| devices | 2 | name | character varying | NULL | YES | NULL |
| devices | 3 | model | character varying | NULL | YES | NULL |
| devices | 4 | serialNumber | character varying | NULL | YES | NULL |
| devices | 5 | price | double precision | NULL | YES | NULL |
| devices | 6 | status | character varying | NULL | YES | NULL |
| devices | 7 | createdAt | timestamp without time zone | NULL | YES | NULL |
| invoice_items | 1 | id | integer | NULL | NO | nextval('invoice_items_id_seq'::regclass) |
| invoice_items | 2 | invoice_id | integer | NULL | NO | NULL |
| invoice_items | 3 | designation | character varying | 255 | NO | NULL |
| invoice_items | 4 | quantite | numeric | 8,2 | YES | NULL |
| invoice_items | 5 | prix_unitaire | numeric | 10,2 | NO | NULL |
| invoice_items | 6 | taux_tva | numeric | 4,2 | YES | NULL |
| invoices | 1 | id | integer | NULL | NO | nextval('invoices_id_seq'::regclass) |
| invoices | 2 | numero | character varying | 30 | NO | NULL |
| invoices | 3 | client_id | integer | NULL | NO | NULL |
| invoices | 4 | date_emission | date | NULL | NO | NULL |
| invoices | 5 | date_echeance | date | NULL | NO | NULL |
| invoices | 6 | montant_ht | numeric | 10,2 | YES | NULL |
| invoices | 7 | montant_ttc | numeric | 10,2 | YES | NULL |
| invoices | 8 | statut | invoicestatus | NULL | YES | NULL |
| invoices | 9 | cree_par_id | character varying | NULL | YES | NULL |
| leave_requests | 1 | id | integer | NULL | NO | nextval('leave_requests_id_seq'::regclass) |
| leave_requests | 2 | employee_id | character varying | NULL | YES | NULL |
| leave_requests | 3 | date_debut | date | NULL | NO | NULL |
| leave_requests | 4 | date_fin | date | NULL | NO | NULL |
| leave_requests | 5 | type_conge | leavetype | NULL | YES | NULL |
| leave_requests | 6 | motif | text | NULL | YES | NULL |
| leave_requests | 7 | statut | leavestatus | NULL | YES | NULL |
| leave_requests | 8 | valide_par_id | character varying | NULL | YES | NULL |
| leave_requests | 9 | commentaire_validation | text | NULL | YES | NULL |
| leave_requests | 10 | created_at | timestamp with time zone | NULL | YES | now() |
| payslips | 1 | id | integer | NULL | NO | nextval('payslips_id_seq'::regclass) |
| payslips | 2 | employee_id | character varying | NULL | NO | NULL |
| payslips | 3 | periode | date | NULL | NO | NULL |
| payslips | 4 | montant_brut | numeric | 10,2 | NO | NULL |
| payslips | 5 | montant_net | numeric | 10,2 | NO | NULL |
| payslips | 6 | fichier_pdf | character varying | 255 | YES | NULL |
| payslips | 7 | date_emission | timestamp with time zone | NULL | YES | now() |
| services | 1 | id | integer | NULL | NO | nextval('services_id_seq'::regclass) |
| services | 2 | titre | character varying | 150 | NO | NULL |
| services | 3 | description | text | NULL | YES | NULL |
| services | 4 | image | character varying | 255 | YES | NULL |
| services | 5 | ordre_affichage | integer | NULL | YES | NULL |
| services | 6 | actif | boolean | NULL | YES | NULL |
| team_members | 1 | id | character varying | NULL | NO | NULL |
| team_members | 2 | firstName | character varying | NULL | YES | NULL |
| team_members | 3 | lastName | character varying | NULL | YES | NULL |
| team_members | 4 | email | character varying | NULL | YES | NULL |
| team_members | 5 | role | character varying | NULL | YES | NULL |
| team_members | 6 | status | character varying | NULL | YES | NULL |
| team_members | 7 | initials | character varying | NULL | YES | NULL |
| team_members | 8 | avatarUrl | character varying | NULL | YES | NULL |
| users | 1 | id | character varying | NULL | NO | NULL |
| users | 2 | email | character varying | NULL | NO | NULL |
| users | 3 | firstName | character varying | NULL | YES | NULL |
| users | 4 | lastName | character varying | NULL | YES | NULL |
| users | 5 | role | character varying | NULL | YES | NULL |
| users | 6 | department | character varying | NULL | YES | NULL |
| users | 7 | avatarUrl | character varying | NULL | YES | NULL |
| users | 8 | hashedPassword | character varying | NULL | YES | NULL |
| users | 9 | isActive | boolean | NULL | YES | NULL |
| users | 10 | isVerified | boolean | NULL | YES | NULL |
| users | 11 | resetToken | character varying | NULL | YES | NULL |
| users | 12 | resetTokenExpiry | timestamp without time zone | NULL | YES | NULL |
| users | 13 | createdAt | timestamp without time zone | NULL | YES | NULL |

## Q-SCH-002

**Objectif :** Colonnes dont le nom exige des guillemets (majuscules) : impact sur le SQL écrit à la main et sur les outils.

**Résultat attendu :** aucune, si la convention snake_case était respectée.

```sql
SELECT table_name, column_name
FROM information_schema.columns
WHERE table_schema='public' AND column_name <> lower(column_name)
ORDER BY 1, 2;
```

**Résultat observé :** 14 ligne(s)

| table_name | column_name |
|---|---|
| devices | createdAt |
| devices | serialNumber |
| team_members | avatarUrl |
| team_members | firstName |
| team_members | lastName |
| users | avatarUrl |
| users | createdAt |
| users | firstName |
| users | hashedPassword |
| users | isActive |
| users | isVerified |
| users | lastName |
| users | resetToken |
| users | resetTokenExpiry |

## Q-SCH-003

**Objectif :** Toutes les contraintes avec leur définition exacte (PK, FK, UNIQUE, CHECK).

**Résultat attendu :** PK partout ; FK conformes aux modèles ; CHECK métier (montants, dates) — aucune n'est déclarée dans les modèles.

```sql
SELECT conrelid::regclass AS table_name, conname AS constraint_name,
       CASE contype WHEN 'p' THEN 'PRIMARY KEY' WHEN 'f' THEN 'FOREIGN KEY' WHEN 'u' THEN 'UNIQUE' WHEN 'c' THEN 'CHECK' WHEN 'x' THEN 'EXCLUDE' ELSE contype::text END AS type,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'public'::regnamespace
ORDER BY 1::text, 3, 2;
```

**Résultat observé :** 17 ligne(s)

| table_name | constraint_name | type | definition |
|---|---|---|---|
| invoice_items | invoice_items_invoice_id_fkey | FOREIGN KEY | FOREIGN KEY (invoice_id) REFERENCES invoices(id) |
| invoices | invoices_client_id_fkey | FOREIGN KEY | FOREIGN KEY (client_id) REFERENCES clients(id) |
| invoices | invoices_cree_par_id_fkey | FOREIGN KEY | FOREIGN KEY (cree_par_id) REFERENCES users(id) |
| leave_requests | leave_requests_employee_id_fkey | FOREIGN KEY | FOREIGN KEY (employee_id) REFERENCES users(id) |
| leave_requests | leave_requests_valide_par_id_fkey | FOREIGN KEY | FOREIGN KEY (valide_par_id) REFERENCES users(id) |
| payslips | payslips_employee_id_fkey | FOREIGN KEY | FOREIGN KEY (employee_id) REFERENCES users(id) |
| clients | clients_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| devices | devices_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| invoice_items | invoice_items_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| invoices | invoices_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| leave_requests | leave_requests_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| payslips | payslips_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| services | services_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| team_members | team_members_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| users | users_pkey | PRIMARY KEY | PRIMARY KEY (id) |
| invoices | invoices_numero_key | UNIQUE | UNIQUE (numero) |
| payslips | uq_employee_periode | UNIQUE | UNIQUE (employee_id, periode) |

## Q-SCH-004

**Objectif :** Clés étrangères avec comportements ON DELETE / ON UPDATE et caractère différable.

**Résultat attendu :** un comportement choisi explicitement par relation (CASCADE / RESTRICT / SET NULL). NO ACTION partout signifie qu'aucun choix n'a été fait.

```sql
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
```

**Résultat observé :** 6 ligne(s)

| child_table | child_columns | parent_table | parent_columns | on_delete | on_update | deferrable | conname |
|---|---|---|---|---|---|---|---|
| invoices | client_id | clients | id | NO ACTION | NO ACTION | False | invoices_client_id_fkey |
| invoices | cree_par_id | users | id | NO ACTION | NO ACTION | False | invoices_cree_par_id_fkey |
| payslips | employee_id | users | id | NO ACTION | NO ACTION | False | payslips_employee_id_fkey |
| leave_requests | employee_id | users | id | NO ACTION | NO ACTION | False | leave_requests_employee_id_fkey |
| invoice_items | invoice_id | invoices | id | NO ACTION | NO ACTION | False | invoice_items_invoice_id_fkey |
| leave_requests | valide_par_id | users | id | NO ACTION | NO ACTION | False | leave_requests_valide_par_id_fkey |

## Q-SCH-005

**Objectif :** Tous les index avec leur définition, leur unicité et leur taille.

**Résultat attendu :** index PK, UNIQUE et index explicites des modèles (index=True) ; repérer les doublons (ex. PK + index=True sur la même colonne).

```sql
SELECT t.relname AS table_name, i.relname AS index_name, ix.indisunique AS is_unique, ix.indisprimary AS is_primary,
       pg_get_indexdef(ix.indexrelid) AS definition, pg_size_pretty(pg_relation_size(ix.indexrelid)) AS size
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_class t ON t.oid = ix.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname='public'
ORDER BY 1, 2;
```

**Résultat observé :** 21 ligne(s)

| table_name | index_name | is_unique | is_primary | definition | size |
|---|---|---|---|---|---|
| clients | clients_pkey | True | True | CREATE UNIQUE INDEX clients_pkey ON public.clients USING btree (id) | 8192 bytes |
| clients | ix_clients_id | False | False | CREATE INDEX ix_clients_id ON public.clients USING btree (id) | 8192 bytes |
| devices | devices_pkey | True | True | CREATE UNIQUE INDEX devices_pkey ON public.devices USING btree (id) | 8192 bytes |
| devices | ix_devices_id | False | False | CREATE INDEX ix_devices_id ON public.devices USING btree (id) | 8192 bytes |
| invoice_items | invoice_items_pkey | True | True | CREATE UNIQUE INDEX invoice_items_pkey ON public.invoice_items USING btree (id) | 8192 bytes |
| invoice_items | ix_invoice_items_id | False | False | CREATE INDEX ix_invoice_items_id ON public.invoice_items USING btree (id) | 8192 bytes |
| invoices | invoices_numero_key | True | False | CREATE UNIQUE INDEX invoices_numero_key ON public.invoices USING btree (numero) | 8192 bytes |
| invoices | invoices_pkey | True | True | CREATE UNIQUE INDEX invoices_pkey ON public.invoices USING btree (id) | 8192 bytes |
| invoices | ix_invoices_id | False | False | CREATE INDEX ix_invoices_id ON public.invoices USING btree (id) | 8192 bytes |
| leave_requests | ix_leave_requests_id | False | False | CREATE INDEX ix_leave_requests_id ON public.leave_requests USING btree (id) | 8192 bytes |
| leave_requests | leave_requests_pkey | True | True | CREATE UNIQUE INDEX leave_requests_pkey ON public.leave_requests USING btree (id) | 8192 bytes |
| payslips | ix_payslips_id | False | False | CREATE INDEX ix_payslips_id ON public.payslips USING btree (id) | 8192 bytes |
| payslips | payslips_pkey | True | True | CREATE UNIQUE INDEX payslips_pkey ON public.payslips USING btree (id) | 8192 bytes |
| payslips | uq_employee_periode | True | False | CREATE UNIQUE INDEX uq_employee_periode ON public.payslips USING btree (employee_id, periode) | 8192 bytes |
| services | ix_services_id | False | False | CREATE INDEX ix_services_id ON public.services USING btree (id) | 8192 bytes |
| services | services_pkey | True | True | CREATE UNIQUE INDEX services_pkey ON public.services USING btree (id) | 8192 bytes |
| team_members | ix_team_members_id | False | False | CREATE INDEX ix_team_members_id ON public.team_members USING btree (id) | 8192 bytes |
| team_members | team_members_pkey | True | True | CREATE UNIQUE INDEX team_members_pkey ON public.team_members USING btree (id) | 8192 bytes |
| users | ix_users_email | True | False | CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email) | 16 kB |
| users | ix_users_id | False | False | CREATE INDEX ix_users_id ON public.users USING btree (id) | 16 kB |
| users | users_pkey | True | True | CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id) | 16 kB |

## Q-SCH-006

**Objectif :** Index redondants : plusieurs index sur exactement les mêmes colonnes, dans le même ordre.

**Résultat attendu :** aucun. `primary_key=True, index=True` crée typiquement un doublon de l'index de PK.

```sql
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
```

**Résultat observé :** 9 ligne(s)

| table_name | indexes_on_same_columns | column_numbers |
|---|---|---|
| clients | clients_pkey, ix_clients_id | 1 |
| devices | devices_pkey, ix_devices_id | 1 |
| invoice_items | invoice_items_pkey, ix_invoice_items_id | 1 |
| invoices | invoices_pkey, ix_invoices_id | 1 |
| leave_requests | ix_leave_requests_id, leave_requests_pkey | 1 |
| payslips | ix_payslips_id, payslips_pkey | 1 |
| services | ix_services_id, services_pkey | 1 |
| team_members | ix_team_members_id, team_members_pkey | 1 |
| users | ix_users_id, users_pkey | 1 |

## Q-SCH-007

**Objectif :** Colonnes de clé étrangère non couvertes par un index dont elles sont la première colonne.

**Résultat attendu :** aucune. PostgreSQL n'indexe pas automatiquement les FK : jointures et suppressions du parent font alors des parcours complets.

```sql
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
```

**Résultat observé :** 5 ligne(s)

| table_name | fk_columns | references |
|---|---|---|
| invoices | client_id | clients |
| invoices | cree_par_id | users |
| leave_requests | employee_id | users |
| invoice_items | invoice_id | invoices |
| leave_requests | valide_par_id | users |

## Q-SCH-008

**Objectif :** Génération des clés primaires : séquences, colonnes identity, ou clés fournies par l'application.

**Résultat attendu :** PK entières sur séquence (SERIAL) ; PK VARCHAR sans défaut = générées par l'application (count()+1).

```sql
SELECT c.table_name, c.column_name, c.data_type, c.column_default, c.is_identity,
       pg_get_serial_sequence('public.'||quote_ident(c.table_name), c.column_name) AS sequence
FROM information_schema.columns c
JOIN information_schema.key_column_usage k
  ON k.table_schema=c.table_schema AND k.table_name=c.table_name AND k.column_name=c.column_name
JOIN information_schema.table_constraints tc
  ON tc.constraint_name=k.constraint_name AND tc.table_schema=k.table_schema AND tc.constraint_type='PRIMARY KEY'
WHERE c.table_schema='public'
ORDER BY 1;
```

**Résultat observé :** 9 ligne(s)

| table_name | column_name | data_type | column_default | is_identity | sequence |
|---|---|---|---|---|---|
| clients | id | integer | nextval('clients_id_seq'::regclass) | NO | public.clients_id_seq |
| devices | id | character varying | NULL | NO | NULL |
| invoice_items | id | integer | nextval('invoice_items_id_seq'::regclass) | NO | public.invoice_items_id_seq |
| invoices | id | integer | nextval('invoices_id_seq'::regclass) | NO | public.invoices_id_seq |
| leave_requests | id | integer | nextval('leave_requests_id_seq'::regclass) | NO | public.leave_requests_id_seq |
| payslips | id | integer | nextval('payslips_id_seq'::regclass) | NO | public.payslips_id_seq |
| services | id | integer | nextval('services_id_seq'::regclass) | NO | public.services_id_seq |
| team_members | id | character varying | NULL | NO | NULL |
| users | id | character varying | NULL | NO | NULL |

## Q-SCH-009

**Objectif :** Colonnes utilisant un type ENUM, et valeurs autorisées par type.

**Résultat attendu :** invoices.statut, leave_requests.type_conge, leave_requests.statut.

```sql
SELECT c.table_name, c.column_name, c.udt_name AS enum_type,
       (SELECT string_agg(e.enumlabel, ', ' ORDER BY e.enumsortorder) FROM pg_type t JOIN pg_enum e ON e.enumtypid=t.oid WHERE t.typname=c.udt_name) AS allowed_values
FROM information_schema.columns c
WHERE c.table_schema='public' AND c.data_type='USER-DEFINED'
ORDER BY 1, 2;
```

**Résultat observé :** 3 ligne(s)

| table_name | column_name | enum_type | allowed_values |
|---|---|---|---|
| invoices | statut | invoicestatus | BROUILLON, ENVOYEE, PAYEE, EN_RETARD, ANNULEE |
| leave_requests | statut | leavestatus | EN_ATTENTE, APPROUVE, REFUSE |
| leave_requests | type_conge | leavetype | PAYE, MALADIE, SANS_SOLDE |

## Q-SCH-010

**Objectif :** Types de date et d'horodatage par colonne (avec ou sans fuseau horaire).

**Résultat attendu :** une seule convention (timestamptz recommandé) ; dates métier en DATE.

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('date','timestamp without time zone','timestamp with time zone','time without time zone')
ORDER BY data_type, table_name, column_name;
```

**Résultat observé :** 10 ligne(s)

| table_name | column_name | data_type |
|---|---|---|
| invoices | date_echeance | date |
| invoices | date_emission | date |
| leave_requests | date_debut | date |
| leave_requests | date_fin | date |
| payslips | periode | date |
| leave_requests | created_at | timestamp with time zone |
| payslips | date_emission | timestamp with time zone |
| devices | createdAt | timestamp without time zone |
| users | createdAt | timestamp without time zone |
| users | resetTokenExpiry | timestamp without time zone |

## Q-SCH-011

**Objectif :** Colonnes monétaires et numériques : type et précision.

**Résultat attendu :** NUMERIC à précision fixe pour tout montant ; jamais de double precision (float) pour de l'argent.

```sql
SELECT table_name, column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('numeric','double precision','real','integer','bigint','smallint')
ORDER BY table_name, column_name;
```

**Résultat observé :** 17 ligne(s)

| table_name | column_name | data_type | numeric_precision | numeric_scale |
|---|---|---|---|---|
| clients | id | integer | 32 | 0 |
| devices | price | double precision | 53 | NULL |
| invoice_items | id | integer | 32 | 0 |
| invoice_items | invoice_id | integer | 32 | 0 |
| invoice_items | prix_unitaire | numeric | 10 | 2 |
| invoice_items | quantite | numeric | 8 | 2 |
| invoice_items | taux_tva | numeric | 4 | 2 |
| invoices | client_id | integer | 32 | 0 |
| invoices | id | integer | 32 | 0 |
| invoices | montant_ht | numeric | 10 | 2 |
| invoices | montant_ttc | numeric | 10 | 2 |
| leave_requests | id | integer | 32 | 0 |
| payslips | id | integer | 32 | 0 |
| payslips | montant_brut | numeric | 10 | 2 |
| payslips | montant_net | numeric | 10 | 2 |
| services | id | integer | 32 | 0 |
| services | ordre_affichage | integer | 32 | 0 |

## Q-SCH-012

**Objectif :** Colonnes texte sans longueur maximale (VARCHAR sans limite).

**Résultat attendu :** OBSERVATION seulement — non bloquant en PostgreSQL, mais révèle l'absence de règle de validation côté base.

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public' AND data_type IN ('character varying','text') AND character_maximum_length IS NULL
ORDER BY 1, 2;
```

**Résultat observé :** 30 ligne(s)

| table_name | column_name | data_type |
|---|---|---|
| clients | adresse | text |
| devices | id | character varying |
| devices | model | character varying |
| devices | name | character varying |
| devices | serialNumber | character varying |
| devices | status | character varying |
| invoices | cree_par_id | character varying |
| leave_requests | commentaire_validation | text |
| leave_requests | employee_id | character varying |
| leave_requests | motif | text |
| leave_requests | valide_par_id | character varying |
| payslips | employee_id | character varying |
| services | description | text |
| team_members | avatarUrl | character varying |
| team_members | email | character varying |
| team_members | firstName | character varying |
| team_members | id | character varying |
| team_members | initials | character varying |
| team_members | lastName | character varying |
| team_members | role | character varying |
| team_members | status | character varying |
| users | avatarUrl | character varying |
| users | department | character varying |
| users | email | character varying |
| users | firstName | character varying |
| users | hashedPassword | character varying |
| users | id | character varying |
| users | lastName | character varying |
| users | resetToken | character varying |
| users | role | character varying |

## Q-SCH-013

**Objectif :** Commentaires de documentation sur les tables et les colonnes.

**Résultat attendu :** inconnu. Leur absence est une OBSERVATION (aucune documentation de schéma dans la base).

```sql
SELECT c.relname AS table_name, a.attname AS column_name, d.description
FROM pg_description d
JOIN pg_class c ON c.oid=d.objoid
LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum=d.objsubid
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public'
ORDER BY 1, 2;
```

**Résultat observé :** 0 ligne(s)


