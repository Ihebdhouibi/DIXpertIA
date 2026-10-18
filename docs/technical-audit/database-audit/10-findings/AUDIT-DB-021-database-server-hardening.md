# AUDIT-DB-021 — Configuration du serveur PostgreSQL : journalisation et délais de garde absents

## Sévérité
LOW

**Justification :**
- C'est une instance **locale de développement**. Les paramètres observés sont
  ceux d'une installation par défaut, et `pg_hba.conf` n'autorise que
  localhost, ce qui limite l'exposition.
- Le niveau LOW vaut pour cet environnement. Les mêmes valeurs sur un serveur
  de production justifieraient MEDIUM. Ce point est `NOT VERIFIED`, faute
  d'accès.

## Catégorie
Sécurité / Exploitation

## Statut
OPEN · CONFIRMED (environnement local)

## Résumé

| Paramètre | Valeur | Risque |
|---|---|---|
| `log_connections`, `log_disconnections` | `off` | aucune trace des accès à la base |
| `log_statement` | `none` | aucune trace des modifications de schéma ni des requêtes |
| `statement_timeout` | `0` | une requête emballée tourne indéfiniment |
| `idle_in_transaction_session_timeout` | `0` | une transaction oubliée garde ses verrous indéfiniment |
| `ssl` | `off` | flux en clair (sans objet en local) |
| `listen_addresses` | `*` | écoute sur toutes les interfaces ; **compensé** par `pg_hba.conf`, qui n'autorise que `127.0.0.1` et `::1` |
| Authentification | `scram-sha-256` partout, aucune règle `trust` | ✅ |

## Détails techniques
Q-SEC-006 (`pg_settings`), Q-SEC-007 (`pg_hba_file_rules`).

## Impact métier
Il serait impossible d'établir après coup qui s'est connecté à la base. Un
risque de blocage existe aussi en cas de transaction applicative oubliée.

## Preuves
`11-evidence/sql-results/05-security.results.md`.

## Composants concernés
`postgresql.conf`, `pg_hba.conf` de l'instance.

## Localisation
- **Code :** —
- **Base :** paramètres du serveur.

## Cause racine
Valeurs par défaut de l'installeur.

## Recommandation
Pour tout environnement partagé ou de production :
- `log_connections = on` ;
- `log_disconnections = on` ;
- `log_statement = 'ddl'` ;
- `idle_in_transaction_session_timeout = '5min'` ;
- `statement_timeout` réglé **par rôle** (par exemple `ALTER ROLE dixpertia_app SET statement_timeout = '30s'`) ;
- `ssl = on` si la base n'est pas sur le même hôte que l'application ;
- `listen_addresses` restreint aux interfaces utiles.

## Correctif proposé
Il s'agit de configuration et non de code. À consigner dans un document
d'exploitation, qui n'existe pas aujourd'hui (AUDIT-DB-022).

## Risques du correctif
Un `statement_timeout` trop court interromprait les migrations : il faut le
régler sur le rôle applicatif uniquement, et non sur le rôle de migration.

## Validation
Q-SEC-006 rejouée sur chaque environnement.

## Effort estimé
S.

## Dépendances
AUDIT-DB-006 (rôle applicatif, porteur du `statement_timeout`).

## Findings liés
AUDIT-DB-006, AUDIT-DB-017.
