# AUDIT-DB-020 — Sérialisation par liste d'exclusion : toute nouvelle colonne sensible est exposée par défaut

## Sévérité
LOW

**Justification :**
- **Aujourd'hui, le contrôle fonctionne :** T-A06 n'a trouvé aucun hash ni
  jeton dans les réponses.
- **Le risque est latent mais structurel :** l'ajout d'une colonne sensible à
  un modèle (IBAN, numéro de sécurité sociale, salaire contractuel…) la publie
  immédiatement via `/api/data`, à tout utilisateur connecté (AUDIT-DB-003),
  sauf si quelqu'un pense à l'ajouter à la liste.
- **Ce qui justifie LOW :** il n'y a pas de fuite constatée, et le défaut
  disparaît avec le correctif d'AUDIT-DB-003.

## Catégorie
Sécurité / Exposition des données

## Statut
OPEN · CONFIRMED (mécanisme)

## Résumé
`_row()` renvoie `obj.__dict__` en retirant seulement les clés commençant par
`_` et 4 noms listés dans `_PRIVATE_COLUMNS`. C'est une **liste d'exclusion** :
tout ce qui n'y figure pas est publié.

## Détails techniques
- `main.py:118` : `_PRIVATE_COLUMNS = {'hashedPassword', 'hashed_password', 'resetToken', 'resetTokenExpiry'}`.
- `main.py:120-129` : `{k: v for k, v in obj.__dict__.items() if not k.startswith('_') and k not in _PRIVATE_COLUMNS}`.
- `obj.__dict__` ne contient que les attributs **chargés** : le contenu exact
  dépend aussi de l'état de la session, ce qui le rend peu prévisible.
- À l'inverse, le router `invoicing` utilise des `response_model` Pydantic
  explicites (`ClientOut`, `InvoiceOut`). C'est la bonne pratique, et elle est
  déjà présente dans le projet.

## Impact métier
Une fuite future, involontaire, de données personnelles ou financières, sans
qu'aucune revue ne la voie.

## Preuves
- T-A06 : la liste des champs utilisateur renvoyés, sans aucun secret.
- Code : `main.py:116-129`.

## Composants concernés
`main.py` (`_row`, `get_data`).

## Localisation
- **Code :** `main.py:116-129`, `:511-518`.
- **Base :** —

## Cause racine
C'était un correctif ponctuel, arrivé avec la PR #35 après une fuite réelle de
hash. Il retire ce qui a fuité, au lieu de déclarer ce qui peut sortir.

## Recommandation
Remplacer `_row()` par des schémas de sortie Pydantic par entité : une **liste
d'autorisation**, déjà utilisée par le router `invoicing`.

## Correctif proposé
Inclus dans le correctif d'AUDIT-DB-003, qui supprime `/api/data`. `_row()`
n'a pas d'autre appelant.

## Risques du correctif
Aucun.

## Validation
`grep -n "_row(" main.py` : aucune occurrence. Chaque endpoint de lecture
déclare un `response_model`.

## Effort estimé
S, inclus dans AUDIT-DB-003.

## Dépendances
AUDIT-DB-003.

## Findings liés
AUDIT-DB-003.
