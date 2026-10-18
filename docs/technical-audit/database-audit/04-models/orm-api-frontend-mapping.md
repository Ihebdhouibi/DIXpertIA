# Phase 3 — Correspondance frontend ↔ API ↔ ORM ↔ base

> 2026-10-01 · `develop` @ `34453a4`
>
> **Périmètre de ce document :** la comparaison **côté code** entre le frontend
> (`src/types.ts`), l'API héritée (`main.py`), les schémas Pydantic et routers
> (`app/schemas/`, `app/routers/`) et les modèles ORM (`app/models/`).
>
> La comparaison **ORM ↔ schéma réel** dépend de Q-SCH-001 à Q-SCH-013, qui
> n'ont pas encore été exécutées (serveur indisponible). Elle fera l'objet de
> `orm-vs-database.md`.

## Synthèse

| Entité | Frontend | API `main.py` | Schéma ou router | ORM | Cohérence |
|---|---|---|---|---|---|
| Utilisateur | `User` | `UserCreate`, `/api/login` | `schemas/user.py` (**non importable**) | `User` | 🟡 cohérent frontend ↔ API ↔ ORM ; le code mort diverge |
| Bulletin de paie | `Payslip` | lecture via `/api/data` | `schemas/payroll.py` | `Payslip` | 🔴 **aucun champ commun** hormis `id`, dont le type diffère |
| Demande de congé | `LeaveRequest` | `LeaveRequestCreate` | `schemas/leaves.py` | `LeaveRequest` | 🔴 incompatible ; l'API plante à la création |
| Membre d'équipe | `TeamMember` | `TeamMemberCreate` | — | `TeamMember` | 🟢 **seule entité cohérente de bout en bout**, mais elle duplique `User` |
| Facture | `Invoice` | `InvoiceCreate` | `schemas/invoicing.py` | `Invoice` | 🔴 **aucun champ commun** entre frontend et ORM |
| Ligne de facture | `Invoice.items[]` | `InvoiceItem` | `InvoiceItemCreate` | `InvoiceItem` | 🔴 noms et sémantique différents ; TVA absente côté frontend |
| Client | chaîne libre `Invoice.client` | chaîne libre | `ClientCreate` | `Client` | 🔴 c'est une entité côté base, un simple texte côté UI |
| Appareil | **absent** | `DeviceCreate` | — | `Device` | 🟡 API ↔ ORM cohérents, mais aucune UI et toutes les routes plantent (OBS-010) |
| Service | **absent** (contenu statique) | — | `schemas/service.py` | `Service` | ⚪ table orpheline : aucun code actif ne la lit ni ne l'écrit |
| Projet | `Project` | **absent** | — | **absent** | ⚪ n'existe que dans le navigateur |
| Notification | `Notification` (`App.tsx:36`) | **absent** | — | **absent** | ⚪ n'existe que dans le navigateur |

Sur 11 entités, **une seule** (`TeamMember`) a la même forme dans toutes les
couches. Les trois entités au cœur du métier (facture, congé, bulletin) sont
incompatibles entre l'interface et la base.

---

## 1. Utilisateur

| Champ | Frontend `src/types.ts:3-16` | API `main.py` | Code mort (`schemas/user.py`, `routers/auth.py`) | ORM `models/user.py` | Constat |
|---|---|---|---|---|---|
| id | `string` | `str` (`USR-NNN`) | `int` | `String` PK | le code mort suppose un entier |
| prénom / nom | `firstName`, `lastName` | idem | `first_name`, `last_name` | `firstName`, `lastName` (nullable) | obligatoires dans l'UI et l'API, nullables en base |
| email | `string` | `EmailStr` | `EmailStr` | `String` UNIQUE | unicité sensible à la casse (Q-INT-004) |
| rôle | union `'employee'\|'admin'\|'accountant'` | **`str` libre** | `RoleEnum` (**inexistant**) | `String` libre | le seul contrôle des valeurs est le typage TypeScript, inexistant à l'exécution |
| département | `string?` | **non modifiable par l'API** | — | `String` nullable | l'UI affiche `'Operations'` par défaut (`App.tsx:223`) |
| avatar | `string?` | non modifiable par l'API | — | `String` nullable | idem |
| isActive | `boolean` | renvoyé, **jamais vérifié** | `is_active` | `Boolean` default `True` | OBS-011 |
| isVerified | `boolean` | mis à `False` à la création ; **aucun endpoint ne le passe à `True`** | — | `Boolean` default `False` | il n'est mis à `True` que par `seed_users.py:95` (admins créés par le script) et par le faux profil du bouton « Switch to Admin » (`App.tsx:262`) ; aucun code ne le consulte : champ sans effet |
| createdAt | `string` | renvoyé | — | `DateTime` naïf, `utcnow` | |
| hashedPassword | — | utilisé | `hashed_password` | `String` **nullable** | un compte sans hash est permis par le schéma |
| resetToken / resetTokenExpiry | **déclarés dans le type frontend** | jamais renvoyés (filtrés, `main.py:118`) | — | `String` / `DateTime` | OBSERVATION : le type frontend porte encore des champs secrets, vestige de l'époque où l'API les exposait |

