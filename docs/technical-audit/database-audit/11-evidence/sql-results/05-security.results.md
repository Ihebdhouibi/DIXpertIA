# Résultats — 05-security.sql

- **Généré le :** 2026-10-02T11:32:23
- **Cible :** `postgresql://localhost:5432/dixpertia` (identifiants masqués)
- **Mode :** lecture seule (`default_transaction_read_only = on`, chaque requête annulée par rollback)
- **Source :** `docs/technical-audit/database-audit/01-requests/sql/05-security.sql`

- **Lecture seule confirmée par le serveur :** `on`

## Q-SEC-001

**Objectif :** Attributs de tous les rôles de connexion (superutilisateur, création de rôles/bases, contournement RLS).

**Résultat attendu :** un rôle applicatif sans aucun de ces attributs ; seul un rôle d'administration les possède.

```sql
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolcanlogin, rolconnlimit
FROM pg_roles WHERE rolname NOT LIKE 'pg\_%' ORDER BY rolname;
```

**Résultat observé :** 1 ligne(s)

| rolname | rolsuper | rolcreaterole | rolcreatedb | rolbypassrls | rolcanlogin | rolconnlimit |
|---|---|---|---|---|---|---|
| postgres | True | True | True | True | True | -1 |

## Q-SEC-002

**Objectif :** Rôle effectivement utilisé par l'application, et s'il est superutilisateur.

**Résultat attendu :** rolsuper = false. true = toute faille d'injection ou de logique donne un contrôle total du serveur.

```sql
SELECT current_user AS app_role, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;
```

**Résultat observé :** 1 ligne(s)

| app_role | rolsuper | rolbypassrls |
|---|---|---|
| postgres | True | True |

## Q-SEC-003

**Objectif :** Droits accordés sur les tables applicatives, par rôle bénéficiaire (dont PUBLIC).

**Résultat attendu :** aucun droit à PUBLIC ; droits minimaux au rôle applicatif.

```sql
SELECT grantee, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE table_schema='public'
GROUP BY grantee, table_name ORDER BY grantee, table_name;
```

**Résultat observé :** 9 ligne(s)

| grantee | table_name | privileges |
|---|---|---|
| postgres | clients | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | devices | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | invoice_items | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | invoices | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | leave_requests | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | payslips | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | services | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | team_members | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |
| postgres | users | DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE |

## Q-SEC-004

**Objectif :** Droits sur le schéma public (CREATE pour PUBLIC = n'importe quel rôle peut créer des objets).

**Résultat attendu :** PostgreSQL 15+ retire CREATE à PUBLIC par défaut.

```sql
SELECT nspname, has_schema_privilege('public', nspname, 'CREATE') AS public_can_create,
       has_schema_privilege('public', nspname, 'USAGE') AS public_can_use
FROM pg_namespace WHERE nspname='public';
```

**Résultat observé :** 1 ligne(s)

| nspname | public_can_create | public_can_use |
|---|---|---|
| public | False | True |

## Q-SEC-005

**Objectif :** Row-level security par table (sujet du ticket #43).

**Résultat attendu :** aucune politique aujourd'hui — l'isolement des données repose entièrement sur l'application.

```sql
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid=c.oid) AS policies
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' ORDER BY 1;
```

**Résultat observé :** 9 ligne(s)

| table_name | rls_enabled | rls_forced | policies |
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

## Q-SEC-006

**Objectif :** Paramètres serveur liés à la sécurité : écoute réseau, SSL, chiffrement des mots de passe, journalisation.

**Résultat attendu :** listen_addresses limité ; password_encryption = scram-sha-256 ; journalisation des connexions activée.

```sql
SELECT name, setting, source
FROM pg_settings
WHERE name IN ('listen_addresses','port','ssl','password_encryption','log_connections','log_disconnections',
               'log_statement','log_min_duration_statement','max_connections','idle_in_transaction_session_timeout',
               'statement_timeout')
ORDER BY name;
```

**Résultat observé :** 11 ligne(s)

| name | setting | source |
|---|---|---|
| idle_in_transaction_session_timeout | 0 | default |
| listen_addresses | * | configuration file |
| log_connections | off | default |
| log_disconnections | off | default |
| log_min_duration_statement | -1 | default |
| log_statement | none | default |
| max_connections | 100 | configuration file |
| password_encryption | scram-sha-256 | default |
| port | 5432 | configuration file |
| ssl | off | default |
| statement_timeout | 0 | default |

## Q-SEC-007

**Objectif :** Règles d'authentification du serveur (pg_hba.conf) : méthode par type de connexion et adresse.

**Résultat attendu :** scram-sha-256 partout ; aucune règle `trust`. Lisible seulement par un superutilisateur.

```sql
SELECT line_number, type, database, user_name, address, netmask, auth_method
FROM pg_hba_file_rules ORDER BY line_number;
```

**Résultat observé :** 6 ligne(s)

| line_number | type | database | user_name | address | netmask | auth_method |
|---|---|---|---|---|---|---|
| 113 | local | ['all'] | ['all'] | NULL | NULL | scram-sha-256 |
| 115 | host | ['all'] | ['all'] | 127.0.0.1 | 255.255.255.255 | scram-sha-256 |
| 117 | host | ['all'] | ['all'] | ::1 | ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff | scram-sha-256 |
| 120 | local | ['replication'] | ['all'] | NULL | NULL | scram-sha-256 |
| 121 | host | ['replication'] | ['all'] | 127.0.0.1 | 255.255.255.255 | scram-sha-256 |
| 122 | host | ['replication'] | ['all'] | ::1 | ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff | scram-sha-256 |

## Q-SEC-008

**Objectif :** Colonnes sensibles par table (repérage par nom), pour la cartographie des données sensibles.

**Résultat attendu :** inventaire seulement — aucune valeur lue.

```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public'
  AND (column_name ILIKE '%password%' OR column_name ILIKE '%token%' OR column_name ILIKE '%secret%'
       OR column_name ILIKE '%email%' OR column_name ILIKE '%telephone%' OR column_name ILIKE '%adresse%'
       OR column_name ILIKE 'montant%' OR column_name ILIKE '%price%' OR column_name ILIKE '%motif%'
       OR column_name ILIKE '%fichier%')
ORDER BY 1, 2;
```

**Résultat observé :** 15 ligne(s)

| table_name | column_name | data_type |
|---|---|---|
| clients | adresse | text |
| clients | email | character varying |
| clients | telephone | character varying |
| devices | price | double precision |
| invoices | montant_ht | numeric |
| invoices | montant_ttc | numeric |
| leave_requests | motif | text |
| payslips | fichier_pdf | character varying |
| payslips | montant_brut | numeric |
| payslips | montant_net | numeric |
| team_members | email | character varying |
| users | email | character varying |
| users | hashedPassword | character varying |
| users | resetToken | character varying |
| users | resetTokenExpiry | timestamp without time zone |

