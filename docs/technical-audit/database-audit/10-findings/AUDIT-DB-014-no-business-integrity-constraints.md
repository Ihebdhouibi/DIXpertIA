# AUDIT-DB-014 — Aucune contrainte métier en base : 26 types de données invalides acceptés

## Sévérité
HIGH

**Justification :**
- **Impact :** les données **financières** (factures, TVA) et de **paie** peuvent
  être enregistrées dans des états impossibles : montant négatif, TTC inférieur
  au HT, net supérieur au brut, deux bulletins pour un même mois.
- **Probabilité :** élevée, car **ni la base ni l'API** n'appliquent ces
  règles. Le schéma Pydantic `InvoiceItemCreate` accepte un `prix_unitaire`
  négatif, et aucun champ n'est borné. Une saisie erronée, un import ou un bug
  suffisent.
- **Critère HIGH rempli :** une corruption de données est probable en usage
  normal.

## Catégorie
Intégrité des données / Contraintes

## Statut
OPEN · CONFIRMED

## Résumé
La base garantit les clés primaires, les 6 clés étrangères et 3 unicités.
**Elle ne garantit aucune autre règle métier :** 0 contrainte CHECK, des
colonnes obligatoires laissées nullables, et des valeurs par défaut présentes
seulement côté Python.

Sur 30 écritures invalides tentées en transaction annulée, **26 ont été
acceptées**. Les 4 refus correspondent exactement aux contraintes existantes.

## Détails techniques

**Absence de contraintes (catalogue) :**
- Q-DISC-006 : 0 CHECK.
- Q-SCH-001 : nullables à tort, sans valeur par défaut en base :
  `invoices.statut`, `montant_ht`, `montant_ttc` et `cree_par_id` ;
  `leave_requests.employee_id`, `type_conge` et `statut` ; `users.role`,
  `hashedPassword` et `isActive`.
- Unicités métier absentes :
  - e-mail sensible à la casse ;
  - numéro de série d'appareil ;
  - nom de client ;
  - paie unique sur une **date** au lieu d'un **mois**.

**Données impossibles acceptées (sondage) :**

| Domaine | Sondes |
|---|---|
| Factures | montant −500 ; échéance avant émission ; TTC < HT ; sans statut ; sans montant ; sans auteur ; en-tête incohérent avec les lignes (P-01 à P-07) |
| Lignes | quantité −4 ; TVA 99,99 % ; TVA −19 % ; prix −10 (P-08 à P-11) |
| Congés | sans employé ; fin avant début ; auto-validation ; approuvé sans valideur ; chevauchement (P-12 à P-16) |
| Paie | net > brut ; négatifs ; **deux bulletins le même mois** (P-17, P-18, P-20) |
| Comptes | rôle `superadmin` ; sans rôle ni mot de passe ; `PROBE@` / `probe@` ; `isActive` NULL (P-21 à P-24) |
| Inventaire et clients | numéro de série dupliqué ; prix −99,99 et statut « Volé » ; clients homonymes (P-25 à P-27) |

## Impact métier
- **Une facture ou un bulletin faux peut être enregistré** sans aucune alerte,
  puis imprimé (PDF) et transmis.
- **Les totaux comptables peuvent devenir incohérents**, car le HT et le TTC
  stockés ne sont pas liés aux lignes.
- **Un compte au rôle mal orthographié** (`Admin`, `superadmin`) n'a aucun
  droit, sans que rien ne le signale.
- **Un employé peut avoir deux comptes**, à la casse près.

## Preuves
- `11-evidence/data-integrity/constraint-probe.results.md` : 26 sondes
  acceptées sur 30, et 0 ligne résiduelle.
- `11-evidence/schema/02-schema-inventory.results.md` : Q-SCH-001, Q-SCH-003.
- `08-data-integrity/data-integrity-results.md`.

## Composants concernés
Toutes les tables métier ; `app/models/*` ; `app/schemas/invoicing.py`.

## Localisation
- **Code :** `app/models/*.py` (colonnes `nullable`, `default=` Python) ;
  `app/schemas/invoicing.py:26-30`.
- **Base :** `invoices`, `invoice_items`, `leave_requests`, `payslips`,
  `users`, `devices`, `clients`.

## Cause racine
Le schéma est généré par `create_all()` à partir de modèles qui ne déclarent
que des types. Aucune règle métier n'a été traduite en contrainte.

