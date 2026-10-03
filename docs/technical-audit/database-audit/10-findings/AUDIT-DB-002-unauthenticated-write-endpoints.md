# AUDIT-DB-002 — Endpoints d'écriture accessibles sans authentification

## Sévérité
CRITICAL

**Justification :**
- **Exploitabilité :** maximale. Aucun jeton n'est exigé, et une simple requête
  HTTP suffit (T-B08 l'a prouvé).
- **Portée :** quiconque peut joindre l'API.
- **Impact :**
  - écriture **effective** de données personnelles dans `team_members` ;
  - approbation et refus de congés acceptés anonymement.
- **Probabilité :** l'approbation anonyme est aujourd'hui **sans effet**, mais
  seulement à cause d'un autre bug (le nom de colonne erroné). Elle deviendra
  effective dès que ce bug sera corrigé, ce qui est une correction probable et
  attendue.

C'est le seul défaut de l'audit qui remplit le critère CRITICAL :
exploitable **sans authentification**, avec impact sur l'**intégrité** de
données du personnel.

## Catégorie
Sécurité / Contrôle d'accès

## Statut
OPEN · CONFIRMED

## Résumé
Quatre endpoints qui écrivent en base n'ont **aucune dépendance
d'authentification** : la création d'un membre d'équipe, la création d'une
demande de congé, son approbation et son refus.

## Détails techniques

| Endpoint | Code | Test | Observé |
|---|---|---|---|
| `POST /api/team-members` | `main.py:373-391` | T-B08 | **201** sans jeton : la ligne `TM-00001` est créée |
| `POST /api/leave-requests/{id}/approve` | `main.py:354-361` | T-A01, T-B09 | **404** sans jeton (le traitement s'exécute) ; **200** « approved successfully » sur une demande réelle |
| `POST /api/leave-requests/{id}/reject` | `main.py:363-371` | T-A02 | **404** sans jeton |
| `POST /api/leave-requests` | `main.py:335-352` | T-A03 | **500** sans jeton : aucune authentification, et l'appelant fournit `employeeId` |

Aucune de ces fonctions ne déclare `Depends(get_current_user)`.

## Impact métier
- **N'importe qui peut injecter des personnes** dans l'annuaire de l'équipe.
  Les chaînes ne sont limitées ni en longueur ni en nombre : pollution massive,
  ou contenu malveillant affiché à tous.
- **Les décisions de congé ne sont pas protégées.** Une personne extérieure ou
  un employé pourra approuver ses propres congés, ou refuser ceux des autres,
  dès que le bug de nom de colonne d'AUDIT-DB-013 sera corrigé.
- **Création de demandes au nom d'un autre** (`employeeId` fourni par
  l'appelant), quand l'endpoint ne plantera plus.

## Preuves
- `11-evidence/api-tests/api-tests.results.md` : T-A01, T-A02, T-A03, T-B08 et T-B09.
- T-B09 : `{"message":"Leave request approved successfully"}`, avec un statut en
  base resté à `LeaveStatus.EN_ATTENTE`.
- Ligne créée anonymement : `team_members.id = TM-00001` (`AUDIT-TEST`,
  conservée).

## Composants concernés
`main.py` (API héritée), tables `team_members` et `leave_requests`.

## Localisation
- **Code :** `main.py:335`, `:354`, `:363`, `:373`.
- **Base :** `team_members`, `leave_requests`.

## Cause racine
L'authentification est déclarée **endpoint par endpoint**, et non au niveau du
router ou de l'application. Un oubli n'est détecté par rien : il n'y a aucun
test automatisé (AUDIT-DB-022).

## Recommandation
Inverser le défaut : **toute route exige l'authentification**, et seules les
routes explicitement publiques (`/api/login`, `/api/forgot-password`,
`/api/reset-password`) en sont exemptées. Chaque route d'écriture vérifie en
plus le rôle.

## Correctif proposé
1. Déplacer les routes de `main.py` dans des routers dotés de
   `dependencies=[Depends(get_current_user)]`.
2. Exiger `require_roles("admin")` pour les décisions de congé et la création
   de membres d'équipe.
3. Pour la création de congé, dériver `employee_id` de `current_user.id`, et ne
   jamais le lire dans le corps de la requête.
4. Ajouter un test automatisé qui énumère `app.routes` et échoue si une route
   non listée comme publique n'a pas de dépendance d'authentification.

## Risques du correctif
- **Faible.** Le frontend n'appelle aucun de ces endpoints (AUDIT-DB-001) :
  aucune régression visible.
- La ligne anonyme `TM-00001` reste à nettoyer, avec accord.

## Validation
- Rejouer T-A01, T-A02, T-A03 et T-B08 : **401** attendu.
- Rejouer T-B09 avec un jeton `employee` : **403** attendu ; avec un jeton
  `admin` : 200, **et** le statut en base passe à `APPROUVE`.

## Effort estimé
S, à condition de le faire avec le correctif d'AUDIT-DB-013.

## Dépendances
Aucune pour la protection. La correction des champs (AUDIT-DB-013) doit suivre
**ou** accompagner ce correctif, **jamais le précéder** : elle rendrait
l'approbation anonyme effective.

## Findings liés
AUDIT-DB-013 (champs inexistants), AUDIT-DB-017 (aucune trace du valideur).
