# Phase 7 — Performance : analyse statique

> 2026-10-01 · `develop` @ `34453a4`
>
> Analyse du code. Les plans `EXPLAIN` (Q-PERF-001 à Q-PERF-012) et la liste
> réelle des index (Q-SCH-005 à Q-SCH-007) seront consignés dans
> `explain-plans-analysis.md` une fois le serveur rétabli.
>
> **Contexte de volume :** quelques utilisateurs, et des tables vides ou
> presque. Aucun de ces points ne pose de problème mesurable aujourd'hui.
> L'analyse porte sur ce qui **se dégradera avec le volume**, notamment
> l'historique des factures qui ne fait que croître.

## 1. Requêtes N+1

| # | Endpoint | Mécanisme | Requêtes pour N factures | Statut |
|---|---|---|---|---|
| P1 | `GET /api/invoices` (`invoicing.py:50-52`) | `response_model=list[InvoiceOut]` sérialise `items` pour chaque facture. `Invoice.items` est en chargement paresseux (`lazy="select"`, valeur par défaut), donc **une requête par facture**. | **1 + N** | CONFIRMED (code) · à mesurer |
| P2 | `POST /api/invoices` (`invoicing.py:79-82`) | `db.refresh(invoice)` puis sérialisation de `items` : 2 requêtes supplémentaires | constant | sans gravité |
| P3 | `GET /api/invoices/{numero}/download` (`invoicing.py:103-119`) | facture, puis `items` (paresseux), puis `client` (paresseux) | 3 | sans gravité |
| P4 | `POST /api/invoices` hérité (`main.py:416-420`, **code mort**) | une requête `SELECT device` par appareil vendu | 1 + D | à corriger s'il est réactivé : `WHERE id IN (...)` |

Correction de P1 : `selectinload(Invoice.items)` dans la requête de liste, ce
qui ramène l'opération à **2 requêtes**, quel que soit N.

## 2. Lectures intégrales et pagination

| # | Endpoint | Ce qui est lu | Pagination | Évolution |
|---|---|---|---|---|
| P5 | **`GET /api/data`** (`main.py:498-509`) | **6 tables entières** : `leave_requests`, `team_members`, `invoices`, `users`, `devices` et `payslips` (toutes pour l'admin et la comptable) | ❌ | La réponse grossit avec **chaque** table. La paie (12 bulletins par salarié et par an) et les factures croissent sans limite. C'est l'endpoint le plus coûteux du système, et il n'est même pas utilisé par l'UI. |
| P6 | `GET /api/invoices` | toutes les factures, avec tri | ❌ | tri complet à chaque appel, sans index sur `date_emission` (Q-PERF-005) |
| P7 | `GET /api/clients` | tous les clients | ❌ | volume modéré |
| P8 | `GET /api/devices` | tous les appareils | ❌ | volume modéré |

**Aucun endpoint de liste n'accepte de filtre ni de pagination** (`limit` /
`offset`, ou curseur). Or les filtres comptables attendus (jour, mois, client)
devront s'exécuter **côté base** pour rester rapides. Aujourd'hui, la seule
possibilité serait de tout charger, puis de filtrer côté client.

## 3. Requêtes coûteuses intégrées aux écritures

| # | Opération | Requête | Coût |
|---|---|---|---|
| P9 | toute création d'utilisateur, d'appareil, de membre ou de congé | `SELECT count(*)` sur la table entière (`main.py:235`, `:337`, `:377`, `:437`) | parcours complet à chaque insertion. Faible en volume absolu, mais inutile : une séquence le remplace, et corrige au passage le défaut d'intégrité T1/T6. |
| P10 | création de facture | `count(*) … WHERE numero LIKE 'FA-AAAA-%'` (`invoicing.py:37`) | parcours complet si l'index sur `numero` n'est pas utilisable pour un `LIKE` préfixe. C'est le cas avec une collation non-C (Q-PERF-009). |

## 4. Index manquants au regard des accès réels

Ce sont les accès que le code émet, ou que le besoin métier impose.
L'existence réelle des index sera vérifiée par Q-SCH-005 et Q-SCH-007.

| Colonne | Accès | Index déclaré dans le modèle ? |
|---|---|---|
| `users.email` | connexion, création, mot de passe oublié | ✅ `unique=True, index=True` |
| `users.id` | chaque requête authentifiée | ✅ PK (`index=True` en plus : doublon probable, Q-SCH-006) |
| `invoices.date_emission` | tri de la liste ; filtres jour et mois | ❌ |
| `invoices.client_id` | filtre client ; jointure | ❌ (FK non indexée) |
| `invoices.statut` | factures « en attente » pour la comptable | ❌ (faible cardinalité ; un index partiel serait pertinent pour le statut « en attente ») |
| `invoice_items.invoice_id` | chargement des lignes (P1, P3) | ❌ (FK non indexée) |
| `invoices.numero` | téléchargement, génération du numéro | ✅ UNIQUE |
| `payslips.employee_id` | bulletins d'un employé | ✅ couvert par `UNIQUE(employee_id, periode)` en première colonne |
| `leave_requests.employee_id` | congés d'un employé | ❌ (FK non indexée) |
| `invoices.cree_par_id`, `leave_requests.valide_par_id` | jointures vers `users` ; suppression d'un utilisateur | ❌ (FK non indexées) |

## 5. Pool de connexions et concurrence

- Le moteur est créé avec les valeurs par défaut : `pool_size=5`,
  `max_overflow=10`, `pool_timeout=30s` et `pool_pre_ping=True`
  (`app/core/database.py:6`).
- Les endpoints synchrones tournent dans le pool de threads d'AnyIO
  (40 threads par défaut). Au-delà de **15 requêtes simultanées** qui utilisent
  la base, les suivantes **attendent** une connexion, jusqu'à 30 s, puis
  échouent.
- `pool_pre_ping=True` ajoute un aller-retour par emprunt de connexion. C'est
  un choix raisonnable.
- À l'échelle actuelle : sans objet. OBSERVATION.

## 6. Synthèse

| Priorité | Point | Pourquoi |
|---|---|---|
| 1 | P5 : `/api/data` | lecture intégrale de 6 tables à chaque appel, et surexposition de données (sécurité). Le supprimer ou le découper règle les deux problèmes. |
| 2 | Index des FK et de `date_emission` | indispensables aux filtres comptables à venir |
| 3 | Pagination et filtres sur les listes | même raison |
| 4 | P1 : N+1 sur les factures | corrigé en une ligne (`selectinload`) |
| 5 | P9 et P10 : `count()` à chaque insertion | à traiter avec la correction des identifiants (séquences) |

Aucun problème de performance n'est **bloquant** aujourd'hui. Tous sont des
coûts qui croîtront avec l'historique comptable. Ils sont peu coûteux à
corriger s'ils le sont **avant** que le circuit des factures ne soit construit
sur l'API.
