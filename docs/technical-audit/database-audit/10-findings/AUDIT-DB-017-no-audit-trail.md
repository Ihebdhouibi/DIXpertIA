# AUDIT-DB-017 — Aucune traçabilité : ni journal d'audit, ni auteur des décisions

## Sévérité
MEDIUM

**Justification :**
- **Impact :** il est impossible de répondre à « qui a fait quoi, quand » pour
  une facture, une décision de congé, une création de compte, un changement de
  rôle ou une connexion. Pour un système qui manipule la **paie** et la
  **comptabilité**, c'est un manque de contrôle interne.
- **Ce qui justifie MEDIUM :** ce n'est pas exploitable en soi, mais le défaut
  empêche de **détecter** et d'**instruire** les abus permis par AUDIT-DB-002,
  003 et 004.

## Catégorie
Sécurité / Conformité / Contrôle interne

## Statut
OPEN · CONFIRMED

## Résumé
- Aucune table d'audit, aucun horodatage de modification, aucun champ « modifié
  par ».
- La seule colonne de traçabilité, `leave_requests.valide_par_id`, n'est
  **jamais renseignée** par le code actif.
- PostgreSQL ne journalise ni les connexions ni les requêtes.

## Détails techniques
- Q-DISC-005, Q-SCH-001 : aucune table `audit_*` ou `*_history`, et aucune
  colonne `updated_at` ou `updated_by`.
- `invoices.cree_par_id` existe mais est nullable (AUDIT-DB-016).
- `leave_requests.valide_par_id` n'est positionné que par le router non monté
  (`app/routers/leaves.py:57`). T-B09 n'a rien écrit.
- Q-SEC-006 : `log_connections = off`, `log_disconnections = off`,
  `log_statement = none`.
- Le logger applicatif n'a pas de handler, et ne trace aucune action métier.

## Impact métier
- **Une approbation ou un refus de congé ne peut pas être attribué.**
- **La modification d'une facture ou d'un bulletin ne laisse aucune trace**, le
  jour où elle sera possible.
- **En cas d'incident**, par exemple un accès par un compte « supprimé »
  (AUDIT-DB-004), il n'existe aucun élément pour l'établir.

## Preuves
`11-evidence/schema/*` (Q-SCH-001) ; `11-evidence/sql-results/05-security.results.md`
(Q-SEC-006) ; T-B09.

## Composants concernés
Toutes les tables métier ; `main.py` ; configuration de PostgreSQL.

## Localisation
- **Code :** `main.py` (aucun appel de journalisation métier) ;
  `app/routers/leaves.py:57`.
- **Base :** absence de tables d'audit ; paramètres `log_*`.

## Cause racine
La traçabilité n'a pas été spécifiée comme exigence.

## Recommandation
1. Ajouter des colonnes `created_at`, `created_by`, `updated_at` et
   `updated_by` aux tables métier.
2. Créer une table **`audit_events`** (`id`, `occurred_at`, `actor_id`,
   `action`, `entity`, `entity_id`, `before`, `after` en JSONB), alimentée par
   l'application pour les actions sensibles :
   - création, émission et décision sur une facture ;
   - décision de congé ;
   - création, désactivation et changement de rôle d'un compte ;
   - réinitialisation de mot de passe.
3. Côté PostgreSQL : `log_connections = on`. Envisager `pgaudit` si une exigence
   de conformité le demande.
4. Accès en lecture au journal réservé à l'admin. Aucune modification ni
   suppression possible par le rôle applicatif : `INSERT` seulement.

## Correctif proposé
Une migration crée `audit_events`, puis un service applicatif unique
`record_event(actor, action, entity, before, after)` est appelé dans les
endpoints concernés.

## Risques du correctif
Le journal contiendra des données personnelles. Sa durée de conservation et son
accès doivent être définis (`06-security/security-static-analysis.md` § 7).

## Validation
Chaque action listée produit une ligne `audit_events`, et le rôle applicatif ne
peut ni modifier ni supprimer une ligne du journal.

## Effort estimé
M.

## Dépendances
AUDIT-DB-015 (migrations) ; AUDIT-DB-006 (droits du rôle applicatif).

## Findings liés
AUDIT-DB-002, AUDIT-DB-004, AUDIT-DB-011, AUDIT-DB-021.
