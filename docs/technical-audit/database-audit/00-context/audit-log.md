# Journal d'audit

## 2026-10-01

### Action
Initialisation de l'audit et création de la structure `docs/technical-audit/database-audit/`.

### Objectif
Disposer d'un dossier de référence unique pour l'audit.

### Résultat
17 dossiers créés, dont les sous-dossiers de `11-evidence/` (`schema`,
`sql-results`, `logs`, `explain-plans`, `api-tests`, `data-integrity`,
`code-references`) et de `01-requests/` (`sql`, `scripts`).

Le dossier `docs/` est déjà exclu du watcher Vite (`vite.config.ts:28`) et des
hooks de reformatage (`.pre-commit-config.yaml:39`) : il n'a aucun effet sur
l'application.

### Fichiers
`README.md`, `00-context/scope-and-method.md`

---

### Action
Phase 1 — Discovery : lecture intégrale du backend.

### Objectif
Comprendre l'existant avant toute conclusion : stack, ORM, modèles, routes,
authentification, autorisation et scripts de données.

### Résultat
1 977 lignes lues, réparties ainsi :
- `main.py` ;
- `app/core/*`, `app/models/*`, `app/routers/*`, `app/schemas/*` ;
- les scripts `tables.py`, `seed_users.py`, `migrate_data.py` et `insert_invoices.py` ;
- `alembic/env.py`, `alembic.ini` ;
- `Dockerfile`, `server.ts`, `pyproject.toml`, `.pre-commit-config.yaml`.

`db.json` a été inspecté **pour sa structure uniquement**, sans lire ni
recopier aucune valeur sensible.

Constats principaux :
- 9 modèles ORM, 1 router monté sur 5, aucune migration ;
- deux piles d'authentification ;
- plusieurs endpoints sans authentification ;
- des modèles incompatibles avec l'API.

### Fichiers
`02-discovery/technology-stack.md`, `project-structure.md`,
`database-overview.md`, `authentication-and-authorization.md`

### Findings
Aucune finding à ce stade : 34 observations sont consignées dans
`02-discovery/discovery-observations.md`.

---

### Action
Phase 1 — Discovery : cartographie du frontend en tant que consommateur de données.

### Objectif
Établir quelles fonctionnalités utilisent réellement la base.

### Résultat
Une recherche exhaustive des `fetch(` dans `src/` relève **5 appels API**.
`/api/data` n'est jamais appelé. Toutes les données métier proviennent de
`src/data.ts` et du `localStorage`.

Le bouton « Switch to Admin View » est affiché pour tous les rôles.

La vue Factures ne propose ni approbation ni filtre par jour, mois ou client.

### Fichiers
`02-discovery/application-data-flow.md`

### Findings
OBS-001, OBS-005, OBS-033 (observations)

---

### Action
Phase 1 — Discovery : préparation et première tentative d'interrogation du
catalogue PostgreSQL.

### Objectif
Confirmer la version, le rôle connecté, les tables, les contraintes, les index,
les ENUM, l'éventuelle table `alembic_version` et la RLS.

### Résultat
- Les requêtes sont prêtes : `01-requests/sql/01-discovery-overview.sql`,
  11 requêtes (Q-DISC-001 à Q-DISC-011).
- L'exécuteur en lecture seule est prêt : `01-requests/scripts/run_readonly.py`.
- **L'exécution a échoué.** Le serveur PostgreSQL refuse toutes les connexions
  avec le message : « n'a pas pu lancer le nouveau processus fils pour la
  connexion : Bad file descriptor », puis « server closed the connection
  unexpectedly ».
- **Diagnostic :** l'échec est reproduit en IPv4 et en IPv6, depuis Git Bash et
  depuis PowerShell, avec et sans l'option lecture seule. Le service
  `postgresql-x64-17` est pourtant `Running` (9 processus, port 5432 en écoute,
  démarré le 2026-10-01 à 12:03:41). La même connexion fonctionnait plus tôt le
  même jour.
- **Hypothèse :** l'état du serveur est dégradé, et un redémarrage du service est
  nécessaire. Cette action système demande les droits administrateur : elle est
  **demandée à Abir**.

