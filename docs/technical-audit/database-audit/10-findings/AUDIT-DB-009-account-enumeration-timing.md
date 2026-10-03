# AUDIT-DB-009 — Énumération des comptes par le temps de réponse de la connexion

## Sévérité
LOW

**Justification :**
- **Exploitabilité :** facile et anonyme. Le temps de réponse suffit, mesuré de
  façon reproductible.
- **Impact limité :** l'attaquant apprend seulement **si un e-mail a un compte**.
  Cela facilite l'hameçonnage ciblé et l'essai de mots de passe, sans donner
  d'accès par soi-même.

## Catégorie
Sécurité / Authentification

## Statut
OPEN · CONFIRMED

## Résumé
`POST /api/login` répond **environ 12 fois plus vite** quand l'e-mail n'existe
pas : il ne calcule alors aucun bcrypt.

## Détails techniques
- `main.py:198-201` : si l'utilisateur est introuvable, l'endpoint renvoie 401
  immédiatement. Sinon, il appelle `bcrypt.checkpw` (coût 12).
- Mesure T-A09, sur 8 essais par cas : médiane de **24 ms** pour un compte
  inexistant, et de **292 ms** pour un compte existant avec un mauvais mot de
  passe.
- Il n'existe ni limitation de débit ni verrouillage : un attaquant peut tester
  des listes entières d'e-mails.
- **Point positif :** le message d'erreur est identique dans les deux cas.

## Impact métier
Un tiers peut établir la liste des adresses du personnel qui ont un compte.

## Preuves
T-A09 dans `11-evidence/api-tests/api-tests.results.md`.

## Composants concernés
`main.py` (`login`).

## Localisation
- **Code :** `main.py:195-206`.
- **Base :** —

## Cause racine
Le chemin « compte inexistant » court-circuite la vérification du mot de passe.

## Recommandation
Exécuter un `bcrypt.checkpw` sur un hash factice quand le compte n'existe pas,
et ajouter une limitation de débit sur `/api/login`.

## Correctif proposé
```python
_DUMMY_HASH = bcrypt.hashpw(b"dummy", bcrypt.gensalt()).decode()
...
hashed = user.hashedPassword if user else _DUMMY_HASH
ok = verify_password(req.password, hashed)
if not user or not ok:
    raise HTTPException(401, "Invalid credentials")
```

## Risques du correctif
Aucun : la connexion d'un compte inexistant coûte simplement autant qu'une
connexion normale.

## Validation
Rejouer T-A09 : des médianes du même ordre de grandeur.

## Effort estimé
S.

## Dépendances
Aucune.

## Findings liés
AUDIT-DB-008 (les logs distinguent aussi les deux cas).
