# AUDIT-DB-019 — Rôles non modélisés et représentation hétérogène des valeurs

## Sévérité
LOW

**Justification :**
- Ce sont des faiblesses de modélisation **sans exploitation directe**.
- Elles provoquent des erreurs silencieuses : un rôle mal orthographié sans
  droit, un arrondi flottant sur un prix, un décalage horaire sur une date
  d'émission.
- Elles compliquent toute requête et tout outil qui lisent la base directement.
- Les risques réels (rôle hors liste, absence de NOT NULL) sont traités par
  AUDIT-DB-014. Restent ici les choix de représentation, d'où le niveau LOW.

## Catégorie
Modèle de données / Conventions

## Statut
OPEN · CONFIRMED

## Résumé

| # | Constat | Preuve |
|---|---|---|
| 1 | **Les rôles ne sont pas une entité :** une chaîne libre `users.role`, documentée par un simple commentaire (`app/models/user.py:11`). Un **rôle fantôme `rh`** est accepté par `require_roles("rh", "admin", "accountant")` (`invoicing.py:14`), mais n'existe nulle part ailleurs. Il n'y a pas de notion de permission, seulement des comparaisons de chaînes dans chaque route. | code ; sonde P-21 (`superadmin` accepté) |
| 2 | **Deux notions s'appellent `role`** : le droit dans `users.role`, le poste dans `team_members.role` (`'Contributor'`…). | code |
| 3 | **Argent en virgule flottante :** `devices.price` est un `double precision`. | Q-SCH-011 |
| 4 | **Trois types temporels coexistent :** `timestamp` naïf alimenté par `utcnow` (`users`, `devices`), `timestamptz` alimenté par `now()` (`payslips`, `leave_requests`), et `date` (dates métier). Les dates d'émission utilisent `date.today()`, donc **l'heure locale du serveur**, alors que les horodatages sont en UTC. | Q-SCH-010 ; `invoicing.py:36`, `:67` |
| 5 | **Deux vocabulaires d'ENUM :** la base stocke `BROUILLON`, l'API expose `brouillon`, et le frontend affiche `Draft`. Trois noms pour un seul état. | Q-SCH-009 ; `src/types.ts:58` |
| 6 | **14 colonnes camelCase** imposent des guillemets dans tout SQL écrit à la main (`"isActive"`). | Q-SCH-002 |
| 7 | **`devices` est rangé dans `invoicing.py`**, sans relation avec les factures. | `app/models/invoicing.py:65` |

## Impact métier
Erreurs silencieuses et coût de maintenance. Un rapport SQL ou un export lu par
la comptable affiche `PAYEE`, alors que l'application affiche `Paid`.

## Preuves
`11-evidence/schema/02-schema-inventory.results.md` (Q-SCH-002, 009, 010, 011) ;
`11-evidence/data-integrity/constraint-probe.results.md` (P-21).

## Composants concernés
`app/models/*`, `app/routers/invoicing.py`, `app/core/deps.py`, `src/types.ts`.

## Localisation
- **Code :** `app/models/user.py:11` ; `app/routers/invoicing.py:14`, `:36`,
  `:67` ; `app/models/invoicing.py:65-73`.
- **Base :** `users.role`, `devices.price`, colonnes temporelles, ENUM.

## Cause racine
Ce sont des conventions héritées de plusieurs étapes de développement, sans
guide de modélisation commun.

## Recommandation
1. **Rôles :** une liste fermée en base (CHECK, voir AUDIT-DB-014), puis, si le
   besoin de finesse apparaît, des tables `roles`, `permissions` et
   `role_permissions`. Décider du sort de `rh` : l'ajouter, ou le retirer du
   code.
2. **Renommer** `team_members.role` en `job_title`.
3. **`devices.price` → `NUMERIC(10,2)`.**
4. **Temps :**
   - `timestamptz` partout pour les horodatages ;
   - un fuseau de référence explicite (`Africa/Tunis`) pour les dates métier,
     comme la date d'émission et l'année de numérotation.
5. **ENUM :** `Enum(..., values_callable=lambda e: [m.value for m in e])` pour
   stocker les valeurs. Sinon, documenter explicitement le choix des noms.
6. **Nommage :** snake_case partout, à décider avec le ticket #37
   (AUDIT-DB-013).

## Correctif proposé
Ces changements sont à regrouper avec la migration de convergence du ticket #37.
Ils sont isolément peu coûteux, mais touchent de nombreuses colonnes.

## Risques du correctif
- Le renommage de colonnes et le changement de stockage des ENUM sont des
  migrations de données, à faire **avant** la saisie de données réelles.
- Passer de `timestamp` à `timestamptz` exige d'interpréter les valeurs
  existantes. Elles sont en UTC, puisqu'elles viennent de `utcnow`.

## Validation
- Q-SCH-002 : 0 ligne.
- Q-SCH-010 : `timestamptz` et `date` seulement.
- Q-SCH-011 : aucune colonne `double precision`.
- Sonde P-21 : rejetée.

## Effort estimé
M, en grande partie absorbé par AUDIT-DB-013.

## Dépendances
Ticket #37 ; AUDIT-DB-013 ; AUDIT-DB-015.

## Findings liés
AUDIT-DB-013, AUDIT-DB-014.
