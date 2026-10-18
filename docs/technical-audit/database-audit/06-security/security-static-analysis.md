# Phase 6 — Sécurité des données : analyse statique

> 2026-10-01 · `develop` @ `34453a4`
>
> **Partie statique** : lecture du code, de l'historique git et de la
> configuration. Les preuves à l'exécution (appels HTTP par rôle, jetons
> détournés, compte désactivé) et la sécurité côté base (Q-SEC-001 à
> Q-SEC-008) font l'objet de `security-runtime-tests.md`, une fois le serveur
> rétabli.
>
> Aucun secret n'est reproduit. Toute valeur est notée
> `SECRET DETECTED — VALUE REDACTED`.

## 1. Carte des données sensibles

| Catégorie | Données | Table et colonne | Stockage | Chiffrement |
|---|---|---|---|---|
| Authentification | hash de mot de passe | `users.hashedPassword` | bcrypt (`$2b$`, coût par défaut 12) | ✅ hachage adapté |
| Authentification | jeton de réinitialisation | `users.resetToken` | **JWT en clair** | ❌ aucun : un accès en lecture à la table suffit pour réinitialiser le compte |
| Authentification | jeton de session | navigateur, `localStorage['token']` | JWT HS256, 60 min | — : lisible par tout script de la page |
| Données personnelles | e-mail, nom, prénom, département, avatar | `users`, `team_members` | clair | ❌ (normal pour ce type de données) |
| Données personnelles de tiers | nom, e-mail, téléphone, adresse des clients | `clients` | clair | ❌ |
| **Rémunération** | brut, net, PDF du bulletin | `payslips` | clair | ❌ |
| **Santé, potentiellement** | type de congé `maladie`, motif libre | `leave_requests.type_conge`, `.motif` | clair | ❌ |
| Financier et comptable | montants HT et TTC, TVA, lignes, client | `invoices`, `invoice_items` | clair | ❌ |
| Inventaire | prix et numéros de série | `devices` | clair | ❌ |

Le chiffrement au repos du disque ou de l'instance n'est pas visible dans le
dépôt : `NOT VERIFIED`. Pour une base locale de développement, il est sans
objet.

## 2. Ce que l'API expose

| Endpoint | Rôles | Données renvoyées | Évaluation |
|---|---|---|---|
| `POST /api/login` | public | profil sans secret | ✅ |
| `POST /api/users` | admin | id, e-mail et **mot de passe provisoire en clair** | ⚠️ décision assumée, documentée en `App.tsx:466-468`, mais le mot de passe transite dans une réponse HTTP |
| `GET /api/data` | **tout rôle connecté** | **tous** les utilisateurs (hors secrets), **toutes** les demandes de congé (motif et type compris), **toutes** les factures, tous les appareils et tous les membres d'équipe ; tous les bulletins pour l'admin et la comptable | 🔴 surexposition (OBS-009) ; le filtre `_PRIVATE_COLUMNS` (`main.py:118-129`) retire bien les hash et les jetons, ce qui est ✅ |
| `GET /api/clients` | `rh`, `admin`, `accountant` | coordonnées complètes des clients | ✅ cohérent avec le besoin comptable |
| `GET /api/invoices`, `/{id}` | `rh`, `admin`, `accountant` | factures et lignes | ✅ |
| `GET /api/invoices/{numero}/download` | `rh`, `admin`, `accountant` | PDF avec l'adresse du client | ✅ contrôle correct ; ⚠️ aucun journal des téléchargements |

**Point de conception :** `_row()` sérialise `obj.__dict__` en appliquant une
**liste d'exclusion**. Toute nouvelle colonne sensible ajoutée à un modèle sera
donc **exposée par défaut** par `/api/data`, tant que personne ne pense à
l'ajouter à `_PRIVATE_COLUMNS`. Une liste d'autorisation, comme un schéma de
sortie Pydantic par entité, inverserait ce défaut. CONFIRMED (code).

## 3. Secrets

| Constat | Localisation | Statut |
|---|---|---|
| Valeur de repli de `SECRET_KEY`, codée en dur, **identique à deux endroits** | `main.py:58`, `app/core/config.py:9` — `SECRET DETECTED — VALUE REDACTED` | CONFIRMED. Sans `SECRET_KEY` dans l'environnement, n'importe qui peut forger un jeton admin. Localement, `SECRET_KEY` est définie dans `.env`. |
| Valeur de repli de `DATABASE_URL`, avec le **mot de passe du compte `postgres`** | `app/core/config.py:8` — `SECRET DETECTED — VALUE REDACTED` | CONFIRMED. Le commentaire de la ligne 7 le décrit comme « the working hardcoded URL ». |
| **3 hash bcrypt de comptes réels** (2 admins, 1 comptable) et **1 jeton de réinitialisation** | `db.json`, versionné depuis le commit `4cec208` — `SECRET DETECTED — VALUE REDACTED` | CONFIRMED. Ils restent dans l'historique git même si le fichier est nettoyé. Le bcrypt rend l'attaque hors ligne coûteuse, mais pas impossible pour un mot de passe faible. |
| Fichier `.env` dans l'historique git | `git log --all -- .env .env.local env/` | ✅ jamais committé |
| `.env` ignoré | `.gitignore:10` | ✅ |
| Hook `detect-private-key` | `.pre-commit-config.yaml` | ✅ ; les règles ruff S105 et S106 couvrent les mots de passe codés en dur, mais elles ne détectent pas ces valeurs de repli, passées à `os.getenv` |
| Mot de passe par défaut des admins créés par script : `Admin123!` | `seed_users.py`, argument `--password` | ⚠️ c'est un mot de passe public, documenté dans le script. Le compte créé le 2026-10-01 l'utilise toujours. |

