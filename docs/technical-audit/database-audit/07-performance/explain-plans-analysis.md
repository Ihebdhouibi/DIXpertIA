# Phase 7 — Performance : index et plans d'exécution

> 2026-10-02 · base locale `dixpertia`
>
> **Preuves :**
> - `11-evidence/explain-plans/04-performance.results.md` (Q-PERF-001 à 017) ;
> - `11-evidence/schema/02-schema-inventory.results.md` (Q-SCH-005 à 007).

## 1. Méthode, et sa limite

Les tables étant vides, le planificateur choisit spontanément un parcours
séquentiel, quel que soit l'index disponible. Les plans de Q-PERF-005 à 012
**ne mesurent donc rien**.

Pour savoir si un index est **utilisable**, Q-PERF-013 à 017 désactivent les
parcours séquentiels pour la durée de la requête (`SET LOCAL enable_seqscan = off`).
Si le plan reste un `Seq Scan`, avec un coût artificiel de l'ordre de 10¹⁰,
**aucun index ne peut servir la requête**. C'est une preuve structurelle,
indépendante du volume.

Aucune mesure de temps n'a été faite : elle n'aurait pas de sens sur des
tables vides.

## 2. Inventaire des index (Q-SCH-005 à 007)

| | Nombre |
|---|---|
| Index au total | 21 |
| Index de clé primaire | 9 |
| **Index redondants**, un `ix_<table>_id` en double de la PK sur chaque table | **9** (Q-SCH-006) |
| Index uniques métier | 3 : `users.email`, `invoices.numero`, `payslips (employee_id, periode)` |
| **Clés étrangères sans index** | **5 sur 6** : `invoices.client_id`, `invoices.cree_par_id`, `invoice_items.invoice_id`, `leave_requests.employee_id`, `leave_requests.valide_par_id` (Q-SCH-007) |

Les 9 index redondants viennent de `primary_key=True, index=True` dans
**chaque** modèle. Ils doublent le coût d'écriture sur les clés primaires sans
rien apporter.

**Preuve qu'ils sont réellement utilisés à la place de la PK :** pour
`WHERE id = …`, Q-PERF-004 choisit `ix_users_id`, et non `users_pkey`.

## 3. Requêtes critiques

| Requête | Origine | Plan observé | Index utilisable ? |
|---|---|---|---|
| Connexion : `users WHERE email = ?` | `main.py:198` | `Index Scan using ix_users_email` (Q-PERF-003) | ✅ |
| Jeton : `users WHERE id = ?` | `main.py:111` | `Index Scan using ix_users_id`, l'index **redondant** (Q-PERF-004) | ✅, par l'index en double |
| Bulletins d'un employé | `main.py:509` | `Index Scan using uq_employee_periode` (Q-PERF-010) | ✅ |
| **Liste des factures, triée par date** | `invoicing.py:52` | `Sort` + `Seq Scan`, **même forcé** (Q-PERF-013) | ❌ |
| **Factures d'un client** (besoin comptable) | à construire | `Seq Scan`, **même forcé** (Q-PERF-014) | ❌ |
| **Factures d'un mois** (besoin comptable) | à construire | `Seq Scan`, **même forcé** (Q-PERF-015) | ❌ |
| **Lignes d'une facture** | `invoicing.py:109`, et le N+1 de la liste | `Seq Scan`, **même forcé** (Q-PERF-016) | ❌ |
| **Numérotation : `numero LIKE 'FA-2026-%'`** | `invoicing.py:37` | `Bitmap Index Scan on invoices_numero_key` **sans condition d'index**, avec un filtre sur le tas (Q-PERF-017) | ❌ : l'index est parcouru **en entier**. La collation `French_Tunisia.1252` (Q-DISC-002) n'est pas `C`, ce qui empêche le btree standard de servir un `LIKE` préfixe. |
| `/api/data` | `main.py:498-509` | 6 parcours séquentiels intégraux, sans limite | ❌ par conception |

## 4. Statistiques d'usage (Q-PERF-001)

`last_analyze` et `last_autoanalyze` sont NULL sur toutes les tables : aucune
statistique n'a encore été collectée, ce qui est normal pour une base créée la
veille. Les compteurs `seq_scan` et `idx_scan` reflètent uniquement l'activité
de l'audit, et ne sont pas interprétables.

## 5. Conclusion

- **Aucun problème de performance n'est mesurable aujourd'hui**, faute de
  volume.
- **Le schéma ne permet pas de servir efficacement les besoins comptables
  annoncés.** Le tri par date, le filtre par client, le filtre par mois et le
  chargement des lignes n'ont **aucun index utilisable**. La numérotation des
  factures parcourt l'index en entier.
- **9 index sont redondants.** Ils sont à supprimer en même temps que la
  correction des modèles.

Les corrections sont simples : 4 à 6 index, et une génération de numéro sans
`LIKE`. Il est préférable de les faire **avant** de construire le circuit
comptable, plutôt qu'après que l'historique a grossi.
