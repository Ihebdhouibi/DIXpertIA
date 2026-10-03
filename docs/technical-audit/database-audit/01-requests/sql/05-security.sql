-- Phase 6 — Sécurité au niveau de la base.
-- Lecture seule. Aucun mot de passe, hash ou jeton n'est lu : seuls les attributs des rôles,
-- les droits et les paramètres serveur.

-- @id: Q-SEC-001
-- @purpose: Attributs de tous les rôles de connexion (superutilisateur, création de rôles/bases, contournement RLS).
-- @expected: un rôle applicatif sans aucun de ces attributs ; seul un rôle d'administration les possède.
SELECT rolname, rolsuper, rolcreaterole, rolcreatedb, rolbypassrls, rolcanlogin, rolconnlimit
FROM pg_roles WHERE rolname NOT LIKE 'pg\_%' ORDER BY rolname;

-- @id: Q-SEC-002
-- @purpose: Rôle effectivement utilisé par l'application, et s'il est superutilisateur.
-- @expected: rolsuper = false. true = toute faille d'injection ou de logique donne un contrôle total du serveur.
SELECT current_user AS app_role, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user;

-- @id: Q-SEC-003
-- @purpose: Droits accordés sur les tables applicatives, par rôle bénéficiaire (dont PUBLIC).
-- @expected: aucun droit à PUBLIC ; droits minimaux au rôle applicatif.
SELECT grantee, table_name, string_agg(privilege_type, ', ' ORDER BY privilege_type) AS privileges
FROM information_schema.role_table_grants
WHERE table_schema='public'
GROUP BY grantee, table_name ORDER BY grantee, table_name;

-- @id: Q-SEC-004
-- @purpose: Droits sur le schéma public (CREATE pour PUBLIC = n'importe quel rôle peut créer des objets).
-- @expected: PostgreSQL 15+ retire CREATE à PUBLIC par défaut.
SELECT nspname, has_schema_privilege('public', nspname, 'CREATE') AS public_can_create,
       has_schema_privilege('public', nspname, 'USAGE') AS public_can_use
FROM pg_namespace WHERE nspname='public';

-- @id: Q-SEC-005
-- @purpose: Row-level security par table (sujet du ticket #43).
-- @expected: aucune politique aujourd'hui — l'isolement des données repose entièrement sur l'application.
SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled, c.relforcerowsecurity AS rls_forced,
       (SELECT count(*) FROM pg_policy p WHERE p.polrelid=c.oid) AS policies
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='r' ORDER BY 1;

-- @id: Q-SEC-006
-- @purpose: Paramètres serveur liés à la sécurité : écoute réseau, SSL, chiffrement des mots de passe, journalisation.
-- @expected: listen_addresses limité ; password_encryption = scram-sha-256 ; journalisation des connexions activée.
SELECT name, setting, source
FROM pg_settings
WHERE name IN ('listen_addresses','port','ssl','password_encryption','log_connections','log_disconnections',
               'log_statement','log_min_duration_statement','max_connections','idle_in_transaction_session_timeout',
               'statement_timeout')
ORDER BY name;

-- @id: Q-SEC-007
-- @purpose: Règles d'authentification du serveur (pg_hba.conf) : méthode par type de connexion et adresse.
-- @expected: scram-sha-256 partout ; aucune règle `trust`. Lisible seulement par un superutilisateur.
SELECT line_number, type, database, user_name, address, netmask, auth_method
FROM pg_hba_file_rules ORDER BY line_number;

-- @id: Q-SEC-008
-- @purpose: Colonnes sensibles par table (repérage par nom), pour la cartographie des données sensibles.
-- @expected: inventaire seulement — aucune valeur lue.
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema='public'
  AND (column_name ILIKE '%password%' OR column_name ILIKE '%token%' OR column_name ILIKE '%secret%'
       OR column_name ILIKE '%email%' OR column_name ILIKE '%telephone%' OR column_name ILIKE '%adresse%'
       OR column_name ILIKE 'montant%' OR column_name ILIKE '%price%' OR column_name ILIKE '%motif%'
       OR column_name ILIKE '%fichier%')
ORDER BY 1, 2;
