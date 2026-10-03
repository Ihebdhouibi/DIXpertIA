# AUDIT-DB-004 — La révocation d'accès est inopérante

## Sévérité
HIGH

**Justification :**
- **Exploitabilité :** une personne dont l'accès devait être retiré garde un
  accès complet. C'est un utilisateur authentifié qui agit au-delà de ses
  droits : le critère HIGH est rempli.
- **Impact :** fort dans les scénarios où la révocation compte le plus : départ
  d'un salarié, changement de poste, compte compromis.
- **Probabilité :** certaine. L'interface **affiche la réussite** de l'opération
  alors que le serveur n'a rien fait.

## Catégorie
Sécurité / Gestion des identités et des accès

## Statut
OPEN · CONFIRMED

## Résumé
Il n'existe aucun moyen effectif de retirer un accès :
- **désactiver** un compte (`isActive = false`) n'empêche pas la connexion ;
- **supprimer** un compte ou **changer son rôle** dans l'interface ne modifie
  que le `localStorage` ;
- aucun endpoint serveur n'existe pour ces opérations ;
- les jetons émis ne peuvent pas être révoqués.

## Détails techniques
| Mécanisme | État | Preuve |
|---|---|---|
| `isActive` vérifié à la connexion | ❌ | T-B04 : un compte `isActive = false` obtient un jeton ; code `main.py:198-206` |
| `isActive` vérifié à chaque requête | ❌ | `main.py:107-114`, `app/core/deps.py:13-30` |
| Suppression d'un compte | 🕳 locale seulement | `App.tsx:489-493` (`setUsers(prev => prev.filter(...))`) |
| Modification d'un compte, dont le rôle | 🕳 locale seulement | `App.tsx:485-487` |
| Endpoint serveur de modification, de désactivation ou de suppression | ❌ inexistant | `openapi.json` du 2026-10-01 |
| Révocation de jeton ou déconnexion serveur | ❌ | `App.tsx:239-246` : effacement local seulement |
| Invalidation des sessions après un changement de mot de passe | ❌ | `main.py:303-326` |

**Point positif :** le rôle est **relu en base** à chaque requête (le claim
`role` du jeton est ignoré). Un changement de rôle fait **en base** est donc
pris en compte immédiatement. Le problème est qu'aucun moyen supporté ne permet
de faire ce changement.

## Impact métier
- **Un salarié parti, « supprimé » par l'admin dans l'interface, garde l'accès**
  à l'API. Cumulé avec AUDIT-DB-003, il continue de lire les factures et la
  liste du personnel.
- **L'admin n'a aucun moyen de savoir** que la suppression n'a pas eu lieu : le
  message affiché dit « deleted ».
- **Le seul moyen réel de couper un accès est une intervention SQL directe**,
  ou la réinitialisation du mot de passe par `seed_users.py`. Les jetons déjà
  émis restent alors valides jusqu'à 60 minutes.

## Preuves
- **T-B04** : `POST /api/login` pour `USR-010` (`isActive = false`) → jeton
  délivré.
- Code : `src/App.tsx:485-493` et `:588-589` (gestionnaires passés à `UsersView`).
- Absence d'endpoints : seules les routes `POST /api/users` (création) et
  `/api/login` touchent `users`.

## Composants concernés
`main.py` (`login`, `get_current_user`), `app/core/deps.py`, `src/App.tsx`,
`src/components/UsersView.tsx`, table `users`.

## Localisation
- **Code :** `main.py:195-222`, `:107-114` ; `app/core/deps.py:13-30` ;
  `src/App.tsx:485-493`.
- **Base :** `users.isActive`.

## Cause racine
L'interface a été conçue sur le `localStorage` (AUDIT-DB-001). La colonne
`isActive` a été ajoutée au modèle sans qu'aucune vérification ne s'en serve.

## Recommandation
Implémenter un cycle de vie des comptes **côté serveur** :
- désactivation **effective** ;
- modification du rôle ;
- suppression logique ;
- révocation des sessions.

## Correctif proposé
1. Vérifier `isActive` à la connexion **et** dans `get_current_user`. Un compte
   désactivé reçoit 401, même avec un jeton valide.
2. Ajouter, réservés à l'admin :
   - `PATCH /api/users/{id}` pour le rôle et l'état actif ;
   - `DELETE /api/users/{id}`, sous forme de **désactivation logique**. Les FK
     `NO ACTION` depuis les bulletins et les congés interdisent de toute façon
     la suppression physique (sonde P-29), et la paie doit être conservée.
3. Ajouter `users.tokenVersion` (ou un horodatage `sessionsInvalidatedAt`),
   inclus dans le jeton et comparé à chaque requête. L'incrémenter à la
   désactivation, au changement de rôle et au changement de mot de passe.
4. Raccorder `UsersView` à ces endpoints, et retirer les gestionnaires locaux.
5. Journaliser ces actions (AUDIT-DB-017).

## Risques du correctif
Les 4 comptes réels sont actifs (Q-INT-008), donc la vérification d'`isActive`
ne bloque personne aujourd'hui. Les lignes créées hors ORM ont `isActive` NULL
(AUDIT-DB-014) : il faut décider si NULL vaut actif ou inactif, et ajouter
`NOT NULL DEFAULT true`.

## Validation
- Rejouer T-B04 : **401** attendu.
- Désactiver un compte connecté : son jeton existant reçoit **401** à la
  requête suivante.
- Supprimer un compte dans l'interface : il ne peut plus se connecter, et
  l'action apparaît dans le journal d'audit.

## Effort estimé
M.

## Dépendances
AUDIT-DB-014 (`isActive NOT NULL`), AUDIT-DB-017 (journal).

## Findings liés
AUDIT-DB-001, AUDIT-DB-003, AUDIT-DB-005.
