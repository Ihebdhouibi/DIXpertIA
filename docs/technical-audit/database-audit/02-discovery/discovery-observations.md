# Registre des observations de la Discovery

> Phase 1 — Discovery · 2026-10-01 · `develop` @ `34453a4`

## Comment lire ce registre

Ces observations **ne sont pas des findings**. Une observation devient une
finding `AUDIT-DB-XXX` (dans `10-findings/`) seulement après la phase qui doit la
prouver ou l'écarter.

Les statuts suivent la règle de la mission :

| Statut | Signification |
|---|---|
| `CONFIRMED` | Fait vérifié : lecture directe du code, sortie d'une commande ou réponse HTTP observée. |
| `SUSPECTED` | Conséquence très probable d'après le code, mais pas encore exécutée ni prouvée. |
| `OBSERVATION` | Constat neutre, dont l'impact reste à qualifier. |
| `NOT VERIFIED` | Vérification impossible pour l'instant (par exemple, serveur indisponible). |

Une observation peut combiner deux statuts. Le fait peut être `CONFIRMED` par
la lecture du code, alors que son effet à l'exécution reste `SUSPECTED`.

---

## A. Architecture de la couche données

### OBS-001 — La base n'est pas la source de vérité de l'application
- **Statut :** CONFIRMED (code)
- **Fait :** le frontend n'appelle que 5 endpoints et jamais `/api/data`. Les
  factures, congés, bulletins, l'équipe et les projets sont initialisés depuis
  `src/data.ts`, puis persistés dans le `localStorage` (`src/App.tsx:74-196`).
- **Impact pressenti :** les données ne sont ni partagées entre utilisateurs, ni
  durables, ni auditables. Les règles serveur ne s'appliquent pas à l'essentiel
  des actions de l'UI.
- **À traiter en :** phase 9 (règles métier) et conclusion de l'audit.

### OBS-002 — Trois représentations incompatibles des mêmes entités
- **Statut :** CONFIRMED (code)
- **Fait :** le frontend (`src/types.ts`) et l'API héritée (`main.py`) parlent
  camelCase anglais. Les modèles `Invoice`, `LeaveRequest` et `Payslip`
  utilisent le snake_case français, avec d'autres clés et d'autres types. Voir
  `application-data-flow.md` § Les trois couches.
- **Lien :** ticket ouvert #37.
- **À traiter en :** phase 3.

### OBS-003 — Aucune migration ; schéma créé par `create_all()`
- **Statut :** CONFIRMED (code)
- **Fait :** `alembic/versions/` est vide. Le schéma est créé par
  `tables.py:33` ou `migrate_data.py:12`. `create_all()` ne modifie jamais une
  table existante.
- **À traiter en :** phase 3. Présence de la table `alembic_version` : `NOT VERIFIED`.

### OBS-004 — Une grande partie du backend est du code mort
- **Statut :** CONFIRMED (code)
- **Fait :**
  - Seul `app/routers/invoicing.py` est monté (`main.py:40`).
  - `auth.py`, `leaves.py`, `payroll.py` et `services.py` ne le sont pas.
  - Ces routers utilisent des attributs inexistants : `User.employee_profile`,
    `hashed_password`, `first_name`.
  - `app/schemas/user.py:5` importe `RoleEnum`, qui n'est pas défini dans
    `app/models/user.py`. Le module est donc impossible à importer.
  - `main.py:393-423` (`POST /api/invoices`) est masqué par la route du router.
- **Impact pressenti :** des règles d'accès écrites mais jamais exécutées, et
  une fausse impression de couverture.
- **À traiter en :** phases 3 et 6.

