# AUDIT-DB-016 — Entités et relations manquantes ou mal modélisées

## Sévérité
MEDIUM

**Justification :**
- **Impact :** il n'y a pas de corruption ni de faille aujourd'hui. En revanche,
  le modèle **ne peut pas représenter** plusieurs réalités du métier :
  - un employé distinct de son compte de connexion ;
  - un appareil vendu sur une facture ;
  - l'auteur obligatoire d'une facture ;
  - un annuaire d'équipe relié aux comptes.
- **Ce qui justifie MEDIUM :** c'est une dette de modélisation qui rendra chaque
  évolution plus coûteuse, et qui permet déjà des incohérences.

## Catégorie
Modèle de données / Relations

## Statut
OPEN · CONFIRMED

## Résumé

| # | Défaut | Constat |
|---|---|---|
| M1 | **Lien facture ↔ appareil absent** | Le ticket #18, « device management linked to invoices », est fermé. Pourtant, aucune colonne ni table de liaison n'existe, et le passage d'un appareil au statut « Sold » vit dans du code mort. |
| M2 | **`team_members` duplique `users`**, sans FK | Mêmes attributs (nom, e-mail, rôle) dans deux tables non reliées. `team_members.role` désigne un *poste*, alors que `users.role` désigne un *droit* : deux notions portent le même nom. |
| M3 | **Pas de fiche employé distincte du compte** | Les routers morts utilisent `User.employee_profile`, et `EmployeeOut` (poste, date d'embauche, solde de congés), mais aucune table n'existe. La paie et les congés sont rattachés au **compte de connexion**. |
| R2 | **`leave_requests.employee_id` nullable** | Une demande sans demandeur est possible (sonde P-12). |
| R4 | **`invoices.cree_par_id` nullable, volontairement** (`app/models/invoicing.py:45`) | Une facture sans auteur est possible (P-06), et `insert_invoices.py:120` en insère. |
| R6 | **Facture sans ligne possible** | La cardinalité est 0..N, alors que le métier attend 1..N. |
| — | **`ON DELETE` implicite partout** (`NO ACTION`) | Il n'y a aucun choix explicite. La cascade de `Invoice.items` n'existe **que dans l'ORM** : une suppression SQL directe est refusée, alors que la même suppression par l'ORM supprime les lignes (sonde P-28). |
| — | **Aucune relation `relationship()` vers `User`** | 4 FK n'ont aucune navigation ORM, et `User` n'a aucune relation inverse. |
| — | **3 tables isolées** : `team_members`, `devices`, `services` | Aucune FK ni entrante ni sortante. |

## Détails techniques
Voir `05-relations/relations-and-erd.md` pour l'ERD, l'analyse relation par
relation et les relations attendues absentes (M1 à M6).

## Impact métier
- **Impossible de savoir quel appareil a été vendu sur quelle facture**, ni de
  garantir qu'un appareil n'est vendu qu'une fois.
- **Désactiver le compte d'un salarié parti affecte son historique.** La paie
  doit être conservée alors que l'accès doit être retiré : avec la paie
  rattachée au compte, la seule voie est la désactivation (AUDIT-DB-004).
- **Le solde de congés n'est stocké nulle part.**
- **L'identité d'une personne peut diverger** entre `users` et `team_members`.

## Preuves
- `11-evidence/schema/02-schema-inventory.results.md` : Q-SCH-003 et Q-SCH-004
  (6 FK, toutes `NO ACTION`).
- `11-evidence/data-integrity/constraint-probe.results.md` : P-06, P-12 et P-28.
- `05-relations/relations-and-erd.md`.

## Composants concernés
`app/models/*`, `app/routers/leaves.py`, `app/routers/payroll.py`,
`app/schemas/user.py`, `insert_invoices.py`.

## Localisation
- **Code :** `app/models/invoicing.py:45`, `:65-73` ; `app/models/service.py:16-25` ;
  `app/models/leaves.py:24`.
- **Base :** `team_members`, `devices`, `leave_requests.employee_id`,
  `invoices.cree_par_id`.

## Cause racine
Le modèle a été dérivé du stockage JSON d'origine, où chaque collection était
autonome. Les relations prévues par la conception cible (fiche employé) n'ont
jamais été réalisées.

## Recommandation
À valider avec le métier :
1. **`employees`** (1..1 avec `users`) : poste, date d'embauche, solde de
   congés, statut d'emploi. La paie et les congés y sont rattachés. Fusionner
   `team_members` dans cette entité, ou le relier par FK.
2. **`invoice_devices`** (ou `devices.invoice_id`, si un appareil n'est vendu
   qu'une fois) : FK, avec unicité de l'appareil.
3. `NOT NULL` sur `leave_requests.employee_id` et `invoices.cree_par_id`
   (AUDIT-DB-014).
4. **`ON DELETE` explicite** pour chaque FK :
   - `RESTRICT` pour la paie, les congés et les factures vers les personnes et
     les clients ;
   - `CASCADE` pour `invoice_items → invoices`, aligné sur l'ORM ;
   - complété par une suppression logique (`archived_at`) plutôt que physique.
5. `relationship()` côté ORM pour les 4 FK vers `users`.

## Correctif proposé
Ce chantier est à découper en migrations distinctes :
1. `ondelete` explicites et `relationship()`, sans risque.
2. `NOT NULL` sur les 2 FK, après vérification des données.
3. Création de `employees` et migration des rattachements, ce qui demande une
   décision métier.
4. Lien appareil ↔ facture.

## Risques du correctif
La création de `employees` modifie les FK de `payslips` et de `leave_requests`.
C'est une migration de données, à faire **avant** que la paie réelle ne soit
saisie.

## Validation
- Q-SCH-004 : chaque FK a un comportement `ON DELETE` choisi.
- Sondes P-06 et P-12 : rejetées.
- Scénario : vente d'un appareil sur une facture, puis tentative de le revendre,
  qui est refusée.

## Effort estimé
L.

## Dépendances
AUDIT-DB-015 ; décision du ticket #37 ; décisions métier sur l'entité employé.

## Findings liés
AUDIT-DB-004, AUDIT-DB-013, AUDIT-DB-014.