## 4. Journalisation

| Message | Référence | Donnée | Évaluation |
|---|---|---|---|
| `Login attempt for <email>` | `main.py:197` | e-mail | ⚠️ donnée personnelle dans chaque log de connexion |
| `Login failed: no user for <email>` / `bad password for <email>` | `main.py:200`, `:203` | e-mail et **cause de l'échec** | ⚠️ le log permet l'énumération des comptes : sans conséquence pour un attaquant externe, utile à quiconque lit les logs |
| `Login OK for <email> (role=…)` | `main.py:205` | e-mail et rôle | ⚠️ |
| `Email error: <exception>` | `main.py:90` | message de l'exception SMTP | ⚠️ peut contenir l'hôte ou l'identifiant SMTP, selon l'erreur |
| `Target: <DATABASE_URL>` | `tables.py:28` | **mot de passe de la base** | 🔴 OBS-017 |
| Jetons, hash, mots de passe provisoires | — | — | ✅ aucun n'est journalisé ; la PR #49 a retiré le mot de passe provisoire de la console |
| Journal d'audit métier (qui a fait quoi) | — | — | ❌ inexistant |

Aucune configuration de journalisation n'est faite : `logging.getLogger("dixpertia")`
n'a ni handler ni niveau défini. Ce qui sort, et où, dépend donc de la
configuration d'Uvicorn (`NOT VERIFIED`).

## 5. Jetons et sessions

| Point | État |
|---|---|
| Algorithme | HS256 (clé symétrique), algorithme fixé à la vérification : ✅ pas de confusion d'algorithme possible |
| Durée | 60 min, sans renouvellement (`main.py:60`) |
| Révocation | ❌ aucune ; la déconnexion est purement locale |
| Claim `role` | il est émis mais **ignoré** par le serveur, qui relit le rôle en base : ✅ **bonne pratique**, puisqu'un jeton ancien ne conserve pas un rôle retiré |
| Séparation des types de jeton | ❌ un jeton de réinitialisation est accepté comme jeton de session (OBS-012, à prouver) |
| Stockage côté client | `localStorage` : exposé à toute faille XSS |
| Lien de réinitialisation | jeton en paramètre d'URL (`?token=`), donc conservé dans l'historique du navigateur |

## 6. Injection et entrées

- **Aucun SQL brut** n'existe dans le code applicatif. Toutes les requêtes
  passent par l'ORM, avec des paramètres liés. Le risque d'injection SQL est
  **faible** : ✅ CONFIRMED (recherche de `text(`, `execute(` et de SQL dans des
  f-strings).
- Les e-mails sont validés par `EmailStr` à la connexion, à la création de
  compte et lors d'un mot de passe oublié.
- Les champs texte n'ont **aucune limite de longueur** côté API
  (`TeamMemberCreate`, `LeaveRequestCreate`, `ClientCreate`), et les colonnes
  `VARCHAR` sans limite les acceptent (Q-SCH-012). Combiné à l'endpoint anonyme
  `POST /api/team-members`, n'importe qui peut écrire des chaînes de taille
  arbitraire en base. SUSPECTED.

## 7. Suppression, rétention, sauvegardes

| Point | État |
|---|---|
| Suppression d'un compte | ❌ impossible côté serveur ; la suppression dans l'UI est locale seulement (R-USR-03) |
| Droit à l'effacement d'un salarié parti | ❌ aucun mécanisme ; l'anonymisation est rendue difficile par les FK `NO ACTION` vers `users` depuis les bulletins et les congés |
| Purge des jetons expirés | ❌ aucune (Q-INT-007) |
| Durée de conservation de la paie et des factures | non définie : `UNKNOWN / NEEDS VERIFICATION`. Les obligations légales de conservation imposent de pouvoir garder ces données **et** d'en restreindre l'accès. |
| Suppression physique | `DELETE /api/devices/{id}` (`main.py:473-482`) : sans corbeille ni trace |
| Sauvegardes | aucun script ni procédure dans le dépôt : `NOT VERIFIED` |

## 8. Accès administrateur au système

- L'application se connecte avec le compte **`postgres`**, très probablement
  superutilisateur (Q-SEC-002). Toute faille applicative donnerait alors un
  contrôle total du serveur de base de données (ticket #43).
- `seed_users.py --admin <email>` **réinitialise le mot de passe et force le
  rôle `admin`** de n'importe quel compte existant, sans aucune trace
  (`seed_users.py:65-74`).
- Il n'existe aucun journal des actions d'administration.

## 9. CORS et transport

- CORS : `allow_origins` se limite à `localhost:3000`, `localhost:5173` et
  `127.0.0.1:5173`, avec `allow_credentials=True` (`main.py:42-48`). C'est
  correct en développement. **Aucune origine de production n'est configurée**,
  ce qui laisse le déploiement `UNKNOWN / NEEDS VERIFICATION`.
- TLS : HTTP en local ; la configuration de production n'est pas visible.

## 10. Synthèse statique

| | Constats |
|---|---|
| Points positifs confirmés | bcrypt ; aucun SQL brut ; rôle relu en base à chaque requête ; secrets retirés des réponses ; `.env` jamais committé ; montants de facture calculés par le serveur |
| Surexposition de données | `/api/data` ; sérialisation par liste d'exclusion |
| Secrets dans le dépôt | 2 valeurs de repli (clé JWT, mot de passe de la base) ; 3 hash et 1 jeton dans `db.json` |
| Cycle de vie des accès | ni révocation, ni désactivation effective, ni suppression |
| Traçabilité | nulle : aucune table d'audit, aucun journal des décisions |