## Recommandation
Traduire en contraintes **toutes** les règles qui ne dépendent que d'une ligne,
et valider les mêmes règles dans les schémas Pydantic pour renvoyer des
messages clairs. La base reste le dernier rempart.

## Correctif proposé
Migration, appliquée **après** vérification qu'aucune donnée existante ne viole
les contraintes. Q-INT-011 à 020 servent à cette vérification.

```sql
ALTER TABLE invoices
  ALTER COLUMN statut SET NOT NULL, ALTER COLUMN statut SET DEFAULT 'BROUILLON',
  ALTER COLUMN montant_ht SET NOT NULL, ALTER COLUMN montant_ttc SET NOT NULL,
  ALTER COLUMN cree_par_id SET NOT NULL,
  ADD CONSTRAINT ck_invoices_amounts CHECK (montant_ht >= 0 AND montant_ttc >= montant_ht),
  ADD CONSTRAINT ck_invoices_dates   CHECK (date_echeance >= date_emission);
ALTER TABLE invoice_items
  ADD CONSTRAINT ck_items_qty   CHECK (quantite > 0),
  ADD CONSTRAINT ck_items_price CHECK (prix_unitaire >= 0),
  ADD CONSTRAINT ck_items_vat   CHECK (taux_tva >= 0 AND taux_tva <= 100);
ALTER TABLE leave_requests
  ALTER COLUMN employee_id SET NOT NULL,
  ADD CONSTRAINT ck_leave_dates CHECK (date_fin >= date_debut),
  ADD CONSTRAINT ck_leave_no_self_validation CHECK (valide_par_id IS NULL OR valide_par_id <> employee_id),
  ADD CONSTRAINT ck_leave_decision_has_validator CHECK (statut = 'EN_ATTENTE' OR valide_par_id IS NOT NULL);
ALTER TABLE payslips
  ADD CONSTRAINT ck_payslip_amounts CHECK (montant_brut >= 0 AND montant_net >= 0 AND montant_net <= montant_brut),
  ADD CONSTRAINT ck_payslip_month   CHECK (extract(day FROM periode) = 1);
ALTER TABLE users
  ALTER COLUMN role SET NOT NULL, ALTER COLUMN "hashedPassword" SET NOT NULL,
  ALTER COLUMN "isActive" SET NOT NULL, ALTER COLUMN "isActive" SET DEFAULT true,
  ADD CONSTRAINT ck_users_role CHECK (role IN ('admin','employee','accountant'));
CREATE UNIQUE INDEX ux_users_email_ci ON users (lower(email));
CREATE UNIQUE INDEX ux_devices_serial ON devices ("serialNumber") WHERE "serialNumber" IS NOT NULL;
-- chevauchement de congés (si la règle est confirmée) :
-- CREATE EXTENSION btree_gist;
-- ALTER TABLE leave_requests ADD CONSTRAINT ex_leave_overlap
--   EXCLUDE USING gist (employee_id WITH =, daterange(date_debut, date_fin, '[]') WITH &&) WHERE (statut <> 'REFUSE');
```

La cohérence entre l'en-tête et les lignes (P-07) ne peut pas s'exprimer en
CHECK. Il y a deux possibilités : **ne plus stocker** HT et TTC et les calculer
(vue ou colonne générée), ou figer les montants à l'émission dans une
transaction qui recalcule.

## Risques du correctif
- `ck_users_role` refusera `rh`, rôle encore cité par le router (AUDIT-DB-019).
  Il faut décider : l'ajouter, ou retirer `rh` du code.
- `ck_payslip_month` impose une convention : `periode` = le 1er du mois.
- Les 2 factures `AUDIT-TEST` au statut NULL doivent être corrigées ou
  supprimées avant d'appliquer `NOT NULL`.
- Des règles sont à confirmer par le métier : R-CNG-06 (chevauchement) et
  R-USR-05 (un compte par personne).

## Validation
Rejouer `run_constraint_probe.py` : **toutes les sondes rejetées**, sauf celles
liées à des règles explicitement écartées par le métier.

## Effort estimé
M.

## Dépendances
AUDIT-DB-015 (migrations) ; décisions métier R-CNG-06 et R-USR-05 ;
AUDIT-DB-019 (rôle `rh`).

## Findings liés
AUDIT-DB-010, AUDIT-DB-011, AUDIT-DB-016, AUDIT-DB-019.