### Fichiers
`01-requests/sql/01-discovery-overview.sql`, `01-requests/scripts/run_readonly.py`

### Findings
Aucune. Les éléments qui dépendent du catalogue sont marqués `NOT VERIFIED`
dans `database-overview.md`.

---

### Action
Le serveur PostgreSQL a été redémarré par Abir. Nouvelle tentative de
connexion.

### Résultat
**Échec persistant.** Depuis pgAdmin, Abir obtient « connection timeout
expired » en IPv4 et en IPv6. Le redémarrage du service ne suffit donc pas.

Pistes transmises à Abir, par ordre de probabilité :
1. un logiciel tiers (antivirus, VPN ou proxy) qui interfère avec le passage de
   la connexion au processus fils ;
2. une pile Winsock dans un état dégradé (`netsh winsock reset`) ;
3. une mise à jour Windows appliquée au démarrage de 12:03.

Abir va redémarrer son poste. Le diagnostic en lecture seule (journal
PostgreSQL, `netsh winsock show catalog`) n'a **pas** été exécuté : la commande
a été interrompue par Abir, et elle ne sera relancée qu'avec son
accord.

### Décisions d'Abir
- **Tests avec écriture en base locale : autorisés.** Cela couvre OBS-007, 011,
  020 et 021, ainsi que la création d'un compte employé de test.
- **Ticket parent : non publié.** L'audit continue jusqu'à vérification
  complète ; les tickets seront traités ensuite, avec des preuves concrètes.

---

### Action
Préparation de toutes les requêtes SQL des phases suivantes, pendant
l'indisponibilité du serveur.

### Objectif
Pouvoir tout exécuter en une seule commande dès le rétablissement du serveur.

### Résultat
4 nouveaux fichiers SQL, soit 64 requêtes au total avec la Discovery :
- `02-schema-inventory.sql` (13 requêtes) ;
- `03-data-integrity.sql` (20 requêtes) ;
- `04-performance.sql` (12 requêtes) ;
- `05-security.sql` (8 requêtes).

Deux corrections ont été faites avant toute exécution :
- **Q-SCH-006** : mauvais argument passé à `pg_get_indexdef`, et `GROUP BY`
  sur `int2vector`.
- **Q-INT-004** : la requête renvoyait des e-mails, donc des données
  personnelles. Elle ne renvoie plus que des comptages.

Nouvelle hypothèse à trancher (Q-SCH-009) : SQLAlchemy stockerait les **noms**
des membres d'ENUM, ce qui ferait échouer `insert_invoices.py`.

### Fichiers
`01-requests/sql/02-*.sql` à `05-*.sql`, `01-requests/README.md`

---

### Action
Phase 3 (côté code) — correspondance frontend ↔ API ↔ schémas ↔ ORM, entité par entité.

### Résultat
- 11 entités comparées champ par champ.
- **Une seule entité, `TeamMember`, est cohérente de bout en bout.**
- Facture, congé et bulletin : **aucun champ commun** entre l'interface et la base.
- Nouveaux faits établis :
  - le type frontend `Payslip` **n'a aucun lien vers un employé** ;
  - le frontend ne connaît pas l'entité Appareil ;
  - le type de congé `Personal Day` n'a pas d'équivalent en base ;
  - les dates de congé sont saisies en texte libre ;
  - l'UI ignore la TVA ;
  - `isVerified` n'est modifié par aucun endpoint.
- 11 règles métier identifiées qui ne vivent que dans le code, alors qu'une
  contrainte de base serait pertinente.
- 7 constats propres à l'ORM, dont la cascade appliquée par l'ORM seulement, le
  stockage des ENUM par nom (hypothèse) et les valeurs par défaut côté Python.
- Deux erreurs de rédaction ont été corrigées après vérification : un numéro
  de ligne, et la portée de `isVerified`.

### Fichiers
`04-models/orm-api-frontend-mapping.md`

---

### Action
Phase 4 — relations et ERD logique.

