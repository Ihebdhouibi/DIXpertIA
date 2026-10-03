# Résultats — tests d'exécution de l'API

- **Exécuté le :** 2026-10-02T11:41:57
- **Cible :** `http://127.0.0.1:8000` (backend local), base `dixpertia` locale
- **Script :** `01-requests/scripts/run_api_tests.py`
- **Jetons, hash et mots de passe :** masqués dans tous les corps de réponse

## Synthèse

| Test | Observation | Verdict | HTTP |
|---|---|---|---|
| T-A01 | OBS-006 | CONFIRMED | 404 |
| T-A02 | OBS-006 | CONFIRMED | 404 |
| T-A03 | OBS-008 | CONFIRMED | 500 |
| T-A04 | — | INFO | 200 |
| T-A05 | OBS-010 | CONFIRMED | 500 |
| T-A06 | OBS-009 | INFO | 200 |
| T-A07 | OBS-021 | CONFIRMED | 500 |
| T-A08 | OBS-014 | REFUTED (configuration locale) | 401 |
| T-A09 | OBS-018 | CONFIRMED | 401 |
| T-B01 | OBS-009 · R-FAC-05 · R-USR-06 | CONFIRMED | 200 |
| T-B02 | contrôle | CONTROL OK | 403 |
| T-B03 | contrôle | CONTROL OK | 403 |
| T-B04 | OBS-011 · R-USR-03 | CONFIRMED | 200 |
| T-B05.1 | R-FAC-01 · OBS-020 | CONFIRMED | 500 |
| T-B05.2 | R-FAC-01 · OBS-020 | CONFIRMED | 500 |
| T-B05.db | OBS-020 | CONFIRMED | 0 |
| T-B06 | contrôle | CONTROL OK | 403 |
| T-B07 | OBS-012 | CONFIRMED | 200 |
| T-B08 | OBS-007 · R-EQP-01 | CONFIRMED | 201 |
| T-B09 | OBS-006 · R-CNG-02 | CONFIRMED | 200 |

## Détail

### T-A01 — Décider d'un congé sans être authentifié.

- **Observation testée :** OBS-006
- **Requête :** `POST /api/leave-requests/999999/approve — sans jeton`
- **Résultat attendu (comportement sûr) :** 401 (authentification exigée).
- **Résultat observé :** HTTP 404
- **Verdict :** **CONFIRMED**
- **Lecture :** Un 404 prouve que le traitement s'exécute sans authentification : l'id inexistant est cherché en base.

```text
{"detail":"Leave request not found"}
```

### T-A02 — Décider d'un congé sans être authentifié.

- **Observation testée :** OBS-006
- **Requête :** `POST /api/leave-requests/999999/reject — sans jeton`
- **Résultat attendu (comportement sûr) :** 401 (authentification exigée).
- **Résultat observé :** HTTP 404
- **Verdict :** **CONFIRMED**
- **Lecture :** Un 404 prouve que le traitement s'exécute sans authentification : l'id inexistant est cherché en base.

```text
{"detail":"Leave request not found"}
```

### T-A03 — Créer une demande de congé anonymement, au nom d'un autre employé.

- **Observation testée :** OBS-008
- **Requête :** `POST /api/leave-requests — sans jeton, employeeId=USR-001`
- **Résultat attendu (comportement sûr) :** 401.
- **Résultat observé :** HTTP 500
- **Verdict :** **CONFIRMED**
- **Lecture :** Un 500 prouve à la fois l'absence d'authentification et le plantage dû aux champs absents du modèle.

```text
Internal Server Error
```

### T-A04 — Endpoint /logs public.

- **Observation testée :** —
- **Requête :** `GET /logs — sans jeton`
- **Résultat attendu (comportement sûr) :** Information.
- **Résultat observé :** HTTP 200
- **Verdict :** **INFO**

```text
[]
```

### T-A05 — Lister les appareils en tant qu'admin.

- **Observation testée :** OBS-010
- **Requête :** `GET /api/devices — jeton admin`
- **Résultat attendu (comportement sûr) :** 200.
- **Résultat observé :** HTTP 500
- **Verdict :** **CONFIRMED**
- **Lecture :** Un 500 confirme `current_user['role']` sur un objet User.

```text
Internal Server Error
```

### T-A06 — Contenu de /api/data pour un admin : clés et volumes, sans valeurs.

- **Observation testée :** OBS-009
- **Requête :** `GET /api/data — jeton admin`
- **Résultat attendu (comportement sûr) :** Aucune colonne secrète.
- **Résultat observé :** HTTP 200
- **Verdict :** **INFO**

