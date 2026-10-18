# AUDIT-DB-005 — Le jeton de réinitialisation sert de jeton de session et il est stocké en clair

## Sévérité
MEDIUM

**Justification :**
- **Exploitabilité :** conditionnelle. Il faut d'abord obtenir un jeton de
  réinitialisation : e-mail intercepté, historique du navigateur (le jeton est
  dans l'URL), ou lecture de la table `users`.
- **Impact :** un tel jeton permet déjà de changer le mot de passe. Le gain
  réel pour un attaquant est donc un **accès discret** de 60 minutes, **sans**
  changer le mot de passe, et donc sans alerter la personne. S'y ajoute une
  prise de contrôle de compte pour quiconque **lit** la base.
- **Ce qui justifie MEDIUM :** le risque est réel mais conditionnel, ce qui
  correspond au critère MEDIUM.

## Catégorie
Sécurité / Authentification

## Statut
OPEN · CONFIRMED

## Résumé
Le jeton de réinitialisation est un JWT signé avec la **même clé** que les
jetons de session, et il contient le même claim `sub`. Aucun `get_current_user`
ne vérifie le type du jeton (`purpose`). Il est donc accepté comme jeton de
session.

Il est par ailleurs stocké **en clair** dans `users.resetToken`, et aucune règle
de complexité ne s'applique au nouveau mot de passe.

## Détails techniques
- La création du jeton se fait en `main.py:277-281` :
  `{"sub": user.id, "exp": +1h, "purpose": "reset"}`, avec `SECRET_KEY` et
  HS256.
- La vérification d'un jeton de session, en `main.py:107-114` et
  `app/core/deps.py:13-30`, lit seulement `sub`, jamais `purpose`.
- Le stockage se fait dans `users.resetToken`, de type `character varying`
  (Q-SCH-001), sans hachage.
- `ResetPasswordRequest.newPassword: str` n'impose aucune contrainte
  (`main.py:183-185`).
- Points positifs :
  - une nouvelle demande écrase l'ancien jeton ;
  - le jeton est vérifié contre la valeur stockée, puis effacé après usage
    (`main.py:317-324`).

## Impact métier
- Quelqu'un qui obtient un lien de réinitialisation peut consulter les données
  du compte pendant une heure, sans laisser la trace d'un changement de mot de
  passe.
- Une fuite de la table `users` (export, sauvegarde, accès en lecture) donne la
  main sur tout compte qui a un jeton en cours.

## Preuves
- **T-B07** : `GET /api/data` avec le `resetToken` de `USR-008` en `Bearer` →
  **200**, avec les factures dans la réponse.
- Q-SCH-001 : type de `users.resetToken`.

## Composants concernés
`main.py` (`forgot_password`, `reset_password`, `get_current_user`),
`app/core/deps.py`, `users.resetToken`.

## Localisation
- **Code :** `main.py:271-326`, `:107-114` ; `app/core/deps.py:13-30`.
- **Base :** `users.resetToken`, `users.resetTokenExpiry`.

## Cause racine
Les jetons de session et de réinitialisation partagent la même clé et la même
forme, sans claim discriminant vérifié.

## Recommandation
1. Séparer les types de jeton : refuser en session tout jeton qui porte
   `purpose`. Mieux encore, utiliser un jeton de réinitialisation **opaque et
   aléatoire**, et non un JWT.
2. Ne stocker que le **hash** (SHA-256) du jeton de réinitialisation.
3. Imposer une politique minimale sur le nouveau mot de passe.
4. Invalider les sessions existantes après la réinitialisation (AUDIT-DB-004).

## Correctif proposé
- `get_current_user` : `if payload.get("purpose"): raise 401`.
- `forgot_password` :
  - `token = secrets.token_urlsafe(32)` ;
  - stocker `sha256(token)` ;
  - envoyer `token`.
- `reset_password` : comparer `sha256(req.token)`, en temps constant.
- Pydantic : `newPassword: constr(min_length=12)`, plus toute règle décidée par
  le métier.

## Risques du correctif
Les jetons de réinitialisation déjà émis deviennent invalides. Q-INT-007 en
compte 0 aujourd'hui : aucun impact.

## Validation
- Rejouer T-B07 : **401** attendu.
- Après une réinitialisation, l'ancien jeton de session reçoit **401**.
- En base, `users.resetToken` ne contient plus qu'un hash.

## Effort estimé
S.

## Dépendances
AUDIT-DB-004 (mécanisme d'invalidation des sessions).

## Findings liés
AUDIT-DB-003, AUDIT-DB-004, AUDIT-DB-007 (même clé de signature).