### OBS-005 — Des entités métier attendues sont absentes du schéma
- **Statut :** CONFIRMED (code)
- **Fait :**
  - Aucune table ni aucun statut pour l'**approbation de facture par la
    comptable**.
  - Aucune table pour les **notifications**, les **projets**, les **demandes
    de documents** ou un **journal d'audit**.
  - Le type de facture (entrante ou sortante) est absent (ticket #40).
- **À traiter en :** phase 9.

## B. Accès, permissions et sécurité

### OBS-006 — Approbation et refus de congé sans authentification
- **Statut :** CONFIRMED (code) · effet à l'exécution SUSPECTED
- **Fait :** `POST /api/leave-requests/{id}/approve` et `/reject`
  (`main.py:354-371`) n'ont aucune dépendance d'authentification.
- **Nuance :** ils écrivent `leave.status` et `leave.rejectionReason`, alors que
  les colonnes s'appellent `statut` et `commentaire_validation`. L'écriture est
  donc probablement **sans effet en base**, mais l'appel répond « approved
  successfully ».
- **À prouver en :** phase 6, par un appel HTTP sans jeton.

### OBS-007 — Insertion anonyme de membres d'équipe
- **Statut :** CONFIRMED (code) · effet à l'exécution SUSPECTED
- **Fait :** `POST /api/team-members` (`main.py:373-391`) n'a aucune
  authentification, et ses champs correspondent au modèle `TeamMember`.
  L'insertion fonctionne donc probablement, pour n'importe qui.
- **À prouver en :** phase 6. Cela nécessite **une écriture en base locale** :
  à demander avant de tester.

### OBS-008 — Création anonyme de demande de congé, qui plante
- **Statut :** CONFIRMED (code) · effet à l'exécution SUSPECTED
- **Fait :** `POST /api/leave-requests` (`main.py:335-352`) n'a aucune
  authentification. `employeeId` est fourni par l'appelant, ce qui permet
  d'usurper n'importe quel employé. Le constructeur reçoit `id` (chaîne),
  `employeeName`, `department`, `type`, `dates` et `duration`, des champs
  absents du modèle : d'où un `TypeError`, donc une erreur 500.
- **À prouver en :** phase 6.

### OBS-009 — `/api/data` expose tout à tout utilisateur connecté
- **Statut :** CONFIRMED (code)
- **Fait :** sans aucun contrôle de rôle, `main.py:492-518` renvoie tous les
  utilisateurs, toutes les demandes de congé, toutes les factures, tous les
  appareils et tous les membres. Seuls les bulletins sont filtrés pour le rôle
  `employee`.
- **Impact pressenti :** un employé lit les factures, donc la donnée comptable,
  et les congés des autres, potentiellement des arrêts maladie.
- **À prouver en :** phase 6, avec un jeton `employee`. Cela nécessite un
  compte employé de test : à demander.

### OBS-010 — Tous les endpoints `devices` plantent probablement
- **Statut :** SUSPECTED
- **Fait :** `main.py:429`, `:435`, `:459` et `:475` lisent `current_user['role']`,
  alors que `get_current_user` renvoie un objet `User`, qui n'est pas indexable.
- **À prouver en :** phase 6. C'est un appel en lecture : `GET /api/devices`.

### OBS-011 — Les comptes désactivés restent utilisables
- **Statut :** CONFIRMED (code) · effet à l'exécution SUSPECTED
- **Fait :** `users.isActive` n'est vérifié ni à la connexion (`main.py:198-206`)
  ni dans les deux `get_current_user`.
- **À prouver en :** phase 6 (nécessite de désactiver un compte de test).

### OBS-012 — Un jeton de réinitialisation sert aussi de jeton de session
- **Statut :** SUSPECTED
- **Fait :** le jeton de reset (`main.py:278`) est signé avec la même clé et
  contient `sub`. Aucun `get_current_user` ne vérifie le claim `purpose`. Il
  permettrait donc d'appeler l'API pendant 1 heure, sans mot de passe.
- **À prouver en :** phase 6.

### OBS-013 — Faiblesses du cycle de vie des secrets d'authentification
- **Statut :** CONFIRMED (code)
- **Fait :**
  - `users.resetToken` est stocké **en clair**.
  - Les jetons de session ne sont pas révoqués après une réinitialisation.
  - Aucune politique de complexité de mot de passe.
  - Le mot de passe provisoire est renvoyé dans la réponse de `POST /api/users`
    (`main.py:268`).
- **À traiter en :** phase 6.

### OBS-014 — Clé de signature JWT de repli codée en dur, à deux endroits
- **Statut :** CONFIRMED (code)
- **Fait :** `main.py:58` et `app/core/config.py:9` utilisent la même valeur de
  repli lorsque `SECRET_KEY` est absente. Cette valeur est publique, puisqu'elle
  est dans le dépôt : n'importe qui pourrait alors forger un jeton admin. En
  local, `SECRET_KEY` est bien définie dans `.env`, générée le 2026-10-01.
- **Nuance :** le risque dépend du déploiement, qui n'est pas visible dans le
  dépôt (`NOT VERIFIED`).

### OBS-015 — `db.json`, versionné, contient des secrets d'authentification
- **Statut :** CONFIRMED
- **Fait :** `db.json`, suivi par git depuis `4cec208`, contient 3 hash bcrypt de
  comptes réels (deux admins, une comptable), ainsi qu'un `resetToken` non vide :
  `SECRET DETECTED — VALUE REDACTED`. Ces valeurs restent dans l'historique git,
  même si le fichier est nettoyé plus tard.
- **À traiter en :** phase 6. Aucune valeur n'a été copiée dans ce dossier.

### OBS-016 — L'application se connecte avec le compte `postgres`
- **Statut :** CONFIRMED (identifiant) · superutilisateur `NOT VERIFIED`
- **Fait :** l'utilisateur déclaré dans `DATABASE_URL` est `postgres`. La valeur
  de repli de `app/core/config.py:8` le code en dur, avec son mot de passe :
  `SECRET DETECTED — VALUE REDACTED`.
- **Lien :** ticket ouvert #43 (RLS et rôle à privilèges minimaux).
- **À prouver en :** phase 6, avec Q-DISC-003.

### OBS-017 — `tables.py` affiche le mot de passe de la base
- **Statut :** CONFIRMED (observé le 2026-10-01)
- **Fait :** `tables.py:28` affiche `settings.DATABASE_URL` en entier, mot de
  passe compris. Il a été masqué lors de l'exécution du 2026-10-01.

### OBS-018 — Données personnelles dans les logs ; énumération par le temps de réponse
- **Statut :** CONFIRMED (logs) · temps de réponse SUSPECTED
- **Fait :** `main.py:197-205` journalise l'e-mail de chaque tentative de
  connexion, et indique si l'échec vient d'un compte inexistant ou d'un mauvais
  mot de passe. Le chemin « compte inexistant » ne calcule aucun bcrypt.

### OBS-019 — Modèle de rôles non contraint
- **Statut :** CONFIRMED (code)
- **Fait :**
  - `users.role` est une chaîne libre.
  - Un rôle `rh` est accepté par le router mais n'existe nulle part ailleurs.
  - `POST /api/users` accepte n'importe quel rôle.
  - Il n'existe aucun endpoint pour changer un rôle, ni pour désactiver ou
    supprimer un compte.

## C. Intégrité et règles métier

### OBS-020 — Création de facture : statut NULL, puis erreur 500 après le commit
- **Statut :** SUSPECTED
- **Fait :**
  - `app/routers/invoicing.py:64-72` ne renseigne pas `statut`, qui reste NULL
    (la colonne est nullable).
  - `InvoiceOut.statut` est typé `InvoiceStatus`, sans être optionnel
    (`app/schemas/invoicing.py:54`). La sérialisation de la réponse échoue donc
    probablement, **après** le `commit` de la ligne 79.
  - Conséquence : la facture est enregistrée mais le client reçoit une erreur
    500. Une nouvelle tentative crée un doublon, avec un numéro différent.
  - Par ailleurs, la **comptable peut créer des factures** : la route autorise
    `accountant`.
- **À prouver en :** phase 8. Cela nécessite une écriture en base locale : à
  demander.

### OBS-021 — La création de compte est probablement cassée aujourd'hui
- **Statut :** SUSPECTED (forte probabilité)
- **Fait :** `main.py:235` calcule `id = USR-{count()+1}`. Avec 4 utilisateurs
  (`USR-001`, `003`, `005`, `006`), cela donne `USR-005`, **déjà pris**, d'où
  une violation de PK et une erreur 500. `seed_users.py:85-95` documente
  précisément ce piège et le contourne. `main.py` ne le fait pas.
- **À prouver en :** phase 8. La tentative échoue sans rien écrire, mais c'est
  une écriture : à demander.

### OBS-022 — Identifiants et numéros générés par `count() + 1`
- **Statut :** CONFIRMED (code)
- **Fait :** c'est le cas des utilisateurs (`main.py:235`), des congés (`:337`),
  des membres d'équipe (`:377`), des factures héritées (`:401`), des appareils
  (`:437`) et des numéros `FA-` (`app/routers/invoicing.py:37`).
- **Impact pressenti :** collisions après une suppression, situations de
  concurrence, numérotation non garantie sans trou (ticket #38).

### OBS-023 — Contraintes d'intégrité absentes ou trop faibles
- **Statut :** CONFIRMED (modèles) · catalogue `NOT VERIFIED`
- **Fait :**
  - Aucune contrainte `CHECK`.
  - Nullables alors qu'ils devraient être obligatoires :
    `leave_requests.employee_id`, `invoices.statut`, `invoices.montant_ht` et
    `montant_ttc`, `invoices.cree_par_id`, `users.role`, `users.hashedPassword`,
    `users.firstName` et `lastName`.
  - Aucune règle `ON DELETE`.

### OBS-024 — Types monétaires et valeurs dérivées
- **Statut :** CONFIRMED (code)
- **Fait :**
  - `devices.price` est un `Float`.
  - `montant_ht` et `montant_ttc` sont stockés **et** recalculables depuis
    `invoice_items`, sans contrôle de cohérence.
  - `insert_invoices.py` insère `ht == ttc` avec une TVA à 0.
  - Il n'y a aucune colonne de devise.

### OBS-025 — Le lien appareil ↔ facture n'existe pas en base
- **Statut :** CONFIRMED (code)
- **Fait :** `deviceIds` n'est pas une colonne de `invoices`, et aucune table de
  liaison n'existe, alors que le ticket #18 est fermé. Le passage d'un appareil
  au statut « Sold » (`main.py:416-420`) se fait dans du code mort.

### OBS-026 — `team_members` duplique `users`, sans lien
- **Statut :** CONFIRMED (code)
- **Fait :** les deux tables ont un nom, un prénom, un e-mail et un rôle, mais
  aucune clé étrangère ne les relie. Un employé peut ainsi exister dans l'une
  sans l'autre, ou avec des valeurs divergentes.

### OBS-027 — Types de dates et d'horodatage hétérogènes
- **Statut :** CONFIRMED (code)
- **Fait :**
  - Les colonnes `DateTime` naïves sont alimentées par `datetime.utcnow`
    (`users`, `devices`).
  - `DateTime(timezone=True)` est alimenté par `func.now()` (`payslips`,
    `leave_requests`).
  - Le frontend manipule des dates en texte (`"Oct 12, 2024"`).

### OBS-028 — Types Pydantic incohérents avec les colonnes
- **Statut :** CONFIRMED (code)
- **Fait :** `PayslipOut.employee_id` et `LeaveRequestOut.employee_id` sont
  typés `int`, alors que les colonnes sont des `VARCHAR` contenant `USR-NNN`
  (`app/schemas/payroll.py:7`, `app/schemas/leaves.py:25`).

### OBS-029 — Deux formats de numéro de facture
- **Statut :** CONFIRMED (code)
- **Fait :** `INV-2024-00N` (frontend, `main.py`, `insert_invoices.py`) et
  `FA-{année}-{NNNN}` (router).

## D. Performance

### OBS-030 — Lectures intégrales, sans pagination ; index de clés étrangères absents des modèles
- **Statut :** CONFIRMED (code) · catalogue `NOT VERIFIED`
- **Fait :**
  - `/api/data` charge **6 tables entières** à chaque appel.
  - `GET /api/invoices` et `GET /api/clients` n'ont ni pagination ni filtre.
  - Aucun modèle ne déclare d'index sur ses colonnes de clé étrangère, et
    PostgreSQL n'en crée pas automatiquement.
- **À traiter en :** phase 7.

## E. Exploitation et qualité

### OBS-031 — Le `Dockerfile` ne peut pas démarrer l'application
- **Statut :** CONFIRMED (code)
- **Fait :** il lance `uvicorn app.main:app`, alors que le module est `main:app`.

### OBS-032 — Aucun test automatisé
- **Statut :** CONFIRMED
- **Fait :** aucun fichier de test n'est suivi par git, et aucun framework de
  test n'est déclaré.

### OBS-033 — L'UI permet à tout rôle de basculer en vue admin ; jeton dans le `localStorage`
- **Statut :** CONFIRMED (code)
- **Fait :** voir `authentication-and-authorization.md` § 4. Le jeton est dans le
  `localStorage`, donc lisible par n'importe quel script injecté (XSS).

### OBS-034 — Création de compte : e-mail envoyé après le commit, mot de passe dans la réponse
- **Statut :** CONFIRMED (code)
- **Fait :** si l'envoi SMTP échoue (`main.py:262`, l'erreur est simplement
  journalisée), le compte existe, et son mot de passe provisoire n'existe plus
  que dans la réponse HTTP et dans une notification éphémère de l'UI.

---

## Récapitulatif

| Statut dominant | Nombre |
|---|---|
| CONFIRMED (code ou observation) | 26 |
| SUSPECTED à l'exécution | 8 (OBS-006, 007, 008, 010, 011, 012, 020, 021) |
| Dépend du catalogue PostgreSQL (`NOT VERIFIED`) | 4 (OBS-003, 016, 023, 030) |

Les tests qui **écrivent** dans la base locale (OBS-007, 011, 020, 021) ne
seront lancés qu'avec ton accord explicite.

---

## Verdicts après preuves (2026-10-02)

Toutes les observations ont été confrontées à la base et à l'API réelles.
Preuves : `11-evidence/`, ainsi que `06-security/security-runtime-tests.md`,
`08-data-integrity/data-integrity-results.md`,
`07-performance/explain-plans-analysis.md` et `04-models/orm-vs-database.md`.

| Obs. | Verdict | Preuve décisive |
|---|---|---|
| OBS-001 | **CONFIRMED** | inventaire des `fetch(` dans `src/` (5 appels, jamais `/api/data`) |
| OBS-002 | **CONFIRMED** | T-A03, T-B05, T-B09 (divergences ORM ↔ API à l'exécution) |
| OBS-003 | **CONFIRMED** | Q-DISC-009 : pas de table `alembic_version` |
| OBS-004 | **CONFIRMED** | `openapi.json` : seul le router `invoicing` est exposé |
| OBS-005 | **CONFIRMED** | Q-DISC-005 : 9 tables, aucune pour l'approbation, les notifications, les projets, les documents ou l'audit |
| OBS-006 | **CONFIRMED** | T-A01, T-A02 (404 sans jeton) ; T-B09 (200 sans jeton, statut inchangé en base) |
| OBS-007 | **CONFIRMED** | T-B08 : 201 sans jeton |
| OBS-008 | **CONFIRMED** | T-A03 : 500, `TypeError … 'employeeId'` |
| OBS-009 | **CONFIRMED** | T-B01 : un employé reçoit les 7 comptes ; T-A06 : les secrets sont bien filtrés |
| OBS-010 | **CONFIRMED** | T-A05 : 500, `'User' object is not subscriptable` |
| OBS-011 | **CONFIRMED** | T-B04 : un compte inactif obtient un jeton |
| OBS-012 | **CONFIRMED** | T-B07 : le `resetToken` ouvre `/api/data` |
| OBS-013 | **CONFIRMED** | code ; `users.resetToken` en `varchar` clair (Q-SCH-001) |
| OBS-014 | **CONFIRMED** (code) · exploitation **REFUTED en local** | T-A08 : 401, car `SECRET_KEY` est définie localement |
| OBS-015 | **CONFIRMED** | structure de `db.json` (valeurs non lues) |
| OBS-016 | **CONFIRMED** | Q-DISC-003, Q-SEC-002 : `postgres`, `rolsuper` et `rolbypassrls` |
| OBS-017 | **CONFIRMED** | sortie de `tables.py` du 2026-10-01 |
| OBS-018 | **CONFIRMED** pour le temps de réponse · **latent** pour les logs | T-A09 : 24 ms contre 292 ms. Le logger est au niveau WARNING : les `log.info` contenant l'e-mail ne sont pas écrits aujourd'hui. |
| OBS-019 | **CONFIRMED** | code ; sonde P-21 (rôle `superadmin` accepté) |
| OBS-020 | **CONFIRMED** | T-B05 : 2 × 500, 2 factures au statut NULL en base |
| OBS-021 | **CONFIRMED** | Q-INT-006 (`USR-005` déjà pris) ; T-A07 (500, `users_pkey`) |
| OBS-022 | **CONFIRMED** | code ; collision démontrée par T-A07 |
| OBS-023 | **CONFIRMED** | Q-DISC-006 (0 CHECK) ; Q-SCH-001 ; 26 sondes acceptées |
| OBS-024 | **CONFIRMED** | Q-SCH-011 (`devices.price` en `double precision`) ; P-07 |
| OBS-025 | **CONFIRMED** | Q-SCH-001 (aucune colonne ni table de liaison) |
| OBS-026 | **CONFIRMED** | Q-SCH-004 (aucune FK sur `team_members`) |
| OBS-027 | **CONFIRMED** | Q-SCH-010 (`date`, `timestamptz` et `timestamp` naïf coexistent) |
| OBS-028 | **CONFIRMED** | code |
| OBS-029 | **CONFIRMED** | T-B05 a produit `FA-2026-0001`, alors que le frontend et `insert_invoices.py` utilisent `INV-2024-00N` |
| OBS-030 | **CONFIRMED** | Q-SCH-007 (5 FK non indexées) ; Q-PERF-013 à 016 (aucun index utilisable) |
| OBS-031 | **CONFIRMED** (code) · exécution `NOT VERIFIED` | Docker n'est pas installé sur le poste |
| OBS-032 | **CONFIRMED** | `git ls-files` |
| OBS-033 | **CONFIRMED** | code |
| OBS-034 | **CONFIRMED** | code |

### Nouveaux constats issus de l'exécution

| Obs. | Statut | Constat | Preuve |
|---|---|---|---|
| **OBS-035** | **CONFIRMED** | Les erreurs d'intégrité écrivent les paramètres SQL dans les logs, **e-mail et hash bcrypt du mot de passe provisoire** compris, faute de `hide_parameters=True`. Avec OBS-021, cela se produit à **chaque** tentative de création de compte. | log du backend, T-A07 |
| **OBS-036** | **CONFIRMED** | `UNIQUE (employee_id, periode)` porte sur une **date** : deux bulletins dans le **même mois** sont acceptés. | sonde P-20 |
| **OBS-037** | **CONFIRMED** | **9 index redondants** (`ix_<table>_id`, en double de chaque PK). PostgreSQL utilise même l'index en double à la place de la PK. | Q-SCH-006, Q-PERF-004 |
| **OBS-038** | **CONFIRMED** | Avec la collation `French_Tunisia.1252`, l'index sur `invoices.numero` ne sert pas le `LIKE 'FA-…%'` de la numérotation : il est parcouru en entier. | Q-DISC-002, Q-PERF-017 |
| **OBS-039** | **CONFIRMED** | Les valeurs par défaut n'existent que côté Python : une insertion hors ORM produit des NULL, dont `isActive` NULL. | Q-SCH-001, sonde P-24 |
| **OBS-040** | **CONFIRMED** | Serveur PostgreSQL : `log_connections`, `log_disconnections` et `log_statement` désactivés ; `statement_timeout` et `idle_in_transaction_session_timeout` à 0 ; `ssl` off ; `listen_addresses = *`, compensé par `pg_hba.conf`, qui n'autorise que localhost. | Q-SEC-006, Q-SEC-007 |
| **OBS-041** | OBSERVATION | Les ENUM ont deux vocabulaires : la base stocke `BROUILLON`, l'API expose `brouillon`. L'hypothèse d'un échec de `insert_invoices.py` est **REFUTED** : SQLAlchemy convertit la valeur. | Q-SCH-009, sonde de liaison |

**Bilan :** sur 41 observations, **40 sont confirmées** (OBS-001 à 040), en tout ou en partie, et OBS-041 reste une OBSERVATION.
Aucune n'est réfutée sur le fond. Deux points sont réfutés ou nuancés dans
leur **portée** :
- OBS-014, dont l'exploitation est impossible en local ;
- OBS-018, dont la partie « logs » est latente.

Une hypothèse annexe a aussi été réfutée : l'échec d'`insert_invoices.py`, dans
OBS-041.