## 2. Bulletin de paie

| Champ | Frontend `src/types.ts:18-25` | `/api/data` (`_row`, `main.py:512`) | Schéma `PayslipOut` | ORM `models/payroll.py` | Constat |
|---|---|---|---|---|---|
| identifiant | `id: string` (`PS-001`) | `id` int | `id: int` | `Integer` PK | types différents |
| **employé** | **absent** | `employee_id` | `employee_id: int` | `employee_id` **VARCHAR** FK → `users` | 🔴 **le frontend n'a aucun lien employé** : tous les rôles voient la même liste fictive ; le schéma déclare `int` pour une colonne `VARCHAR` (OBS-028) |
| période | `period: "September 2024"` (texte) | `periode` | `periode: date` | `Date` | représentation texte ↔ date |
| brut | `grossPay: number` | `montant_brut` | `Decimal` | `Numeric(10,2)` | noms différents |
| net | `netPay: number` | `montant_net` | `Decimal` | `Numeric(10,2)` | noms différents |
| émission | `issuedOn: "Sep 30, 2024"` (texte) | `date_emission` | `datetime` | `DateTime(tz)` | |
| PDF | `pdfUrl?` | `fichier_pdf` | `str \| None` | `String(255)` | |

**Conséquence :** même si le frontend appelait `/api/data`, il ne pourrait
afficher aucun bulletin. Les clés JSON renvoyées (`montant_brut`…) ne sont pas
celles qu'il lit (`grossPay`…), comme le montre le comptage des champs lus par
les vues : `slip.grossPay`, `slip.netPay`, `slip.period`, `slip.issuedOn`.

## 3. Demande de congé

| Champ | Frontend `src/types.ts:27-38` | API `main.py:132-139` | Schéma `leaves.py` | ORM `models/leaves.py` | Constat |
|---|---|---|---|---|---|
| id | `string` (`LR-001`) | `str` (`LR-00NNN`) | `int` | `Integer` PK | l'API passe une chaîne à une PK entière |
| employé | `employeeId` | `employeeId`, **fourni par l'appelant** | `employee_id: int` | `employee_id` VARCHAR, **nullable** | |
| nom de l'employé | `employeeName` | `employeeName` | — | **absent** | donnée dénormalisée, dérivable de `users` |
| département | `department` | `department` | — | **absent** | idem |
| type | `'Annual Leave'\|'Sick Leave'\|'Personal Day'\|'Unpaid Leave'` (4) | `str` | `LeaveType` | ENUM `paye`, `maladie`, `sans_solde` (**3**) | 🔴 **`Personal Day` n'a pas d'équivalent** |
| dates | **`dates: string` libre** (`"Oct 20, 2024"`) | `str` | `date_debut`, `date_fin` | `date_debut`, `date_fin` `Date` NOT NULL | 🔴 une plage de dates en texte libre ne se convertit pas de façon fiable en deux dates |
| durée | `duration: number` | `int` | — | **absent** | valeur dérivée (`date_fin − date_debut`), stockée côté UI |
| statut | `'Approved'\|'Pending'\|'Rejected'` | `'Pending'` | `LeaveStatus` | ENUM `en_attente`, `approuve`, `refuse` | correspondance 1-pour-1 possible, mais les libellés diffèrent |
| motif | `reason?` | `reason` | `motif` | `motif` Text | |
| motif de refus | `rejectionReason?` | écrit `leave.rejectionReason` | `commentaire_validation` | `commentaire_validation` | 🔴 l'écriture de l'API vise un attribut inexistant (OBS-006) |
| valideur | — | — | (positionné par le router mort) | `valide_par_id` FK | **jamais renseigné par le code actif** |
| création | — | — | `created_at` | `created_at` tz, `server_default` | |