### Résultat
- ERD Mermaid de l'état actuel : 9 tables, 6 FK.
- **3 tables isolées** : `team_members`, `devices` et `services`.
- 6 relations analysées (cardinalité, optionalité, suppression, orphelins,
  ORM). 2 ont une optionalité erronée : un congé sans employé et une facture
  sans auteur.
- **6 relations attendues par le métier sont absentes**, dont l'entité employé
  distincte du compte (prévue par les routers morts, jamais créée), le lien
  facture ↔ appareil et la trace d'approbation.
- Aucun diagramme préexistant n'était à comparer.

### Fichiers
`05-relations/relations-and-erd.md`

---

### Action
Phases 6, 7, 8 et 9 — analyses statiques, sans la base.

### Résultat
- **Phase 8, transactions et concurrence**
  (`08-data-integrity/transactions-and-concurrency.md`) : 8 opérations
  critiques analysées.
  - Aucun verrou, aucun rollback explicite, isolation `READ COMMITTED`.
  - Une seule opération est correctement atomique : la facture avec ses lignes.
  - Cause racine commune : des identifiants générés par `count() + 1`.
  - Nouveau constat : la suppression d'un appareil bloque les créations
    suivantes.
- **Phase 9, règles métier** (`09-business-rules/business-rules-matrix.md`) :
  36 règles évaluées.
  - **6 sont protégées côté serveur**, 15 sont enfreignables par un appel direct
    à l'API, et 5 fonctionnalités n'existent pas.
  - Nouveau constat majeur : **la modification et la suppression d'un compte
    dans l'UI sont locales seulement**. Un compte « supprimé » garde son accès
    (`App.tsx:485-493`).
- **Phase 6, sécurité statique** (`06-security/security-static-analysis.md`) :
  - **Aucun SQL brut** dans le code : risque d'injection faible (point positif).
  - Aucun `.env` dans l'historique git.
  - Sérialisation par liste d'exclusion : toute nouvelle colonne sensible
    serait exposée par défaut.
  - 2 valeurs de repli secrètes et les secrets de `db.json` (valeurs masquées).
- **Phase 7, performance statique** (`07-performance/performance-static-analysis.md`) :
  - une requête N+1 sur la liste des factures ;
  - `/api/data` lit 6 tables entières ;
  - aucune pagination ;
  - aucun index sur les FK ni sur `date_emission`.

### Corrections de rédaction
Les numéros de ligne cités pour `app/core/config.py` étaient décalés d'un : la
valeur de repli de `DATABASE_URL` est à la ligne 8, celle de `SECRET_KEY` à la
ligne 9. Les 4 occurrences ont été corrigées. La synthèse de la matrice des
règles a aussi été recomptée (36 règles, 6 protégées).

---

### Action
Préparation des tests d'exécution de l'API.

### Résultat
`01-requests/scripts/run_api_tests.py` : 20 tests en deux parties. La partie A
n'écrit rien. La partie B crée des données `AUDIT-TEST`, comme autorisé.

Le script se compile. ruff signale 13 points, dont des `print` (T201) attendus
dans un script en ligne de commande. Les autres points n'ont pas encore été lus.

---

### Action
**Point de reprise** avant une interruption du travail.

### Résultat
Note de reprise interne, non versionnée : l'état des phases, le blocage, les
commandes de reprise, les hypothèses à trancher et les décisions déjà prises.
Les commandes de reprise sont reprises dans `01-requests/README.md`.

---

### Action
Préparation du ticket parent de l'audit.

### Résultat
Brouillon rédigé : `13-tickets/TICKET-DB-000-parent-audit.md`. Il est en
anglais, parce qu'il est destiné à GitHub. **Il n'a pas été publié** : la
publication attend un accord explicite.

## 2026-10-02

### Action
Reprise de l'audit. Le serveur PostgreSQL est rétabli (connexion vérifiée :
PostgreSQL 17.11, 4 utilisateurs). `develop` est inchangé à `34453a4`.

---

### Action
Exécution des 64 requêtes en lecture seule, puis de 5 sondes d'utilisabilité
des index (Q-PERF-013 à 017).

