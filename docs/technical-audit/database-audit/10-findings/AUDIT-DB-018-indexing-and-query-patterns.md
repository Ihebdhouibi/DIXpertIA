# AUDIT-DB-018 — Index manquants ou redondants, lectures intégrales, N+1

## Sévérité
LOW

**Justification :**
- **Impact actuel :** nul. Les tables sont vides ou presque, et aucun temps
  n'est mesurable.
- **Probabilité de dégradation :** certaine avec le volume. L'historique des
  factures et de la paie ne fait que croître, et les filtres comptables
  attendus portent précisément sur les colonnes non indexées.
- **Coût de correction :** faible.
- **Ce qui justifie LOW :** il n'y a pas de risque propre aujourd'hui. Le
  défaut serait à reclasser **MEDIUM** dès que le circuit comptable
  (AUDIT-DB-011) sera construit sans le corriger.

## Catégorie
Performance

## Statut
OPEN · CONFIRMED

## Résumé
- **5 FK sur 6 ne sont pas indexées.**
- **Aucun index n'est utilisable** pour le tri des factures par date, ni pour
  les filtres par client et par mois.
- **9 index redondants** doublent la PK de chaque table.
- L'index de `numero` ne sert pas la génération du numéro (collation non-C).
- `/api/data` lit 6 tables entières.
- La liste des factures fait 1 + N requêtes.
- Aucune liste n'est paginée.

## Détails techniques

| Constat | Preuve |
|---|---|
| FK non indexées : `invoices.client_id`, `invoices.cree_par_id`, `invoice_items.invoice_id`, `leave_requests.employee_id`, `leave_requests.valide_par_id` | Q-SCH-007 |
| Aucun index utilisable, **même en interdisant le parcours séquentiel** : tri par `date_emission`, filtre `client_id`, filtre par mois, lignes d'une facture | Q-PERF-013 à 016 (coût ≈ 10¹⁰) |
| `ix_<table>_id` redondant sur les 9 tables ; PostgreSQL utilise même `ix_users_id` à la place de `users_pkey` | Q-SCH-006, Q-PERF-004 |
| `numero LIKE 'FA-2026-%'` : l'index est parcouru en entier, sans condition | Q-PERF-017, collation `French_Tunisia.1252` (Q-DISC-002) |
| `/api/data` : 6 `.all()` sans limite | `main.py:498-509` |
| N+1 : `GET /api/invoices` sérialise `items` en chargement paresseux | `invoicing.py:50-52`, `InvoiceOut.items` |
| Aucune pagination ni aucun filtre sur les listes | `07-performance/performance-static-analysis.md` § 2 |

## Impact métier
À terme, les écrans comptables deviendront lents, précisément sur les usages
les plus fréquents : factures du mois, factures d'un client, factures en
attente.

## Preuves
- `11-evidence/explain-plans/04-performance.results.md`.
- `11-evidence/schema/02-schema-inventory.results.md`.
- `07-performance/explain-plans-analysis.md`.

## Composants concernés
`app/models/*` (`index=True` sur les PK, index de FK absents) ;
`app/routers/invoicing.py` ; `main.py` (`/api/data`).

## Localisation
- **Code :** `app/models/*.py` (lignes `primary_key=True, index=True`) ;
  `app/routers/invoicing.py:37`, `:50-52` ; `main.py:498-509`.
- **Base :** tables `invoices`, `invoice_items`, `leave_requests`, plus les 9
  index `ix_*_id`.

## Cause racine
Les index sont déclarés par défaut (`index=True`) sur les PK plutôt qu'à partir
des requêtes réelles. Les FK n'ont aucun index, et PostgreSQL n'en crée pas
automatiquement.

## Recommandation et correctif proposé
```sql
-- supprimer les doublons (les PK restent indexées par leur contrainte)
DROP INDEX ix_users_id, ix_clients_id, ix_devices_id, ix_invoice_items_id, ix_invoices_id,
           ix_leave_requests_id, ix_payslips_id, ix_services_id, ix_team_members_id;
-- index utiles aux accès réels et au circuit comptable
CREATE INDEX ix_invoices_client_date ON invoices (client_id, date_emission DESC);
CREATE INDEX ix_invoices_status_date ON invoices (statut, date_emission DESC);
CREATE INDEX ix_invoices_date        ON invoices (date_emission DESC);
CREATE INDEX ix_invoice_items_invoice ON invoice_items (invoice_id);
CREATE INDEX ix_leave_employee       ON leave_requests (employee_id, date_debut);
CREATE INDEX ix_invoices_creator     ON invoices (cree_par_id);
CREATE INDEX ix_leave_validator      ON leave_requests (valide_par_id);
```

Côté modèles, retirer `index=True` des PK.

Côté code :
- `selectinload(Invoice.items)` sur la liste ;
- pagination `limit` / `offset`, avec un plafond ;
- suppression de `/api/data` (AUDIT-DB-003) ;
- numérotation par compteur plutôt que par `LIKE` (AUDIT-DB-012).

## Risques du correctif
Les `DROP INDEX` sont sans risque : la PK conserve son propre index. Il faut
cependant retirer `index=True` des modèles **dans la même révision**, sinon
l'autogénération d'Alembic les recréera.

## Validation
- Q-SCH-006 : 0 ligne.
- Q-SCH-007 : 0 ligne.
- Q-PERF-013 à 016 rejouées : `Index Scan` ou `Bitmap Index Scan` avec une
  `Index Cond`.
- `GET /api/invoices` émet 2 requêtes, quel que soit N.

## Effort estimé
S.

## Dépendances
AUDIT-DB-015.

## Findings liés
AUDIT-DB-003, AUDIT-DB-011, AUDIT-DB-012.
