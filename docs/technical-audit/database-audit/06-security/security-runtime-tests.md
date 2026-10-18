# Phase 6 — Sécurité : preuves à l'exécution

> 2026-10-02 · `develop` @ `34453a4` · backend local `127.0.0.1:8000`, base locale `dixpertia`
>
> **Preuves brutes :**
> - `11-evidence/api-tests/api-tests.results.md` (20 tests HTTP) ;
> - `11-evidence/sql-results/05-security.results.md` (Q-SEC) ;
> - `11-evidence/schema/01-discovery-overview.results.md` (Q-DISC) ;
> - log du backend pendant les tests, copie masquée avec les numéros de ligne
>   d'origine : `11-evidence/logs/backend-api-tests-2026-10-02.redacted.log`.
>
> **Reproduction :** voir `01-requests/README.md` (commandes et scripts).

## 1. Résultats

| Test | Observation | Comportement sûr attendu | Observé | Verdict |
|---|---|---|---|---|
| T-A01 | OBS-006 | 401 sans jeton | **404** « Leave request not found » : la requête a atteint la base sans authentification | **CONFIRMED** |
| T-A02 | OBS-006 | 401 | **404**, même mécanisme | **CONFIRMED** |
| T-A03 | OBS-008 | 401 | **500**. Log : `TypeError: 'employeeId' is an invalid keyword argument for LeaveRequest` | **CONFIRMED**, double défaut : aucune authentification, et une route qui plante toujours |
| T-A05 | OBS-010 | 200 pour un admin | **500**. Log : `TypeError: 'User' object is not subscriptable` | **CONFIRMED** : la gestion des appareils est inutilisable, **même par l'admin** |
| T-A06 | OBS-009 | — | `/api/data` renvoie, par utilisateur : `avatarUrl, createdAt, department, email, firstName, id, isActive, isVerified, lastName, role`. **Aucun hash ni jeton.** | contrôle `_PRIVATE_COLUMNS` **efficace** |
| T-A07 | OBS-021 | 201 | **500**. Log : `UniqueViolation … users_pkey` sur `USR-008` | **CONFIRMED** : la création de compte par l'admin échoue |
| T-A08 | OBS-014 | 401 | **401**, le jeton forgé avec la clé de repli est refusé | **REFUTED pour cet environnement**, qui définit `SECRET_KEY`. Le risque reste entier pour tout déploiement qui ne la définirait pas. |
| T-A09 | OBS-018 | temps comparables | médiane **24 ms** pour un compte inexistant, **292 ms** pour un compte existant avec un mauvais mot de passe | **CONFIRMED** : un attaquant peut savoir si un e-mail a un compte, à partir du seul temps de réponse (rapport ≈ 12) |
| T-B01 | OBS-009 · R-USR-06 | pas de comptes d'autrui | un **employé** reçoit les **7 comptes**, avec e-mail, rôle et département | **CONFIRMED** |
| T-B02 | contrôle | 403 | **403** sur `/api/invoices` | ✅ contrôle efficace |
| T-B03 | contrôle | 403 | **403** sur `/api/clients` | ✅ contrôle efficace |
| T-B04 | OBS-011 · R-USR-03 | 401 | **jeton délivré** à un compte `isActive = false` | **CONFIRMED** |
| T-B05 | R-FAC-01 · OBS-020 | 403 (création réservée à l'admin) | **500** ×2. Log : `ResponseValidationError … statut … input: None`. **En base : 2 factures créées** (`FA-2026-0001`, `FA-2026-0002`), au statut NULL, auteur `USR-009` (comptable) | **CONFIRMED**, triple défaut : la comptable crée des factures, le statut n'est jamais positionné, et chaque tentative crée une facture tout en renvoyant une erreur, d'où des **doublons** |
| T-B06 | contrôle | 403 | **403** sur le téléchargement du PDF par un employé | ✅ contrôle efficace |
| T-B07 | OBS-012 | 401 | **200** : le `resetToken` d'un employé, utilisé comme jeton `Bearer`, ouvre `/api/data`. La réponse contient les **factures** créées en T-B05. | **CONFIRMED** |
| T-B08 | OBS-007 · R-EQP-01 | 401 | **201** : un membre d'équipe est créé **sans authentification** (`TM-00001`), avec une adresse fabriquée `…@dixpertia.com` | **CONFIRMED** |
| T-B09 | OBS-006 · R-CNG-02 | 401 | **200** « Leave request approved successfully » ; **statut en base inchangé : `EN_ATTENTE`** | **CONFIRMED**, double défaut : approbation anonyme acceptée, et réponse de succès alors que rien n'est écrit |

**Bilan, sur 17 tests évalués :**
- **12 défauts confirmés** : T-A01, A02, A03, A05, A07, A09, B01, B04, B05,
  B07, B08 et B09 ;
- **4 contrôles efficaces** : T-A06, T-B02, T-B03 et T-B06 ;
- **1 risque réfuté pour l'environnement local** : T-A08.

T-A04 est purement informatif : `/logs` est public et renvoie `[]`.

T-B05 comporte 3 lignes dans le fichier de preuves (deux tentatives, puis
l'état en base), ce qui porte le nombre de lignes à 20.

## 2. Nouveau constat issu des tests

### OBS-035 — Les erreurs d'intégrité écrivent les paramètres SQL dans les logs, hash de mot de passe compris
- **Statut :** CONFIRMED (log du backend, ligne 434 de la sortie du 2026-10-02)
- **Fait :** lors de l'échec de T-A07, la trace de l'exception contient :

  ```text
  [parameters: {'id': 'USR-008', 'email': '<EMAIL>@audit-test.example.com', 'firstName': 'AUDIT-TEST', …,
                'hashedPassword': '<BCRYPT REDACTED>', 'isActive': True, …}]
  ```

  Ce sont l'e-mail et le **hash bcrypt du mot de passe provisoire**.
- **Aggravation :** la création de compte échoue **à chaque tentative**
  (OBS-021). Chaque essai de l'admin dépose donc un hash et un e-mail dans les
  logs du serveur.
- **Cause :** le moteur SQLAlchemy est créé sans `hide_parameters=True`
  (`app/core/database.py:6`).

## 3. Précision sur OBS-018 (journalisation des e-mails)

`logging.getLogger("dixpertia")` a un niveau effectif **WARNING** et **aucun
handler** : vérifié le 2026-10-02. Les messages `log.info("Login attempt for
%s")` de `main.py:197-205` **ne sont donc pas écrits** aujourd'hui. Le risque
est **latent** : il se concrétisera dès que la journalisation sera configurée
au niveau INFO.

L'énumération par le temps de réponse (T-A09), elle, est **effective dès
maintenant**.

## 4. Sécurité au niveau de la base (Q-SEC, Q-DISC)

| Point | Observé | Évaluation |
|---|---|---|
| Rôle utilisé par l'application | `postgres` : `rolsuper = true`, `rolcreaterole`, `rolcreatedb`, **`rolbypassrls = true`** (Q-SEC-002) | 🔴 **CONFIRMED** (OBS-016) : toute faille applicative donne le contrôle total du serveur PostgreSQL |
| Rôles applicatifs dédiés | **aucun** : `postgres` est le seul rôle de connexion (Q-SEC-001) | 🔴 |
| Droits | `postgres` a tous les droits, `TRUNCATE` compris, sur les 9 tables (Q-SEC-003) | conséquence du point précédent |
| `CREATE` pour `PUBLIC` sur le schéma `public` | non (Q-SEC-004) | ✅ comportement par défaut de PostgreSQL 15 et plus |
| RLS | désactivée sur les 9 tables, 0 politique (Q-SEC-005) | constat attendu (ticket #43), et sans effet tant que l'application est superutilisateur (`bypassrls`) |
| Méthode d'authentification | `scram-sha-256` partout ; aucune règle `trust` (Q-SEC-007) | ✅ |
| Écoute réseau | `listen_addresses = *` (Q-SEC-006), mais `pg_hba.conf` n'autorise que `127.0.0.1` et `::1` | ✅ en pratique ; défense en profondeur faible si `pg_hba.conf` est un jour élargi |
| SSL | `off` | sans objet en local ; `NOT VERIFIED` pour un déploiement |
| Journalisation des connexions | `log_connections = off`, `log_disconnections = off`, `log_statement = none` | ⚠️ aucune trace des accès à la base |
| Délais de garde | `statement_timeout = 0`, `idle_in_transaction_session_timeout = 0` | ⚠️ une requête ou une transaction oubliée peut bloquer indéfiniment |
| Chiffrement des mots de passe des rôles | `scram-sha-256` | ✅ |

## 5. Matrice d'accès vérifiée

Une case n'est remplie que si un test l'a vérifiée.

| Endpoint | Anonyme | Employé | Comptable | Admin | Compte désactivé |
|---|---|---|---|---|---|
| `POST /api/leave-requests/{id}/approve` | ✅ **accepté** (T-A01, T-B09) | | | | |
| `POST /api/leave-requests` | 💥 500 (T-A03) | | | | |
| `POST /api/team-members` | ✅ **accepté** (T-B08) | | | | |
| `GET /api/data` | 🔒 (constaté le 2026-10-01) | ✅ **tous les comptes** (T-B01) | | ✅ (T-A06) | via `resetToken` : ✅ (T-B07) |
| `GET /api/invoices`, `/api/clients` | | 🔒 403 (T-B02, T-B03) | | | |
| `POST /api/invoices` | | | ✅ **accepté**, puis 500 (T-B05) | | |
| `GET /api/invoices/{n}/download` | | 🔒 403 (T-B06) | | | |
| `GET /api/devices` | | | | 💥 500 (T-A05) | |
| `POST /api/users` | | | | 💥 500 (T-A07) | |
| `POST /api/login` | | | | | ✅ **jeton délivré** (T-B04) |

Légende : ✅ accès accordé · 🔒 refusé · 💥 erreur serveur.
