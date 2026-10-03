# Flux de données applicatif

> Phase 1 — Discovery · 2026-10-01 · `develop` @ `34453a4`

## Constat principal

**La base de données n'est pas la source de vérité de l'application.**

Le frontend appelle exactement **5 endpoints** de l'API. Recherche exhaustive
de `fetch(` dans `src/` :

| Appel | Fichier | Usage |
|---|---|---|
| `POST /api/login` | `src/App.tsx:204` | connexion |
| `POST /api/users` | `src/App.tsx:438` | création de compte par un admin |
| `POST /api/forgot-password` | `src/components/ForgotPassword.tsx:24` | demande de réinitialisation |
| `POST /api/reset-password` | `src/components/ResetPassword.tsx:45` | réinitialisation |
| `GET /api/invoices/{id}/download` | `src/components/InvoicesView.tsx:41` | PDF d'une facture |

**`GET /api/data` n'est jamais appelé**, alors que c'est le seul endpoint qui
renvoie bulletins, congés, équipe, factures, utilisateurs et appareils.

Toutes les autres données sont :
1. initialisées à partir de **données fictives** codées en dur dans
   `src/data.ts` (`initialPayslips`, `initialLeaveRequests`,
   `initialTeamMembers`, `initialInvoices`, `initialProjects`) ;
2. modifiées **uniquement dans l'état React** ;
3. persistées dans le **`localStorage` du navigateur** (`src/App.tsx:166-196`).

Conséquence directe, à confirmer en phase 9 (règles métier) : la comptable et
l'administrateur ne voient **pas les mêmes factures**. Chacun voit les données
de son propre navigateur.

## Flux par fonctionnalité

Légende des colonnes :
- **Source UI** : d'où l'interface tire ses données.
- **Endpoint** : route existante côté serveur.
- **Fonctionne ?** : le comportement prévisible d'après le code. Les essais
  réels sont prévus en phase 6 ; tant qu'ils n'ont pas eu lieu, le statut est
  `SUSPECTED`.

| Fonctionnalité | Source UI | Écriture UI | Endpoint serveur | Table | Fonctionne ? |
|---|---|---|---|---|---|
| Connexion | API | — | `POST /api/login` (`main.py:195`) | `users` | ✅ CONFIRMED (testé en HTTP le 2026-10-01) |
| Création de compte | API | API + `localStorage` `dixpertia_users` | `POST /api/users` (`main.py:224`) | `users` | ❌ SUSPECTED : génère l'id `USR-{count+1}` = `USR-005`, **déjà pris** par un compte importé → violation de PK |
| Mot de passe oublié / reset | API | API | `main.py:271`, `main.py:303` | `users.resetToken` | SUSPECTED OK (SMTP non configuré en local) |
| Liste des factures | `localStorage` / `data.ts` | `localStorage` | `GET /api/invoices` (router) | `invoices` | ⚠️ endpoint existant, **non appelé** |
| Création de facture | `localStorage` | `localStorage` (`App.tsx:340`) | `POST /api/invoices` (router, `app/routers/invoicing.py:55`) | `invoices`, `invoice_items` | ⚠️ endpoint non appelé ; voir OBS-020 |
| PDF de facture | API | — | `GET /api/invoices/{numero}/download` | `invoices`, `invoice_items`, `clients` | SUSPECTED : fonctionne seulement si le `numero` en base coïncide avec l'`id` fictif du `localStorage` (`INV-2024-00N`) |
| Approbation de facture par la comptable | — | — | **aucun** | aucune colonne ni statut d'approbation | ❌ CONFIRMED : absente côté serveur **et** côté UI (`InvoicesView.tsx` n'a aucune action d'approbation ou de refus) |
| Filtres comptables (jour, mois, client) | — | — | **aucun** paramètre de filtre sur `GET /api/invoices` | — | ❌ CONFIRMED : l'UI filtre seulement par statut et par recherche texte (`InvoicesView.tsx:99-103`) |
| Notification à la comptable des factures en attente | — | — | **aucun** | aucune table | ❌ CONFIRMED : absente |
| Clients | — | — | `GET/POST /api/clients` | `clients` | ⚠️ endpoints non appelés, aucune UI |
| Bulletins de paie | `localStorage` / `data.ts` | — | **aucun monté** (`main.py:35-39`) ; lecture via `/api/data` seulement | `payslips` | ❌ table jamais lue par l'UI |
| Demandes de congés | `localStorage` / `data.ts` | `localStorage` (`App.tsx:270`) | `POST /api/leave-requests` (`main.py:335`) | `leave_requests` | ❌ SUSPECTED : le constructeur reçoit des champs camelCase (`employeeName`, `dates`…) **absents du modèle** → `TypeError` |
| Approuver / refuser un congé | `localStorage` | `localStorage` (`App.tsx:292`, `:309`) | `main.py:354`, `main.py:363` | `leave_requests` | ❌ SUSPECTED : écrit `leave.status` alors que la colonne s'appelle `statut` → aucune écriture effective |
| Équipe | `localStorage` / `data.ts` | `localStorage` (`App.tsx:327`) | `POST /api/team-members` (`main.py:373`) | `team_members` | ⚠️ endpoint compatible avec le modèle, mais **non appelé** |
| Appareils | — | — | `GET/POST/PUT/DELETE /api/devices` (`main.py:427-482`) | `devices` | ❌ SUSPECTED : `current_user['role']` sur un objet `User` → `TypeError` sur chaque appel |
| Projets | `localStorage` / `data.ts` | `localStorage` (`App.tsx:355-399`) | **aucun** | **aucune table** | entité inexistante côté serveur |
| Notifications | `localStorage` | `localStorage` | **aucun** | **aucune table** | entité inexistante côté serveur |
| Services (site vitrine) | `Homepage.tsx` : contenu statique, aucun `fetch` (CONFIRMED) | — | router `services` **non monté** | `services` | table jamais utilisée |
| Demandes de documents par les employés | — | — | **aucun** | **aucune table** | fonctionnalité citée dans la mission, **absente** |

