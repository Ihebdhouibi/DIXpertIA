# AUDIT-DB-001 — La base n'est pas la source de vérité : les données métier vivent dans le navigateur

## Sévérité
HIGH

**Justification :**
- **Impact :** les données métier ne sont ni partagées entre utilisateurs, ni
  durables, ni soumises aux règles du serveur. La fonction centrale du produit,
  où la comptable traite les factures émises par l'admin, est donc inopérante.
- **Portée :** factures, congés, bulletins, équipe, projets, notifications et
  gestion des comptes.
- **Probabilité :** certaine, car c'est le fonctionnement nominal.
- **Ce qui justifie HIGH plutôt que CRITICAL :** il ne s'agit pas d'une faille
  exploitable, mais d'une fonctionnalité centrale qui ne fonctionne pas.
- **Ce qui ferait passer en CRITICAL :** si des données réelles sont saisies
  dans l'application aujourd'hui, vider le cache du navigateur les **perd**.
  Cela relève du critère « perte de données ». Le point est
  `UNKNOWN / NEEDS VERIFICATION` : l'audit ne sait pas si la plateforme est déjà
  utilisée en production.

## Catégorie
Architecture / Cohérence applicative

## Statut
OPEN · CONFIRMED

## Résumé
Hors authentification, création de compte et PDF de facture, le frontend
n'appelle jamais l'API. Il initialise ses données à partir de jeux fictifs codés
en dur (`src/data.ts`), les modifie dans l'état React et les persiste dans le
`localStorage`. La base PostgreSQL ne voit donc pratiquement aucune donnée
métier.

## Détails techniques
- Le frontend contient **5 appels** `fetch(` au total : `/api/login`,
  `/api/users`, `/api/forgot-password`, `/api/reset-password` et
  `/api/invoices/{id}/download`.
- **`GET /api/data`**, le seul endpoint qui renvoie les données métier, **n'est
  jamais appelé**.
- 8 clés de `localStorage` servent de stockage : `dixpertia_user`, `_payslips`,
  `_leave_requests`, `_team_members`, `_invoices`, `_projects`, `_users` et
  `_notifications`.
- Les gestionnaires d'actions modifient l'état local seulement :
  `handleAddInvoice` (`App.tsx:340`), `handleApproveLeave` (`:292`),
  `handleAddEmployee` (`:327`), `handleEditUser` et `handleDeleteUser`
  (`:485-493`), ainsi que les projets (`:355-399`).
- Le téléchargement du PDF ne fonctionne que si l'`id` fictif du `localStorage`
  (`INV-2024-00N`) coïncide par hasard avec un `numero` en base.

## Impact métier
- **La comptable ne voit pas les factures de l'admin :** chacun voit le contenu
  de son propre navigateur.
- **Rien n'est sauvegardé côté serveur :** changer de poste, de navigateur, ou
  vider son cache fait disparaître les données.
- **Aucune règle serveur ne s'applique** aux actions de l'interface : droits,
  validations, numérotation.
- **Toute la couche base de données auditée ici n'est, en pratique, pas
  utilisée.** Ses défauts n'ont donc pas encore produit de dégâts, mais ils en
  produiront dès qu'elle sera branchée.

## Preuves
- Inventaire des appels : `grep -rn "fetch(" src` → 5 résultats
  (`02-discovery/application-data-flow.md`).
- Persistance : `src/App.tsx:74-196`.
- Données fictives : `src/data.ts:3`, `:15`, `:51`, `:108`, `:163`.
- Base vide de toute donnée métier avant l'audit : Q-DISC-005 (users = 4,
  toutes les autres tables à 0).

## Composants concernés
`src/App.tsx`, `src/data.ts`, toutes les vues de `src/components/`, `GET /api/data`.

## Localisation
- **Code :** `src/App.tsx:74-196`, `:270-399`, `:485-493`.
- **Base :** l'ensemble des tables métier.

## Cause racine
Le frontend vient d'un prototype Google AI Studio (`metadata.json`), conçu avec
des données locales. Le backend a été construit ensuite, sans que le frontend y
soit raccordé.

## Recommandation
Faire de l'API la seule source de vérité :
- chaque vue lit et écrit via des endpoints dédiés ;
- le `localStorage` ne conserve que des préférences d'interface (thème) et,
  éventuellement, le jeton.

**Ce chantier dépend des corrections du modèle de données** (AUDIT-DB-013) :
brancher l'interface sur l'API actuelle reproduirait les erreurs prouvées.

## Correctif proposé
1. Corriger d'abord le modèle et l'API : AUDIT-DB-012, AUDIT-DB-013, AUDIT-DB-014.
2. Créer des endpoints de lecture et d'écriture par entité, paginés et filtrés,
   en remplacement de `/api/data` (AUDIT-DB-003).
3. Raccorder chaque vue, entité par entité, en commençant par les factures,
   besoin central de la comptable.
4. Supprimer `src/data.ts` et les persistances `localStorage` de données
   métier.

## Risques du correctif
- Si l'application est déjà utilisée, les données présentes dans des
  `localStorage` seront perdues. Il faut d'abord prévoir un export.
- Le raccordement fera apparaître immédiatement les défauts de l'API.
  L'ordonnancement ci-dessus évite ce piège.

## Validation
- Une facture créée par l'admin est visible par la comptable depuis un autre
  navigateur.
- Vider le `localStorage` ne fait disparaître aucune donnée métier.
- `grep -rn localStorage src` ne renvoie plus que le jeton et le thème.

## Effort estimé
XL : c'est un chantier par entité, qui dépend d'AUDIT-DB-013.

## Dépendances
AUDIT-DB-012, AUDIT-DB-013, AUDIT-DB-014, AUDIT-DB-003.

## Findings liés
AUDIT-DB-004 (révocation locale seulement), AUDIT-DB-011 (circuit comptable
absent), AUDIT-DB-013.