```text
{"payslips": 0, "leaveRequests": 0, "teamMembers": 0, "invoices": 0, "users": 7, "devices": 0, "users[0].keys": ["avatarUrl", "createdAt", "department", "email", "firstName", "id", "isActive", "isVerified", "lastName", "role"]}
```

### T-A07 — Créer un compte en tant qu'admin, avec des id existants non contigus.

- **Observation testée :** OBS-021
- **Requête :** `POST /api/users — jeton admin`
- **Résultat attendu (comportement sûr) :** 201.
- **Résultat observé :** HTTP 500
- **Verdict :** **CONFIRMED**
- **Lecture :** Un 500 confirme la collision d'id `USR-{count()+1}`. Précondition au 2026-10-02 : 7 comptes (USR-001, 003, 005, 006 + AUDIT-TEST 008, 009, 010), donc l'id généré est USR-008, déjà pris. L'état naturel d'avant l'audit (4 comptes, donc USR-005 déjà pris) est prouvé par Q-INT-006.

```text
Internal Server Error
```

### T-A08 — Jeton forgé avec la clé de repli codée en dur dans le dépôt.

- **Observation testée :** OBS-014
- **Requête :** `GET /api/data — jeton forgé`
- **Résultat attendu (comportement sûr) :** 401 (la clé de repli n'est pas celle utilisée).
- **Résultat observé :** HTTP 401
- **Verdict :** **REFUTED (configuration locale)**
- **Lecture :** REFUTED signifie seulement que **cet** environnement définit SECRET_KEY ; le risque reste entier pour tout déploiement qui ne la définirait pas.

```text
{"detail":"Invalid token"}
```

### T-A09 — Énumération des comptes par le temps de réponse de la connexion.

- **Observation testée :** OBS-018
- **Requête :** `8 × POST /api/login par cas`
- **Résultat attendu (comportement sûr) :** Temps comparables.
- **Résultat observé :** HTTP 401
- **Verdict :** **CONFIRMED**
- **Lecture :** médiane compte inconnu = 24 ms ; compte existant = 292 ms

```text
médiane compte inconnu = 24 ms ; compte existant = 292 ms
```

### T-B01 — Un employé lit /api/data (volumes par clé).

- **Observation testée :** OBS-009 · R-FAC-05 · R-USR-06
- **Requête :** `GET /api/data — jeton employee`
- **Résultat attendu (comportement sûr) :** Ni utilisateurs, ni factures, ni congés d'autrui.
- **Résultat observé :** HTTP 200
- **Verdict :** **CONFIRMED**
- **Lecture :** Les factures et les congés sont vides tant que T-B05 et T-B08 n'ont pas créé de lignes ; la clé `users` suffit à prouver la fuite.

```text
{"payslips": 0, "leaveRequests": 0, "teamMembers": 0, "invoices": 0, "users": 7, "devices": 0}
```

### T-B02 — Un employé appelle /api/invoices.

- **Observation testée :** contrôle
- **Requête :** `GET /api/invoices — jeton employee`
- **Résultat attendu (comportement sûr) :** 403.
- **Résultat observé :** HTTP 403
- **Verdict :** **CONTROL OK**

```text
{"detail":"Accès refusé"}
```

### T-B03 — Un employé appelle /api/clients.

- **Observation testée :** contrôle
- **Requête :** `GET /api/clients — jeton employee`
- **Résultat attendu (comportement sûr) :** 403.
- **Résultat observé :** HTTP 403
- **Verdict :** **CONTROL OK**

```text
{"detail":"Accès refusé"}
```

### T-B04 — Connexion d'un compte désactivé (isActive = false).

- **Observation testée :** OBS-011 · R-USR-03
- **Requête :** `POST /api/login — USR-010`
- **Résultat attendu (comportement sûr) :** 401.
- **Résultat observé :** HTTP 200
- **Verdict :** **CONFIRMED**

```text
jeton délivré
```

### T-B05.1 — La comptable crée une facture (tentative 1).

- **Observation testée :** R-FAC-01 · OBS-020
- **Requête :** `POST /api/invoices — jeton accountant`
- **Résultat attendu (comportement sûr) :** 403 (création réservée à l'admin) ; à défaut, 200 avec un statut défini.
- **Résultat observé :** HTTP 500
- **Verdict :** **CONFIRMED**
- **Lecture :** 200 ou 500 = la comptable a pu atteindre la création ; 403 = règle appliquée ; autre = à analyser.

```text
Internal Server Error
```

### T-B05.2 — La comptable crée une facture (tentative 2).

- **Observation testée :** R-FAC-01 · OBS-020
- **Requête :** `POST /api/invoices — jeton accountant`
- **Résultat attendu (comportement sûr) :** 403 (création réservée à l'admin) ; à défaut, 200 avec un statut défini.
- **Résultat observé :** HTTP 500
- **Verdict :** **CONFIRMED**
- **Lecture :** 200 ou 500 = la comptable a pu atteindre la création ; 403 = règle appliquée ; autre = à analyser.

```text
Internal Server Error
```

### T-B05.db — État en base après les deux tentatives.

- **Observation testée :** OBS-020
- **Requête :** `SELECT invoices WHERE client_id = <AUDIT-TEST>`
- **Résultat attendu (comportement sûr) :** Si l'API a répondu 500 : aucune ligne.
- **Résultat observé :** HTTP 0
- **Verdict :** **CONFIRMED**
- **Lecture :** Des lignes au statut NULL après un 500 prouvent l'erreur après commit et le doublon.

```text
[{"id": 8, "numero": "FA-2026-0001", "statut": "None", "cree_par_id": "USR-009"}, {"id": 9, "numero": "FA-2026-0002", "statut": "None", "cree_par_id": "USR-009"}]
```

### T-B06 — Un employé télécharge un PDF de facture.

- **Observation testée :** contrôle
- **Requête :** `GET /api/invoices/{numero}/download — jeton employee`
- **Résultat attendu (comportement sûr) :** 403.
- **Résultat observé :** HTTP 403
- **Verdict :** **CONTROL OK**

```text
{"detail":"Accès refusé"}
```

### T-B07 — Utiliser le jeton de réinitialisation comme jeton de session.

- **Observation testée :** OBS-012
- **Requête :** `GET /api/data — Bearer = resetToken de USR-008`
- **Résultat attendu (comportement sûr) :** 401.
- **Résultat observé :** HTTP 200
- **Verdict :** **CONFIRMED**

```text
{"payslips":[],"leaveRequests":[],"teamMembers":[],"invoices":[{"id":8,"numero":"FA-2026-0001","date_echeance":"2026-11-
```

### T-B08 — Créer un membre d'équipe sans être authentifié.

- **Observation testée :** OBS-007 · R-EQP-01
- **Requête :** `POST /api/team-members — sans jeton`
- **Résultat attendu (comportement sûr) :** 401.
- **Résultat observé :** HTTP 201
- **Verdict :** **CONFIRMED**

```text
{"firstName":"AUDIT-TEST","role":"Contributor","status":"Active","avatarUrl":null,"lastName":"Anonymous","id":"TM-00001","email":"audit-test.anonymous@dixpertia.com","initials":"AA"}
```

### T-B09 — Approuver anonymement une demande réelle, puis relire son statut en base.

- **Observation testée :** OBS-006 · R-CNG-02
- **Requête :** `POST /api/leave-requests/7/approve — sans jeton`
- **Résultat attendu (comportement sûr) :** 401 ; et si accepté, statut = APPROUVE.
- **Résultat observé :** HTTP 200
- **Verdict :** **CONFIRMED**
- **Lecture :** 200 + statut inchangé (EN_ATTENTE) = absence d'authentification ET écriture sans effet.

```text
{"message":"Leave request approved successfully"} | statut en base après appel : LeaveStatus.EN_ATTENTE
```

## Données créées par ce script (marquées AUDIT-TEST, non supprimées)

- users.id=USR-008 (audit.employee@audit-test.example.com) — compte AUDIT-TEST existant réutilisé (mot de passe et isActive réinitialisés)
- users.id=USR-009 (audit.accountant@audit-test.example.com) — compte AUDIT-TEST existant réutilisé (mot de passe et isActive réinitialisés)
- users.id=USR-010 (audit.inactive@audit-test.example.com) — compte AUDIT-TEST existant réutilisé (mot de passe et isActive réinitialisés)
- clients.id=3 (AUDIT-TEST Client)
- invoices.id=8 (FA-2026-0001, statut=None)
- invoices.id=9 (FA-2026-0002, statut=None)
- team_members — {"firstName":"AUDIT-TEST","role":"Contributor","status":"Active","avatarUrl":null,"lastName":"Anonymous","id":"TM-00001"
- leave_requests.id=7 (AUDIT-TEST, statut EN_ATTENTE)