## Les trois couches ne décrivent pas les mêmes entités

Exemple : la facture.

| Couche | Fichier | Identifiant | Client | Montant | Dates | Statut | Lignes |
|---|---|---|---|---|---|---|---|
| Frontend | `src/types.ts:51` | `id: string` (`INV-2024-001`) | `client: string` (texte libre) | `amount` | `dateIssued`, `dueDate` (texte `"Oct 12, 2024"`) | `Draft/Sent/Paid/Overdue` | `items[]` avec `description, qty, price, total` |
| API héritée | `main.py:159-168` | `id: str` | `client: str` | `amount: float` | texte | `'Sent'` | `items` JSON + `deviceIds` |
| API du router | `app/schemas/invoicing.py:40-55` | `id: int` + `numero` | `client_id: int` (FK) | `montant_ht`, `montant_ttc` calculés | `date` | `brouillon/envoyee/payee/en_retard/annulee` | table `invoice_items` |
| Base | `app/models/invoicing.py:34-49` | `id` INTEGER + `numero` UNIQUE | `client_id` FK | `NUMERIC(10,2)` | `DATE` | ENUM | table `invoice_items` |

Le frontend et le router n'ont **aucun champ en commun**, à part l'idée de
« lignes ». Le statut `annulee` n'existe pas côté frontend. Le statut `Overdue`
est stocké côté frontend, alors que c'est une valeur dérivable de
`date_echeance`.

Ce même décalage existe pour les congés et pour les bulletins de paie : voir
`04-models/` (Phase 3).

## Scripts de données

| Script | Compatible avec les modèles actuels ? | Effet |
|---|---|---|
| `tables.py` | ✅ | `create_all()` des 9 tables |
| `seed_users.py` | ✅ | importe les 3 comptes de `db.json`, crée ou réinitialise un admin |
| `insert_invoices.py` | ✅ (lecture du code) | 5 clients + 5 factures de démonstration ; numéros `INV-2024-00N`, TVA à 0 |
| `migrate_data.py` | ❌ | utilise les champs camelCase sur `Payslip`, `LeaveRequest` et `Invoice` ; plante sur la boucle des bulletins (constat de la PR #35) |

Deux formats de numéro de facture coexistent : `INV-2024-00N`
(`insert_invoices.py`, frontend, `main.py:401`) et `FA-{année}-{NNNN}`
(`app/routers/invoicing.py:38`).