## 4. Membre d'équipe

| Champ | Frontend | API `main.py:144-151` | ORM `models/service.py:16-25` | Constat |
|---|---|---|---|---|
| id | `string` | `TM-00NNN` (`count()+1`) | `String` PK | cohérent |
| firstName, lastName, email, role, status, initials, avatarUrl | ✓ | ✓ | ✓ (tous nullables) | **noms identiques dans les trois couches** |
| lien vers `users` | — | — | **aucun** | 🔴 duplique `User` (OBS-026) |
| `email` par défaut | — | **fabriqué** : `prenom.nom@dixpertia.com` (`main.py:375`) | — | l'API invente une adresse sur un domaine `.com`, alors que le domaine de la société est `dixpertia.tn` |
| `role` | `string` libre (`'Contributor'`…) | `str` | `String` | c'est l'**intitulé de poste**, sans rapport avec `users.role`. Deux notions portent le même nom. |

## 5. Facture et lignes de facture

### En-tête

| Champ | Frontend `types.ts:51-65` | API morte `main.py:159-168` | Router `schemas/invoicing.py` | ORM `models/invoicing.py:34-49` | Constat |
|---|---|---|---|---|---|
| identifiant | `id: "INV-2024-001"` | `id: str` | `id: int` + `numero: str` | `id` Integer + `numero` UNIQUE | l'UI utilise un numéro comme identifiant |
| client | `client: string` + `clientInitials` | idem | `client_id: int` | FK → `clients` | 🔴 texte libre ↔ clé étrangère ; `clientInitials` est une donnée de présentation |
| montant | `amount` | `amount: float` | `montant_ht`, `montant_ttc` calculés | `Numeric(10,2)` nullable | 🔴 un seul montant côté UI, sans HT/TTC ; `float` dans l'API |
| émission | `dateIssued: "Oct 12, 2024"` | texte | `date_emission` = **aujourd'hui, imposé** | `Date` NOT NULL | le router ne permet pas d'antidater ni de choisir la date |
| échéance | `dueDate` texte | texte | `date_echeance: date` | `Date` NOT NULL | |
| statut | `Draft\|Sent\|Paid\|Overdue` | `'Sent'` | `InvoiceStatus` **requis en sortie** | ENUM **nullable**, jamais positionné | 🔴 OBS-020 ; `annulee` n'existe pas dans l'UI ; `Overdue` est une valeur dérivable, stockée comme un état |
| créateur | — | — | `current_user.id` | `cree_par_id` **nullable** | |
| appareils vendus | — | `deviceIds` | — | **aucune colonne** | OBS-025 |
| approbation comptable | — | — | — | **aucune colonne** | OBS-005 |
| type (entrante/sortante) | — | — | — | **aucune colonne** | ticket #40 |

### Lignes

| Champ | Frontend `items[]` | API morte | Router `InvoiceItemCreate` | ORM `InvoiceItem` | Constat |
|---|---|---|---|---|---|
| libellé | `description` | `description` | `designation` | `designation` String(255) | noms différents |
| quantité | `qty` (entier) | `int` | `Decimal` | `Numeric(8,2)` default 1 | |
| prix | `price` | `float` | `prix_unitaire` | `Numeric(10,2)` | |
| total de ligne | `total` (**stocké**) | `float` | — | **absent** (dérivé) | l'UI stocke une valeur dérivée, sans contrôle de cohérence |
| TVA | **absente** | absente | `taux_tva` default 19 | `Numeric(4,2)` default 19 | 🔴 l'UI ne connaît pas la TVA, donc son `amount` ne correspond ni au HT ni au TTC |

## 6. Appareil
- `main.py:187-192` (`DeviceCreate`) et `models/invoicing.py:65-73` utilisent
  les mêmes noms : `name`, `model`, `serialNumber`, `price`, `status`,
  `createdAt`.
- `price` est un `Float` en base et un `float` dans l'API (OBS-024).
- `status` est une chaîne libre : `'Available'`, `'Sold'`.
- `serialNumber` n'est pas unique.
- Il n'existe **aucune UI**.
- Le modèle est rangé dans `invoicing.py` alors qu'il n'a aucune relation avec
  `Invoice`.

## 7. Service
- `models/service.py:5-13` et `schemas/service.py` sont cohérents entre eux.
- Le router n'est **pas monté**, et la homepage affiche du contenu statique.
- La table existe mais **aucun code actif ne l'utilise**.

