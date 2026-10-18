# AUDIT-DB-008 — Données sensibles écrites dans les logs

## Sévérité
MEDIUM

**Justification :**
- **Impact :** les logs reçoivent le hash bcrypt du mot de passe provisoire et
  l'e-mail. `tables.py` y écrit le mot de passe de la base. Les logs sont
  souvent moins protégés que la base : copiés, centralisés, partagés pour du
  support.
- **Exploitabilité :** il faut accéder aux logs.
- **Probabilité :** **élevée** pour la fuite du hash. Elle se produit à
  **chaque** tentative de création de compte, puisque celle-ci échoue
  systématiquement (AUDIT-DB-012).
- **Ce qui justifie MEDIUM :** le risque est réel, mais conditionné à l'accès
  aux logs.

## Catégorie
Sécurité / Journalisation

## Statut
OPEN · CONFIRMED

## Résumé
Trois sources de fuite, dont la troisième est latente :
1. **Les erreurs d'intégrité SQLAlchemy écrivent tous les paramètres de la
   requête** dans la trace de l'exception, e-mail et `hashedPassword` compris.
2. **`tables.py` affiche `DATABASE_URL` en entier**, mot de passe compris.
3. **`main.py` journalise l'e-mail et la cause d'échec de chaque connexion**
   (`log.info`). Ces lignes ne sont **pas écrites aujourd'hui**, parce que le
   logger est au niveau WARNING sans handler. Elles le seront dès que la
   journalisation sera configurée.

## Détails techniques
- **Fuite 1, CONFIRMED.** Pendant T-A07, la sortie du backend (ligne 434)
  contient
  `[parameters: {'id': 'USR-008', 'email': '<EMAIL>@…', …, 'hashedPassword': '<BCRYPT REDACTED>', …}]`.
  Cause : `create_engine(settings.DATABASE_URL, pool_pre_ping=True)`
  (`app/core/database.py:6`), sans `hide_parameters=True`.
- **Fuite 2, CONFIRMED.** `tables.py:28` contient
  `print(f"Target: {settings.DATABASE_URL}")`. La sortie du 2026-10-01 a dû
  être masquée à la main.
- **Fuite 3, latente.** `main.py:197`, `:200`, `:203` et `:205`. Niveau
  effectif vérifié : `logging.getLogger('dixpertia')` est en WARNING, avec
  `handlers = []`.
- `main.py:90` contient `log.error("Email error: %s", e)` : le message d'une
  exception SMTP peut contenir l'hôte ou l'identifiant.
- **Point positif :** les jetons et les mots de passe en clair ne sont jamais
  journalisés. La PR #49 a retiré le mot de passe provisoire de la console.

## Impact métier
Quiconque accède aux logs du serveur (hébergeur, collègue, outil de
centralisation) obtient des hash de mots de passe, des e-mails et le mot de
passe de la base.

## Preuves
- `06-security/security-runtime-tests.md` § 2 (OBS-035).
- `11-evidence/logs/backend-api-tests-2026-10-02.redacted.log`, ligne 434
  d'origine (les valeurs sont masquées dans la copie).
- `discovery-observations.md` OBS-017, OBS-018.

## Composants concernés
`app/core/database.py`, `tables.py`, `main.py` (journalisation de la connexion).

## Localisation
- **Code :** `app/core/database.py:6`, `tables.py:28`, `main.py:90`,
  `:197-205`.
- **Base :** —

## Cause racine
Les erreurs ne sont pas traitées : un `IntegrityError` remonte jusqu'à Uvicorn,
qui imprime la trace complète. La journalisation n'est pas configurée, ni sa
politique définie.

## Recommandation
1. `create_engine(..., hide_parameters=True)`.
2. Intercepter `IntegrityError` dans les endpoints d'écriture, et renvoyer 409
   avec un message neutre (voir aussi AUDIT-DB-012).
3. `tables.py` : n'afficher que l'hôte, le port et la base, comme le fait déjà
   `run_readonly.py`.
4. Définir une politique de journalisation :
   - pas d'e-mail en clair à la connexion (identifiant interne, ou e-mail haché) ;
   - pas de distinction « compte inexistant / mauvais mot de passe » dans les
     messages.

## Correctif proposé
```python
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, hide_parameters=True)
```

```python
url = make_url(settings.DATABASE_URL)
print(f"Target: {url.host}:{url.port}/{url.database}")
```

## Risques du correctif
Aucun fonctionnel. Le débogage est un peu moins riche : les paramètres restent
obtenables en activant temporairement le niveau DEBUG en local.

## Validation
- Rejouer T-A07 : la sortie ne contient plus `[parameters:`.
- `python tables.py` : aucun mot de passe affiché.
- Recherche d'e-mails dans les logs après une série de tests : 0.

## Effort estimé
S.

## Dépendances
Aucune.

## Findings liés
AUDIT-DB-007, AUDIT-DB-009 (énumération), AUDIT-DB-012 (cause des erreurs
d'intégrité répétées).
