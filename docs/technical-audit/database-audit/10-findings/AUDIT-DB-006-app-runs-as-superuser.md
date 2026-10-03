# AUDIT-DB-006 — L'application se connecte en superutilisateur PostgreSQL

## Sévérité
HIGH

**Justification :**
- **Impact :** maximal en cas de faille. Un superutilisateur peut lire et
  modifier toutes les bases du serveur, créer des rôles, contourner toute RLS
  (`bypassrls`), et exécuter des commandes système sur l'hôte
  (`COPY … TO PROGRAM`).
- **Exploitabilité directe :** faible aujourd'hui. Le code n'exécute aucun SQL
  brut (`06-security/security-static-analysis.md` § 6), et aucun vecteur
  d'injection n'a été trouvé.
- **Ce qui justifie HIGH :** c'est un **amplificateur**. Il transforme toute
  faille future, applicative ou de dépendance, en compromission totale du
  serveur de base. Il rend aussi inopérante la RLS prévue par le ticket #43.
- **Ce qui exclut CRITICAL :** il n'existe pas de vecteur d'exploitation
  directe.

## Catégorie
Sécurité / Moindre privilège

## Statut
OPEN · CONFIRMED

## Résumé
`DATABASE_URL` utilise le rôle `postgres`, qui possède `rolsuper`,
`rolcreaterole`, `rolcreatedb` et `rolbypassrls`. C'est le seul rôle de
connexion du serveur. Le mot de passe de ce rôle figure en clair dans la
valeur de repli du code.

## Détails techniques
- Q-DISC-003 et Q-SEC-002 : `postgres | rolsuper = true | rolbypassrls = true`.
- Q-SEC-001 : `postgres` est le seul rôle de connexion.
- Q-SEC-003 : tous les droits, `TRUNCATE` compris, sur les 9 tables.
- Valeur de repli `app/core/config.py:8` : URL complète avec l'utilisateur
  `postgres` et son mot de passe (`SECRET DETECTED — VALUE REDACTED`). Le
  commentaire de la ligne 7 la présente comme « the working hardcoded URL ».

## Impact métier
- Une faille dans l'API, ou dans une de ses 14 dépendances Python directes
  (`requirements.txt`) et leurs dépendances transitives, ouvrirait la
  totalité des données (paie, factures, comptes) **et** le serveur lui-même.
- La row-level security du ticket #43 serait **ignorée** tant que l'application
  garde `bypassrls`.

## Preuves
- `11-evidence/schema/01-discovery-overview.results.md`, Q-DISC-003.
- `11-evidence/sql-results/05-security.results.md`, Q-SEC-001 à 003.

## Composants concernés
`.env` / `DATABASE_URL`, `app/core/config.py`, configuration de PostgreSQL.

## Localisation
- **Code :** `app/core/config.py:7-8`.
- **Base :** rôle `postgres`.

## Cause racine
C'est la configuration par défaut d'une installation locale. Aucun rôle
applicatif n'a été créé, et l'URL de repli codée en dur l'a rendue durable.

## Recommandation
Créer **deux rôles** :
- `dixpertia_migrator`, propriétaire du schéma, utilisé seulement pour les
  migrations ;
- `dixpertia_app`, `LOGIN NOSUPERUSER NOBYPASSRLS`, avec seulement
  `SELECT, INSERT, UPDATE` sur les tables utiles, et `DELETE` uniquement là où
  une suppression est prévue.

Retirer l'URL de repli du code.

## Correctif proposé
```sql
CREATE ROLE dixpertia_app LOGIN PASSWORD '<secret>' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT CONNECT ON DATABASE dixpertia TO dixpertia_app;
GRANT USAGE ON SCHEMA public TO dixpertia_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO dixpertia_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO dixpertia_app;
-- DELETE accordé table par table, selon les règles de suppression retenues (AUDIT-DB-016)
```

Dans le code, `DATABASE_URL = os.environ["DATABASE_URL"]` : pas de valeur de
repli, et une erreur explicite au démarrage si la variable manque.

## Risques du correctif
- Un `DELETE` que l'application ferait réellement serait refusé. Seul
  `DELETE /api/devices` existe, et il est cassé (T-A05). Il faut l'inventorier
  au moment du correctif.
- `tables.py` et Alembic doivent tourner avec le rôle propriétaire.

## Validation
- Q-SEC-002 relancée avec le nouveau rôle : `rolsuper = false`,
  `rolbypassrls = false`.
- Les 20 tests de `run_api_tests.py` donnent les mêmes contrôles efficaces.
- Une tentative de `TRUNCATE` par le rôle applicatif est refusée.

## Effort estimé
S, plus la mise à jour des environnements.

## Dépendances
AUDIT-DB-015 : les migrations doivent appartenir au rôle propriétaire. Ticket #43.

## Findings liés
AUDIT-DB-007 (secrets dans le dépôt), AUDIT-DB-021 (configuration du serveur).