---

## Logique métier présente seulement dans le code, alors qu'une contrainte de base serait pertinente

| Règle | Où elle vit aujourd'hui | Contrainte de base pertinente |
|---|---|---|
| un rôle ∈ {admin, employee, accountant} | commentaire, et type TypeScript | `CHECK` ou ENUM, ou table de rôles + FK |
| `date_fin >= date_debut` | nulle part | `CHECK (date_fin >= date_debut)` |
| `date_echeance >= date_emission` | nulle part | `CHECK` |
| montants ≥ 0 ; `montant_ttc >= montant_ht` | nulle part | `CHECK` |
| `montant_net <= montant_brut` | nulle part | `CHECK` |
| `quantite > 0`, `0 <= taux_tva <= 100` | nulle part | `CHECK` |
| pas deux congés qui se chevauchent pour un même employé | nulle part | contrainte d'exclusion `EXCLUDE USING gist` sur une `daterange` |
| numéro de série d'appareil unique | nulle part | `UNIQUE` |
| un e-mail = un compte, quelle que soit la casse | `UNIQUE` sensible à la casse | `UNIQUE` sur `lower(email)`, ou type `citext` |
| identifiants `USR-NNN`, `TM-NNN`, `DEV-NNN` uniques et non réutilisés | `count() + 1` dans l'application | séquence ou `IDENTITY` |
| un membre d'équipe correspond à un utilisateur | nulle part | FK `team_members.user_id → users.id` |

## Constats propres à l'ORM

1. **`relationship()` n'est déclarée que dans `invoicing.py`.** Les clés
   étrangères de `payslips` et `leave_requests` vers `users` n'ont aucune
   relation ORM, et `User` n'a aucune relation inverse. Tout accès croisé exige
   donc une requête écrite à la main.
2. **`primary_key=True, index=True`** sur toutes les PK (`User.id`,
   `TeamMember.id`, `Device.id`, et toutes les PK entières). Cela produit
   probablement un index redondant à côté de l'index de PK : à confirmer par
   Q-SCH-006.
3. **`cascade="all, delete-orphan"`** sur `Invoice.items` est appliqué **par
   l'ORM seulement**. La FK `invoice_items.invoice_id` n'a pas
   d'`ondelete="CASCADE"`. Une suppression SQL directe d'une facture est donc
   refusée (`NO ACTION`), alors qu'une suppression via l'ORM supprime les
   lignes. Les deux chemins ont des comportements différents (Q-SCH-004).
4. **`Enum(InvoiceStatus)` sans `values_callable`** : SQLAlchemy stocke le
   **nom** du membre (`BROUILLON`), et non sa valeur (`brouillon`). C'est
   **CONFIRMED** par Q-SCH-009.
   - L'hypothèse selon laquelle `insert_invoices.py`, qui passe `"brouillon"`,
     échouerait est **REFUTED**. Le processeur de liaison de SQLAlchemy accepte
     aussi la valeur et la convertit en `'BROUILLON'`
     (`11-evidence/data-integrity/constraint-probe.results.md`).
   - Constat restant (OBSERVATION) : la base, et tout outil qui la lit
     directement (pgAdmin, exports, rapports SQL), voit
     `BROUILLON/ENVOYEE/PAYEE`, alors que l'API expose
     `brouillon/envoyee/payee`. Ce sont deux vocabulaires pour une même valeur.
     Renommer un membre Python changerait silencieusement la valeur attendue en
     base.
5. **`Query.get()`** est utilisé (`routers/invoicing.py:87` et les routers
   morts). C'est une API dépréciée depuis SQLAlchemy 2.0 ; `Session.get()` la
   remplace.
6. **Les valeurs par défaut sont côté Python, pas côté base.** C'est le cas de
   `default=datetime.utcnow`, `default=True` et `default=19` : une insertion SQL
   directe ne les applique pas. Seuls `payslips.date_emission` et
   `leave_requests.created_at` ont un `server_default` (Q-SCH-001).
7. **Le module `app/models/__init__.py` est vide.** L'enregistrement des modèles
   sur `Base.metadata` dépend d'imports faits à la main dans chaque script
   (`tables.py:20-24`, `alembic/env.py:10`, `invoicing.py:11`). Un oubli produit
   un schéma incomplet sans aucune erreur : c'est exactement le défaut corrigé
   par la PR #35.
