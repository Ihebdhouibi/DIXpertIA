# AUDIT-DB-010 — Création de facture : séparation des responsabilités inversée, statut absent, doublons

## Sévérité
HIGH

**Justification :**
- **Impact :**
  - **corruption de données en usage normal** : chaque tentative crée une
    facture **et** renvoie une erreur, ce qui produit des doublons numérotés ;
  - **règle métier centrale violée** : la comptable peut créer les factures
    qu'elle est censée contrôler.
- **Exploitabilité :** par un utilisateur authentifié au-delà de ses droits, ce
  qui remplit le critère HIGH.
- **Probabilité :** certaine, à chaque création par l'API.

## Catégorie
Intégrité des données / Règles métier / Contrôle d'accès

## Statut
OPEN · CONFIRMED

## Résumé
`POST /api/invoices` présente trois défauts :
1. Il est ouvert aux rôles `rh`, `admin` **et `accountant`**, alors que la
   règle métier réserve la génération des factures à l'admin.
2. Il **ne positionne jamais `statut`**, qui reste NULL.
3. Le schéma de sortie exige un statut. La sérialisation **échoue donc après le
   commit** : la facture est enregistrée, le client reçoit une erreur 500, et
   une nouvelle tentative crée une seconde facture.

## Détails techniques
- Le router déclare `dependencies=[Depends(require_roles("rh", "admin", "accountant"))]`
  (`app/routers/invoicing.py:14`).
- La règle « admin seulement » existe en `main.py:393-396`, mais cette route
  est **masquée** par celle du router, enregistrée avant elle (`main.py:40`).
- La construction de `Invoice(...)`, en `invoicing.py:64-72`, ne mentionne pas
  `statut`. La colonne `invoices.statut` est nullable et sans défaut
  (Q-SCH-001).
- `InvoiceOut.statut: InvoiceStatus` est obligatoire
  (`app/schemas/invoicing.py:54`).
- Log : `ResponseValidationError … ('response', 'statut') … input: None`.
- Point positif : les montants sont recalculés côté serveur, et l'en-tête est
  créé avec ses lignes en un seul commit.

## Impact métier
- **La comptable peut créer, puis approuver** (une fois l'approbation
  construite) ses propres factures. La séparation des responsabilités, contrôle
  comptable de base, n'existe pas.
- **Factures en double** à chaque nouvelle tentative, chacune avec son propre
  numéro légal. En comptabilité, une facture émise ne se supprime pas : chaque
  doublon impose un avoir.
- **Aucune facture n'a de statut** : impossible de distinguer un brouillon
  d'une facture émise ou payée.

## Preuves
- **T-B05.1 et T-B05.2** : jeton de la comptable → **500** à chaque tentative.
- **T-B05.db** : 2 lignes en base, `FA-2026-0001` et `FA-2026-0002`, toutes deux
  `statut = None`, `cree_par_id = USR-009` (la comptable).
- La cause dans le log est citée plus haut.

## Composants concernés
`app/routers/invoicing.py`, `app/schemas/invoicing.py`, `main.py:393-423`
(code mort), table `invoices`.

## Localisation
- **Code :** `app/routers/invoicing.py:14`, `:55-82` ;
  `app/schemas/invoicing.py:54` ; `main.py:40`, `:393`.
- **Base :** `invoices.statut`, `invoices.cree_par_id`.

## Cause racine
Deux implémentations concurrentes de la même route, celle du router et celle
de `main.py`, avec des règles différentes. La moins stricte l'emporte par
l'ordre d'enregistrement. Le statut initial n'a jamais été défini.

## Recommandation
1. Une seule route de création, réservée à l'admin.
2. Statut initial **`BROUILLON`**, positionné par le serveur et imposé par
   `NOT NULL DEFAULT 'BROUILLON'`.
3. Transitions de statut via des endpoints dédiés (AUDIT-DB-011).
4. Construire la réponse avant le commit, ou valider les données avant
   l'écriture, pour qu'une erreur de sérialisation ne laisse jamais une ligne
   orpheline.
5. Clé d'idempotence (`Idempotency-Key`), pour qu'une nouvelle tentative ne
   crée pas de doublon.

## Correctif proposé
- `invoicing.py` :
  - `require_roles("admin")` sur `POST /invoices` ;
  - `statut=InvoiceStatus.BROUILLON` dans le constructeur.
- Supprimer `main.py:393-423`.
- Migration :
  ```sql
  UPDATE invoices SET statut = 'BROUILLON' WHERE statut IS NULL;
  ALTER TABLE invoices ALTER COLUMN statut SET NOT NULL, ALTER COLUMN statut SET DEFAULT 'BROUILLON';
  ```
- Décider du sort des 2 factures `AUDIT-TEST` créées par l'audit.

## Risques du correctif
- La comptable perd le droit de créer : c'est voulu, mais à confirmer par le
  métier (R-FAC-01).
- La migration doit tourner **avant** que de vraies factures n'existent.

## Validation
- Rejouer T-B05 avec le jeton de la comptable : **403**.
- Avec un jeton admin : **200**, `statut = brouillon`, une seule ligne en base.

## Effort estimé
S pour le correctif, M avec l'idempotence.

## Dépendances
AUDIT-DB-015 (migrations), AUDIT-DB-012 (numérotation).

## Findings liés
AUDIT-DB-011 (circuit d'approbation absent), AUDIT-DB-012, AUDIT-DB-013
(routes concurrentes), AUDIT-DB-014.
