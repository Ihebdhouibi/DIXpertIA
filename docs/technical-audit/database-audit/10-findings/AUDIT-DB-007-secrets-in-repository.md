# AUDIT-DB-007 — Secrets dans le dépôt : clé JWT de repli, mot de passe de la base, hash de comptes réels

## Sévérité
HIGH

**Justification :**
- **Impact :** avec la clé de repli, **n'importe qui peut forger un jeton admin**
  sur tout déploiement qui ne définit pas `SECRET_KEY`. C'est la compromission
  totale de l'application.
- **Exploitabilité :** conditionnelle au déploiement. Mais la condition est
  **probable** :
  - `.env.example`, le modèle fourni, **ne mentionne pas `SECRET_KEY`** et ne
    contient que des variables Google AI Studio ;
  - la documentation est obsolète (AUDIT-DB-022).

  Un déploiement fait en suivant le dépôt aboutit donc à la clé de repli.
- **Portée :** toute personne ayant lu le dépôt, c'est-à-dire tout collaborateur
  présent ou passé, ou toute personne ayant obtenu une copie.
- **Ce qui justifie HIGH plutôt que MEDIUM :** la probabilité est élevée, et
  l'impact maximal.

## Catégorie
Sécurité / Gestion des secrets

## Statut
OPEN · CONFIRMED

## Résumé
Trois catégories de secrets sont versionnées :
1. Une **valeur de repli de `SECRET_KEY`**, identique dans `main.py:58` et
   `app/core/config.py:9`.
2. Une **valeur de repli de `DATABASE_URL`** contenant le mot de passe du
   superutilisateur `postgres` (`app/core/config.py:8`).
3. Dans **`db.json`**, versionné depuis `4cec208` : **3 hash bcrypt** de comptes
   réels (deux admins, une comptable) et **1 jeton de réinitialisation**.

Toutes ces valeurs sont : `SECRET DETECTED — VALUE REDACTED`.

## Détails techniques
- `git grep` sur `getenv("SECRET_KEY"` et `getenv("DATABASE_URL"` donne 3
  occurrences avec valeur par défaut.
- `.env` n'a **jamais** été committé (`git log --all -- .env` est vide) : c'est
  un point positif.
- Le hook `detect-private-key` et les règles ruff S105 et S106 ne détectent pas
  ces valeurs passées à `os.getenv`.
- T-A08 : en local, un jeton forgé avec la clé de repli est **refusé**, parce
  que `.env` définit `SECRET_KEY`. Cela prouve que le risque dépend uniquement
  de la configuration du déploiement.
- Les valeurs de `db.json` restent dans l'historique git, même si le fichier est
  nettoyé.

## Impact métier
- **Prise de contrôle complète** de tout déploiement sans `SECRET_KEY`.
- **Accès au serveur de base** de tout environnement qui aurait gardé ce mot de
  passe.
- **Hash de comptes admin** exposés à une attaque hors ligne. Le bcrypt la rend
  coûteuse, mais elle est faisable contre un mot de passe faible ou réutilisé.

## Preuves
- `git grep -n -E 'getenv\("(SECRET_KEY|DATABASE_URL)"'` : `main.py:58`,
  `app/core/config.py:8-9`, avec les valeurs masquées
  (`06-security/security-static-analysis.md` § 3).
- `db.json` : structure inspectée sans en lire les valeurs
  (`01-requests/README.md`).
- T-A08 : `11-evidence/api-tests/api-tests.results.md`.

## Composants concernés
`main.py`, `app/core/config.py`, `db.json`, `.env.example`, historique git.

## Localisation
- **Code :** `main.py:58`, `app/core/config.py:7-9`, `db.json`.
- **Base :** rôle `postgres`.

## Cause racine
Les valeurs de repli ont été ajoutées pour que l'application « démarre toute
seule » en local. `db.json` vient de l'ancien stockage JSON, et a été committé
comme donnée d'amorçage.

## Recommandation
1. **Supprimer toute valeur de repli secrète.** L'application doit **refuser de
   démarrer** si `SECRET_KEY` ou `DATABASE_URL` manque.
2. **Changer immédiatement** :
   - le mot de passe du rôle `postgres` de tout environnement qui utiliserait
     la valeur du dépôt ;
   - les mots de passe des 3 comptes de `db.json`.
3. **Retirer `db.json` du dépôt** et le remplacer par un script d'amorçage sans
   hash réel. Décider s'il faut réécrire l'historique git : ce sont des
   opérations destructives, à faire avec l'accord d'Iheb, l'admin du dépôt.
4. Mettre à jour `.env.example` avec les vraies variables, chacune avec une
   valeur factice explicite.
5. Ajouter un hook de détection de secrets, par exemple `gitleaks` ou
   `detect-secrets`.

## Correctif proposé
```python
# app/core/config.py
DATABASE_URL: str = os.environ["DATABASE_URL"]
SECRET_KEY: str = os.environ["SECRET_KEY"]
if len(SECRET_KEY) < 32:
    raise RuntimeError("SECRET_KEY must be at least 32 characters")
```

`main.py` importe `settings.SECRET_KEY`, et ne recalcule plus sa propre valeur.

## Risques du correctif
- Un environnement qui fonctionnait grâce à la valeur de repli **ne démarrera
  plus**. C'est le comportement voulu, mais il faut prévenir l'équipe.
- Réécrire l'historique git casse les clones existants : c'est une décision
  d'équipe.

## Validation
- `git grep -E 'getenv\("(SECRET_KEY|DATABASE_URL)",'` ne renvoie plus rien.
- Démarrer sans `SECRET_KEY` : erreur explicite au démarrage.
- T-A08 rejoué sur chaque environnement : **401**.

## Effort estimé
S pour le code, M pour la rotation des secrets et la décision sur l'historique.

## Dépendances
AUDIT-DB-006 (rôle applicatif dédié, dont le mot de passe sera alors un secret
propre).

## Findings liés
AUDIT-DB-005 (même clé de signature), AUDIT-DB-006, AUDIT-DB-008,
AUDIT-DB-022 (`.env.example` obsolète).
