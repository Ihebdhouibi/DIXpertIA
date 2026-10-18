# Vue d'ensemble de la base de données

> Phase 1 — Discovery · 2026-10-01
>
> **Mise à jour du 2026-10-02.** Le document avait d'abord été rédigé à partir
> des modèles, pendant que le serveur était indisponible. Les éléments du
> catalogue ont été vérifiés le 2026-10-02 (preuves dans
> `11-evidence/schema/`), et les mentions `NOT VERIFIED` ont été remplacées par
> les valeurs observées.

## Identification

| Élément | Valeur | Statut |
|---|---|---|
| SGBD | PostgreSQL | CONFIRMED |
| Version | 17.11 on x86_64-windows | CONFIRMED (connexion du 2026-10-01, avant la panne) |
| Base | `dixpertia` | CONFIRMED |
| Hôte | `localhost:5432` | CONFIRMED |
| Rôle utilisé par l'application | `postgres` | CONFIRMED (`DATABASE_URL`, identifiant uniquement) |
| `postgres` est superutilisateur ? | **oui** : `rolsuper`, `rolcreaterole`, `rolcreatedb`, **`rolbypassrls`** | CONFIRMED — Q-DISC-003 |
| Encodage, collation, fuseau | UTF8 · `French_Tunisia.1252` (collation non-C) · `Africa/Lagos` (UTC+1) | CONFIRMED — Q-DISC-002 |
| Schémas | `public` uniquement | CONFIRMED — Q-DISC-004 |
| Extensions | `plpgsql` uniquement | CONFIRMED — Q-DISC-011 |
| RLS, triggers | aucune RLS, aucun trigger utilisateur | CONFIRMED — Q-DISC-010 |
| Contraintes CHECK | **aucune** | CONFIRMED — Q-DISC-006 |
| Index | 21, dont 9 en double des PK | CONFIRMED — Q-SCH-005, Q-SCH-006 |

## Inventaire des tables

9 tables, créées par `tables.py` le 2026-10-01. Ce nombre est confirmé par la
sortie du script.

| Table | Modèle | Fichier | Rôle métier | PK | Lignes au 2026-10-01 |
|---|---|---|---|---|---|
| `users` | `User` | `app/models/user.py` | comptes et identité de connexion | `id` VARCHAR (`USR-NNN`) | 4 (3 importés de `db.json` + 1 admin) |
| `team_members` | `TeamMember` | `app/models/service.py` | annuaire de l'équipe | `id` VARCHAR (`TM-NNN`) | 0 |
| `payslips` | `Payslip` | `app/models/payroll.py` | bulletins de paie | `id` INTEGER | 0 |
| `leave_requests` | `LeaveRequest` | `app/models/leaves.py` | demandes de congés | `id` INTEGER | 0 |
| `clients` | `Client` | `app/models/invoicing.py` | clients facturés | `id` INTEGER | 0 |
| `invoices` | `Invoice` | `app/models/invoicing.py` | en-têtes de factures | `id` INTEGER | 0 |
| `invoice_items` | `InvoiceItem` | `app/models/invoicing.py` | lignes de factures | `id` INTEGER | 0 |
| `devices` | `Device` | `app/models/invoicing.py` | parc matériel (vendu via factures) | `id` VARCHAR (`DEV-NNN`) | 0 |
| `services` | `Service` | `app/models/service.py` | services affichés sur le site vitrine | `id` INTEGER | 0 |

Ces comptages sont **confirmés** par Q-DISC-005 : `users` = 4, toutes les
autres tables à 0, `clients` et `services` compris. Ils datent d'**avant** les
tests d'exécution du 2026-10-02, qui ont ajouté des lignes `AUDIT-TEST` (liste
dans `11-evidence/api-tests/api-tests.results.md`).

## Classification

### Entités principales
`users`, `invoices`, `clients`, `payslips`, `leave_requests`, `devices`.

### Tables de référence
**Aucune.** Les listes de valeurs sont portées par :
- des **ENUM PostgreSQL**, créés par SQLAlchemy pour `invoices.statut`,
  `leave_requests.type_conge` et `leave_requests.statut`. Ce sont
  `invoicestatus`, `leavetype` et `leavestatus`, et ils stockent les **noms**
  des membres Python (`BROUILLON`, `EN_ATTENTE`, `PAYE`…), non leurs valeurs
  (CONFIRMED, Q-DISC-008) ;
- de **simples chaînes libres** pour `users.role`, `team_members.role`,
  `team_members.status` et `devices.status`, sans aucune contrainte.