### Résultat
69 requêtes, **0 erreur**. Lecture seule confirmée par le serveur.
- Rôle `postgres` superutilisateur, avec `bypassrls`.
- Aucune migration appliquée.
- 0 CHECK, 0 RLS, 0 trigger.
- 6 FK, toutes en `NO ACTION`, dont 5 non indexées.
- 9 index redondants.
- ENUM stockés par nom.
- Collation non-C, qui rend l'index de `numero` inutile pour la numérotation.
- Aucun index utilisable pour le tri des factures par date, ni pour les
  filtres par client ou par mois.

### Fichiers
`11-evidence/schema/*`, `11-evidence/data-integrity/03-*`,
`11-evidence/explain-plans/*`, `11-evidence/sql-results/*`

---

### Action
Sondage des contraintes (`run_constraint_probe.py`) : 30 écritures invalides,
dans une transaction toujours annulée.

### Résultat
**26 sur 30 sont acceptées** ; les 4 refus sont les 4 contraintes existantes.
**0 ligne résiduelle**, vérifié après le rollback.
- Nouveau constat : deux bulletins sont acceptés pour un même mois (OBS-036).
- **Hypothèse réfutée :** `insert_invoices.py` n'échoue pas, car SQLAlchemy
  convertit les valeurs d'ENUM.

---

### Action
Tests d'exécution de l'API (`run_api_tests.py`).

### Incident et correction
**Premier passage**
- T-A07 a renvoyé 422 et la partie B a été interrompue. Cause : le domaine
  réservé `.invalid` choisi pour les comptes de test est rejeté par `EmailStr`.
  Erreur de conception du jeu de test.
- Avant de s'interrompre, la partie B avait créé 3 comptes `AUDIT-TEST`
  (`USR-901` à `903`). Cela changeait la précondition de T-A07.

**Correction**
- Domaine `audit-test.example.com` (RFC 2606, jamais délivré).
- Mes 3 comptes de test ont été renumérotés en `USR-008`, `009` et `010` ;
  aucune autre table ne les référençait, ce qui a été vérifié. T-A07 tombe ainsi
  à nouveau sur un id existant.
- La précondition naturelle (4 comptes, `USR-005` déjà pris) reste prouvée par
  Q-INT-006.

### Résultat
**12 défauts confirmés, 4 contrôles efficaces et 1 risque réfuté pour
l'environnement local** (T-A08). Les 6 causes d'erreur 500 ont été vérifiées
une par une dans le log du backend.

Nouveau constat : **les erreurs d'intégrité écrivent dans les logs l'e-mail et
le hash du mot de passe provisoire** (OBS-035).

Données créées, toutes marquées `AUDIT-TEST`, rien n'a été supprimé :
- 3 comptes ;
- 1 client ;
- 2 factures (`FA-2026-0001` et `0002`, statut NULL) et leurs lignes ;
- 1 membre d'équipe (`TM-00001`) ;
- 1 demande de congé (id 7).

### Fichiers
`06-security/security-runtime-tests.md`, `11-evidence/api-tests/api-tests.results.md`

---

### Action
Consolidation des résultats.

### Résultat
- `08-data-integrity/data-integrity-results.md`
- `07-performance/explain-plans-analysis.md`
- `04-models/orm-vs-database.md`
- `02-discovery/database-overview.md` : les mentions `NOT VERIFIED` sont
  remplacées par les valeurs observées.
- Verdicts ajoutés au registre des observations : **40 confirmées sur 41**, et
  6 nouvelles observations (OBS-036 à 041).

### Corrections de rédaction
- Nombre de défauts confirmés : 12, et non 13.
- Nombre de colonnes camelCase dans `users` : 9, et non 10.
- Date non vérifiée attribuée à la PR #35, retirée.
- Nombre d'observations confirmées : 40, et non 39.

---

### Action
Phases 10 à 14 : findings, recommandations, tickets, rapport final.

