# AUDIT-DB-024 — Création de compte : mot de passe provisoire dans la réponse, e-mail envoyé après le commit

## Sévérité
LOW

**Justification :**
- Le mot de passe provisoire ne transite que vers l'**admin** authentifié qui a
  créé le compte. Ce choix est documenté et assumé (`App.tsx:466-468`).
- Il n'est ni journalisé ni persisté dans le navigateur (PR #49).
- Le risque résiduel est faible : interception de la réponse, compte créé dont
  le titulaire n'est pas informé.

## Catégorie
Sécurité / Gestion des identifiants

## Statut
OPEN · CONFIRMED (code)

## Résumé
`POST /api/users` :
- génère un mot de passe provisoire de 10 caractères alphanumériques ;
- enregistre le compte ;
- **valide la transaction** ;
- tente ensuite l'envoi de l'e-mail ;
- **renvoie le mot de passe en clair** dans la réponse.

Si l'e-mail échoue, l'erreur est seulement journalisée. Aucune obligation de
changer le mot de passe à la première connexion n'existe, et `isVerified` n'a
aucun effet.

## Détails techniques
- `main.py:231-232` : `secrets.choice` sur `[A-Za-z0-9]`, 10 caractères
  (environ 59 bits) : robuste.
- `main.py:245-247` : commit.
- `main.py:262` : `send_email`, dont l'échec est seulement journalisé.
- `main.py:264-269` : `tempPassword` dans la réponse.
- Il n'existe aucun indicateur « mot de passe à changer ».
- **Aujourd'hui, cette route ne fonctionne de toute façon pas** (AUDIT-DB-012).

## Impact métier
- Si SMTP est mal configuré, l'admin doit transmettre lui-même le mot de passe,
  hors du système.
- Un mot de passe provisoire peut rester indéfiniment le mot de passe définitif.

## Preuves
Code cité ci-dessus. Le message `SMTP credentials missing. Email not sent.` a
été observé pendant les tests (`11-evidence/logs/`).

## Composants concernés
`main.py` (`create_user`, `send_email`).

## Localisation
- **Code :** `main.py:224-269`.
- **Base :** `users`.

## Cause racine
Le flux d'invitation a été conçu sans lien d'activation.

## Recommandation
Remplacer le mot de passe provisoire par un **lien d'activation à usage
unique**, sur le même mécanisme que la réinitialisation, une fois celle-ci
corrigée (AUDIT-DB-005).
1. Créer le compte avec un mot de passe inutilisable.
2. Envoyer un lien d'activation à usage unique, valable par exemple 72 h.
3. L'utilisateur choisit son mot de passe, et `isVerified` passe à `true`.
4. La connexion d'un compte non vérifié est refusée.

## Correctif proposé
Ce point se traite avec AUDIT-DB-005, puisqu'il réutilise le même mécanisme de
jeton.

## Risques du correctif
SMTP devient indispensable à la création de compte. Il faut prévoir un renvoi
du lien.

## Validation
- La réponse de `POST /api/users` ne contient plus de mot de passe.
- Un compte non activé ne peut pas se connecter.

## Effort estimé
M.

## Dépendances
AUDIT-DB-005, AUDIT-DB-012.

## Findings liés
AUDIT-DB-004, AUDIT-DB-005, AUDIT-DB-012.
