# AUDIT-DB-013 — Modèle de données scindé entre l'API et l'ORM : des routes plantent, d'autres écrivent dans le vide

## Sévérité
HIGH

**Justification :**
- **Impact :** des fonctions centrales sont **inopérantes**, et le confirment à
  l'exécution :
  - création de congé → 500 ;
  - toute la gestion des appareils, **même pour l'admin** → 500 ;
  - décision sur un congé → réponse de succès **sans aucune écriture**.
- **Probabilité :** certaine.
- **Critère HIGH rempli :** une fonctionnalité centrale est inopérante.
- **Aggravation :** la réponse de succès sans effet trompe l'utilisateur.

## Catégorie
Architecture / Cohérence ORM ↔ API

## Statut
OPEN · CONFIRMED

## Résumé
Deux vocabulaires incompatibles coexistent :
- l'API héritée (`main.py`) et le frontend parlent **camelCase anglais**
  (`employeeName`, `dates`, `status`, `amount`) ;
- les modèles `LeaveRequest`, `Invoice` et `Payslip` sont en **snake_case
  français** (`date_debut`, `statut`, `montant_ttc`).

Le code construit ou modifie des objets avec des attributs qui n'existent pas.
S'y ajoutent :
- **4 routers non montés**, du code mort qui ne s'importe pas toujours ;
- **deux piles d'authentification** ;
- des types Pydantic incohérents avec les colonnes.

## Détails techniques

| Défaut | Code | Preuve à l'exécution |
|---|---|---|
| `LeaveRequest(employeeId=…, employeeName=…, dates=…)` | `main.py:338-348` | T-A03 : `TypeError: 'employeeId' is an invalid keyword argument for LeaveRequest` |
| `leave.status = 'Approved'` (la colonne est `statut`) ; `leave.rejectionReason` (la colonne est `commentaire_validation`) | `main.py:359`, `:368-369` | T-B09 : 200 « approved successfully », statut en base **inchangé** |
| `current_user['role']` sur un objet `User` | `main.py:395`, `:429`, `:435`, `:459`, `:475` | T-A05 : `TypeError: 'User' object is not subscriptable` |
| `Invoice(id=str, client=…, amount=…, items=JSON, deviceIds=…)` | `main.py:402-413` | code mort, masqué par le router |
| `Payslip(period=…, grossPay=…)` | `migrate_data.py:40-46` | plantage documenté dans la PR #35 |
| `PayslipOut.employee_id: int` et `LeaveRequestOut.employee_id: int`, pour des colonnes VARCHAR `USR-NNN` | `app/schemas/payroll.py:7`, `leaves.py:25` | non exécuté (routers non montés) |
| `from app.models.user import RoleEnum` (inexistant) | `app/schemas/user.py:5` | le module est impossible à importer |
| Routers `auth`, `leaves`, `payroll` et `services` non montés ; ils utilisent `User.employee_profile`, `hashed_password` et `first_name`, qui n'existent pas | `app/routers/*.py` | `openapi.json` : non exposés |
| Deux `get_current_user` et deux `create_access_token` | `main.py:94-114` ; `app/core/deps.py`, `security.py` | — |

**Seule entité cohérente de bout en bout :** `TeamMember`
(`04-models/orm-api-frontend-mapping.md`).

## Impact métier
- **Congés :** impossible d'en créer par l'API, et les décisions ne sont pas
  enregistrées.
- **Appareils :** module entièrement inutilisable, alors que le ticket #18 est
  fermé.
- **Paie :** aucune route ne permet de créer ou de lister des bulletins, hors
  `/api/data`.
- **Coût de maintenance :** il faut savoir quelle moitié du code est vivante.
  Des contrôles d'accès écrits dans le code mort donnent l'illusion d'une
  protection.

## Preuves
- `11-evidence/api-tests/api-tests.results.md` : T-A03, T-A05 et T-B09, avec
  les causes vérifiées dans le log du backend.
- `04-models/orm-api-frontend-mapping.md`, `04-models/orm-vs-database.md` § 3.

## Composants concernés
`main.py`, `app/routers/*`, `app/schemas/*`, `migrate_data.py`, `src/types.ts`.

## Localisation
- **Code :** voir le tableau.
- **Base :** `leave_requests`, `invoices`, `payslips`, `devices`.

## Cause racine
La migration du stockage JSON vers PostgreSQL a introduit un schéma métier en
français, **sans adapter l'API** qui le consomme. Les routers prévus pour ce
schéma ont été écrits, mais jamais branchés. C'est le sujet du ticket ouvert #37.

## Recommandation
**Trancher le ticket #37 avant toute autre évolution du modèle.**
1. **Choisir un vocabulaire unique** pour le schéma, l'ORM et l'API. Les
   données métier étant françaises et le code anglais, l'option la plus simple
   est un schéma **snake_case**, quelle que soit la langue retenue. L'API expose
   alors des noms stables via des schémas Pydantic (`alias` camelCase si le
   frontend le souhaite).
2. **Une seule implémentation** par route et par fonction transverse
   (authentification, hachage, jetons).
3. **Supprimer le code mort**, ou le monter après correction. Ne jamais le
   laisser en l'état.

## Correctif proposé
1. Décision sur le #37.
2. Réécrire les routes de `main.py` dans des routers, sur les modèles existants
   (`date_debut`, `statut`…), avec des schémas d'entrée et de sortie Pydantic
   par route.
3. Monter les routers `leaves` et `payroll` corrigés. Créer, ou abandonner
   explicitement, la fiche employé (`employee_profile`, AUDIT-DB-016).
4. Supprimer :
   - `main.py:393-423`, `:58-114` (doublons) ;
   - `app/schemas/user.py`, ou le corriger ;
   - `migrate_data.py`.
5. Ajouter des tests d'API : il n'en existe aucun (AUDIT-DB-022).

## Risques du correctif
- **Le corriger avant AUDIT-DB-002 rendrait l'approbation anonyme effective.**
  Les deux doivent être livrés ensemble.
- Le frontend n'appelle pas ces routes (AUDIT-DB-001) : pas de régression
  visible, mais aussi aucune validation par l'usage. D'où l'importance des tests.

## Validation
- Rejouer T-A03 et T-A05 : plus d'erreur 500.
- Rejouer T-B09 avec un jeton admin : le statut passe à `APPROUVE` en base, et
  `valide_par_id` est renseigné.
- `python -c "import app.schemas.user"` réussit, ou le module n'existe plus.

## Effort estimé
L.

## Dépendances
Décision du ticket #37. AUDIT-DB-002 doit être livré en même temps.

## Findings liés
AUDIT-DB-001, AUDIT-DB-002, AUDIT-DB-010, AUDIT-DB-016, AUDIT-DB-022.
