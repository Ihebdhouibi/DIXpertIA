# AUDIT-DB-003 — `/api/data` expose toutes les données à tout utilisateur connecté

## Sévérité
HIGH

**Justification :**
- **Exploitabilité :** un utilisateur **authentifié**, quel que soit son rôle,
  lit des données au-delà de ses droits. Le critère HIGH est rempli.
- **Impact :** il lit les données comptables (factures), personnelles (tous les
  comptes) et potentiellement de santé (motifs de congé, arrêts maladie).
- **Probabilité :** certaine dès qu'un utilisateur appelle l'endpoint.
- **Ce qui justifie HIGH plutôt que CRITICAL :** l'accès exige un compte.

## Catégorie
Sécurité / Contrôle d'accès horizontal et vertical

## Statut
OPEN · CONFIRMED

## Résumé
`GET /api/data` n'a aucun contrôle de rôle. Il renvoie à **tout** utilisateur
connecté **tous** les comptes, **toutes** les factures, **toutes** les demandes
de congé, tous les appareils et tous les membres d'équipe. Seuls les bulletins
de paie sont filtrés pour le rôle `employee`.

## Détails techniques
- La fonction `main.py:492-518` exécute 6 requêtes `.all()`, sans filtre.
- La sérialisation `_row()` (`main.py:120-129`) retire bien `hashedPassword`,
  `resetToken` et `resetTokenExpiry` (T-A06). **Ce contrôle fonctionne.**
- La sérialisation fonctionne par **liste d'exclusion** : toute nouvelle colonne
  sensible serait exposée par défaut (voir AUDIT-DB-020).
- Le router `invoicing` protège correctement `/api/invoices` et `/api/clients`
  (T-B02, T-B03 : 403 pour un employé). **Cette protection est contournée** par
  `/api/data`, qui renvoie les mêmes factures.

## Impact métier
- **Un employé lit la comptabilité de l'entreprise** : montants, clients, dates.
- **Un employé lit la liste complète du personnel**, avec e-mail, rôle et
  département.
- **Un employé et la comptable lisent toutes les demandes de congé**, motif et
  type `maladie` compris. Le ticket #47 a retiré les congés à la comptable
  **dans l'interface seulement**.
- Les arbitrages des tickets #10, #12 et #47 sont donc inopérants côté serveur.

## Preuves
- **T-B01** : jeton `employee` → 200, avec 7 comptes renvoyés.
- **T-B07** : la réponse contient les factures `FA-2026-0001` et `FA-2026-0002`.
  Le jeton utilisé est celui d'un employé (son jeton de réinitialisation).
- **T-A06** : liste des champs utilisateur renvoyés, sans aucun secret.

Les preuves sont dans `11-evidence/api-tests/api-tests.results.md`.

## Composants concernés
`main.py` (`get_data`, `_row`), tables `users`, `invoices`, `leave_requests`,
`devices`, `team_members` et `payslips`.

## Localisation
- **Code :** `main.py:492-518`, `:116-129`.
- **Base :** 6 tables.

## Cause racine
L'endpoint unique « tout charger » vient du stockage JSON d'origine, où le
frontend recevait toute la base. Il a été conservé lors de la migration vers
PostgreSQL, avec un filtre ajouté pour les seuls bulletins.

## Recommandation
**Supprimer `/api/data`.** Le remplacer par des endpoints par entité, dont
chacun applique sa règle d'accès et dont les sorties sont définies par des
**schémas Pydantic explicites** (liste d'autorisation), plutôt que par
`obj.__dict__`.

## Correctif proposé
1. Créer des endpoints par entité :
   - `GET /api/me/payslips` (l'employé) ;
   - `GET /api/payslips` (comptable, admin) ;
   - `GET /api/leave-requests` (l'employé voit les siennes, l'admin toutes) ;
   - `GET /api/users` (admin ; comptable en lecture, à confirmer par le métier).
2. Utiliser un `response_model` par sortie.
3. Supprimer `_row()` et `/api/data`. **Le frontend ne l'appelle pas**
   (AUDIT-DB-001), donc la suppression est sans régression.

## Risques du correctif
**Nul pour l'interface actuelle**, qui n'utilise pas l'endpoint. La seule
contrainte : les nouveaux endpoints doivent exister avant le raccordement du
frontend (AUDIT-DB-001).

## Validation
- Rejouer T-B01 : **404**, ou **403**, attendu.
- Pour chaque nouvel endpoint, un test par rôle : employé, comptable, admin et
  anonyme.

## Effort estimé
M.

## Dépendances
Aucune pour la suppression. Les endpoints de remplacement dépendent
d'AUDIT-DB-013.

## Findings liés
AUDIT-DB-001, AUDIT-DB-005 (le jeton de réinitialisation ouvre aussi cet
endpoint), AUDIT-DB-018 (coût : 6 lectures intégrales), AUDIT-DB-020.