Les rôles (`admin`, `employee`, `accountant`) n'existent que sous forme de
commentaire, en `app/models/user.py:11`.

### Tables de liaison (pivot)
**Aucune.** Deux relations de fait n'ont pas de table :
- **facture ↔ appareils vendus** : `main.py:411` écrit `deviceIds` dans un
  attribut qui n'existe pas sur `Invoice`. Le ticket #18 (« device management
  linked to invoices ») est fermé, mais aucun lien n'existe dans le schéma ;
- **projet ↔ membres** : l'entité `Project` n'existe que dans le frontend
  (`src/types.ts:66-75`).

### Tables d'audit / journal
**Aucune.** Il n'existe pas de trace des approbations, des changements de
statut, des changements de rôle ni des connexions. `leave_requests.valide_par_id`
est la seule colonne de traçabilité du schéma, et elle n'est alimentée que par
un router non monté (`app/routers/leaves.py:57`).

### Tables sensibles

| Table | Données sensibles | Nature |
|---|---|---|
| `users` | `hashedPassword` (bcrypt), `resetToken` (JWT en clair), `resetTokenExpiry`, `email`, nom, prénom | authentification et données personnelles |
| `payslips` | `montant_brut`, `montant_net`, `fichier_pdf`, lien vers l'employé | **rémunération**, donnée personnelle sensible |
| `leave_requests` | `type_conge` (dont `maladie`), `motif` | potentiellement **santé** |
| `invoices`, `invoice_items` | montants HT et TTC, TVA, client | financier et comptable |
| `clients` | nom, e-mail, téléphone, adresse | données personnelles et commerciales de tiers |
| `team_members` | e-mail, nom, rôle | données personnelles |

## Relations déclarées dans les modèles

Toutes les clés étrangères sont déclarées sans `ondelete` ni `onupdate`. En
PostgreSQL, le comportement effectif est donc `NO ACTION`, sur les 6 FK
(CONFIRMED, Q-SCH-004). **5 des 6 colonnes de FK n'ont aucun index**
(Q-SCH-007).

| De | Vers | Colonne | Nullable | `relationship()` ORM |
|---|---|---|---|---|
| `payslips` | `users` | `employee_id` VARCHAR | non | aucune |
| `leave_requests` | `users` | `employee_id` VARCHAR | **oui** | aucune |
| `leave_requests` | `users` | `valide_par_id` VARCHAR | oui | aucune |
| `invoices` | `clients` | `client_id` INTEGER | non | `Invoice.client` ↔ `Client.invoices` |
| `invoices` | `users` | `cree_par_id` VARCHAR | **oui**, volontairement : « so we can insert without it » (`app/models/invoicing.py:45`) | aucune |
| `invoice_items` | `invoices` | `invoice_id` INTEGER | non | `Invoice.items` (cascade ORM `all, delete-orphan`) |

`team_members`, `devices`, `services` et `clients` (en tant qu'enfant) n'ont
**aucune clé étrangère**.

## Contraintes déclarées dans les modèles

| Table | Contrainte |
|---|---|
| `users` | `email` UNIQUE + index ; `id` PK + index |
| `payslips` | UNIQUE (`employee_id`, `periode`) nommée `uq_employee_periode` |
| `invoices` | `numero` UNIQUE |
| toutes | PK |

Les modèles ne déclarent **aucune contrainte CHECK** : pas de montant positif,
pas de `date_fin >= date_debut`, pas de `date_echeance >= date_emission`, pas de
liste fermée de rôles. C'est confirmé dans le catalogue : **0 contrainte
CHECK** (Q-DISC-006). Le sondage des contraintes montre que la base accepte
26 types de données métier invalides (`08-data-integrity/data-integrity-results.md`).

Correction : l'unicité de `users.email` est portée par un **index unique**
(`ix_users_email`), et non par une contrainte `UNIQUE` (Q-SCH-003, Q-SCH-005).
L'effet est le même.

## Migrations

- **Aucune migration n'existe** : `alembic/versions/` est vide.
- La table `alembic_version` est **absente** (CONFIRMED, Q-DISC-009). Aucune
  migration n'a jamais été appliquée à cette base.
- Le schéma est créé par `create_all()`, qui **crée les tables manquantes mais
  ne modifie jamais une table existante**. Une colonne ajoutée à un modèle ne
  sera donc jamais propagée à une base déjà créée.

## Conventions

Voir `project-structure.md` § Conventions de nommage : mélange de camelCase
anglais et de snake_case français, et mélange de PK chaînes générées par
l'application et de PK entières auto-incrémentées.