### Résultat
- **24 findings** (`10-findings/`) au format imposé, avec la sévérité justifiée
  par les critères de la mission : **1 CRITICAL, 10 HIGH, 5 MEDIUM, 8 LOW**.
  Chaque finding est CONFIRMED et cite ses preuves. Le contrôle par lecture des
  24 fiches redonne exactement ces nombres.
- **Plan de remédiation** en 5 phases, ordonné par les dépendances techniques
  (`12-recommendations/remediation-plan.md`). Il inclut 8 décisions métier
  préalables et une contrainte d'ordonnancement critique : DB-002 doit passer
  avant DB-005.
- **14 tickets + 1 parent** (`13-tickets/`). Ce sont des brouillons en anglais,
  **non publiés**. Les 24 findings sont couvertes, et 3 recoupements sont
  signalés : #37, #38/#39 et #43.
- **Rapport final** (`14-final-report/`). Verdict : la couche données n'est pas
  prête en l'état, elle est réparable, et les phases 0 à 2 (10 tickets)
  suffisent à la rendre apte à la suite.
- **Preuve conservée :** le log du backend, qui se trouvait dans un fichier
  temporaire, a été copié et masqué dans `11-evidence/logs/`, avant sa
  disparition.

### Corrections de rédaction
- AUDIT-DB-006 : 14 dépendances directes, et non 19.
- Rapport final : 4 findings HIGH de catégorie sécurité, et non 5.

### Données laissées en base locale (AUDIT-TEST, non supprimées)
- 3 comptes ;
- 1 client ;
- 2 factures et leurs lignes ;
- 1 membre d'équipe ;
- 1 demande de congé.

---

### Action
Contrôle final des secrets sur l'ensemble du dossier d'audit.

### Résultat
- Recherche des hash bcrypt, des jetons JWT, de la `SECRET_KEY` et du mot de
  passe du `.env`, ainsi que de la clé et du mot de passe de repli du code.
- **1 occurrence trouvée et corrigée.** La valeur de repli de `SECRET_KEY`
  avait été recopiée le 2026-10-01 dans
  `02-discovery/authentication-and-authorization.md` (ligne 58). Elle est
  maintenant remplacée par `SECRET DETECTED — VALUE REDACTED`. La valeur était
  déjà publique dans le dépôt, mais sa copie contrevenait à la règle de l'audit.
- Nouveau contrôle : **0 occurrence**.
- Dépôt git : seuls `design/` et `docs/technical-audit/` sont non suivis.
  **Aucun fichier du code n'a été modifié pendant l'audit.**

## 2026-10-03

### Action
Préparation du dossier à sa publication dans le dépôt (validée par Iheb, documentation en français).

### Résultat
- **Conformité CI :**
  - `ruff check .` passe sur tout le dépôt ;
  - 9 lignes trop longues ont été corrigées dans `run_api_tests.py` ;
  - deux exemptions commentées ont été ajoutées dans `pyproject.toml` :
    `T201` pour les scripts d'audit, comme pour les scripts existants du
    dépôt, et `E501` pour la seule table de requêtes SQL de
    `run_constraint_probe.py`.
- **Données personnelles :** l'e-mail de l'admin n'a plus de valeur par défaut
  dans `run_api_tests.py` ; il est fourni par `AUDIT_ADMIN_EMAIL`.
- **Fichiers internes :** la note de reprise interne est exclue du dépôt, et
  ses deux renvois pointent désormais vers `01-requests/README.md`.
  `__pycache__/` est déjà ignoré par le `.gitignore`.
- **Formulations :** les tournures propres à l'échange de travail sont
  remplacées par des tournures neutres ou nominatives (« Abir »). Les mentions
  « dossier local, non versionné » sont mises à jour.
- **Contrôle final sur les 80 fichiers à committer :** 0 secret, 0 hash, 0 jeton,
  0 e-mail réel ; tous les hooks pre-commit passent.

### Hors périmètre de cette préparation
`run_api_tests.py` a été modifié (mise en forme, e-mail obligatoire), mais n'a
pas été rejoué : la compilation et ruff passent. Il sera rejoué comme preuve
d'acceptation des tickets de la phase 0.
