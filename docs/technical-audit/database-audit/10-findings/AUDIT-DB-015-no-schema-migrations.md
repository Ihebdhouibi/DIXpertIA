# AUDIT-DB-015 — Aucune migration : le schéma n'est ni versionné ni modifiable sans risque

## Sévérité
MEDIUM

**Justification :**
- **Impact :** la plupart des corrections de cet audit (contraintes, index,
  rôles, colonnes) exigent de **modifier un schéma existant**. Sans migrations,
  chaque correction se fait à la main, environnement par environnement, sans
  trace ni retour arrière.
- **Ce qui justifie MEDIUM :** c'est une dette qui rend l'évolution coûteuse et
  risquée, plutôt qu'un défaut exploitable.
- **C'est le prérequis de la remédiation :** à traiter en premier.

## Catégorie
Architecture / Gestion du schéma

## Statut
OPEN · CONFIRMED

## Résumé
- Alembic est installé et configuré (`alembic/env.py`), mais
  `alembic/versions/` est vide.
- La base n'a pas de table `alembic_version`.
- Le schéma est créé par `Base.metadata.create_all()`, qui ne modifie **jamais**
  une table existante.

## Détails techniques
- Q-DISC-009 : `alembic_version` est absente.
- `alembic.ini:3` contient une URL fictive, écrasée par `alembic/env.py:13`.
  C'est correct.
- `alembic/env.py:10` importe les modèles : l'autogénération est donc
  opérationnelle.
- `tables.py` et `migrate_data.py` appellent `create_all()`.
- `app/models/__init__.py` est vide : l'enregistrement des modèles repose sur
  des imports manuels, dont l'oubli a déjà produit un schéma vide sans erreur
  (corrigé par la PR #35).

## Impact métier
- **Impossible de savoir quel schéma tourne** sur un autre environnement, comme
  une éventuelle production : `NOT VERIFIED`, aucun accès.
- **Toute colonne ajoutée à un modèle n'apparaît pas** dans une base déjà
  créée. Le code et la base divergent alors silencieusement.
- **Les corrections de cet audit ne peuvent pas être livrées proprement.**

## Preuves
`11-evidence/schema/01-discovery-overview.results.md` (Q-DISC-009) ;
`alembic/versions/` vide.

## Composants concernés
`alembic/`, `tables.py`, `migrate_data.py`, `app/models/__init__.py`.

## Localisation
- **Code :** `alembic/versions/`, `tables.py:33`, `migrate_data.py:12`.
- **Base :** table `alembic_version`, absente.

## Cause racine
Le schéma a été amorcé par `create_all()` au moment de la migration depuis le
JSON, sans revision initiale.

## Recommandation
1. Générer une **révision initiale** représentant le schéma actuel
   (`alembic revision --autogenerate -m "baseline"`), puis l'**estampiller** sur
   les bases existantes (`alembic stamp head`). Ne jamais la rejouer.
2. Toutes les corrections suivantes de l'audit passent par des révisions
   versionnées et relues en PR.
3. `tables.py` ne sert plus qu'aux environnements jetables, ou disparaît au
   profit de `alembic upgrade head`.
4. Centraliser l'import des modèles dans `app/models/__init__.py`.

## Correctif proposé
```powershell
.venv\Scripts\alembic.exe revision --autogenerate -m "baseline schema"
.venv\Scripts\alembic.exe stamp head          # sur chaque base existante
```

Relire la révision générée : l'autogénération gère mal les ENUM, et ne crée pas
les types existants.

## Risques du correctif
- Une base existante dont le schéma diffère de la révision de référence serait
  mal estampillée. Il faut comparer avant (`alembic check`, ou Q-SCH-001 sur
  chaque base).
- Les opérations d'Alembic doivent être exécutées avec un rôle propriétaire,
  et non avec le rôle applicatif (AUDIT-DB-006).

## Validation
- `alembic current` affiche la révision de référence sur chaque base.
- `alembic check` ne signale aucune différence entre les modèles et la base.
- Une base vide créée par `alembic upgrade head` est identique à la base
  actuelle (Q-SCH-001 à 009 comparées).

## Effort estimé
S.

## Dépendances
Aucune. **C'est la première étape de la remédiation.**

## Findings liés
AUDIT-DB-006, AUDIT-DB-010, AUDIT-DB-012, AUDIT-DB-014, AUDIT-DB-016, AUDIT-DB-018.
