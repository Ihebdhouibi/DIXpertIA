# AUDIT-DB-022 — Exploitation et qualité : aucun test, `Dockerfile` cassé, documentation et modèle d'environnement obsolètes

## Sévérité
LOW

**Justification :**
- Ces manques **ne causent pas de défaut par eux-mêmes**. En revanche, ils
  expliquent pourquoi plusieurs défauts graves de cet audit sont passés
  inaperçus : routes sans authentification, routes qui plantent à chaque appel,
  création de compte cassée.
- Le cas le plus lourd est l'absence de tests. Un seul test par route aurait
  détecté AUDIT-DB-002, 010, 012 et 013.
- **Ce qui justifie LOW :** c'est un facteur de risque, pas un risque propre.

## Catégorie
Maintenabilité / Exploitation

## Statut
OPEN · CONFIRMED

## Résumé

| Constat | Preuve |
|---|---|
| **Aucun test automatisé** : ni `tests/`, ni pytest, ni vitest | `git ls-files` ; `requirements*.txt` ; `package.json` |
| **Le `Dockerfile` ne peut pas démarrer l'application** : il lance `uvicorn app.main:app`, alors que le module est `main:app` à la racine. Il utilise Python 3.12 alors que la CI est en 3.11, et installe Pango/Cairo pour un PDF fait avec ReportLab. | `Dockerfile:1`, `:14` |
| **`.env.example` ne contient aucune des variables réelles** (`DATABASE_URL`, `SECRET_KEY`, `SMTP_*`, `FRONTEND_URL`), seulement `GEMINI_API_KEY` et `APP_URL`, hérités d'AI Studio | `.env.example` |
| **`docs/DOCUMENTATION.MD` décrit l'ancien backend JSON** | `docs/DOCUMENTATION.MD:42` |
| **Aucune procédure documentée** de mise en place de la base, de sauvegarde ou de restauration | — |
| `server.ts` lance `python3`, généralement absent sous Windows, et n'est appelé par aucun script | `server.ts:12` |
| Dépendances inutilisées : `@google/genai`, `mailtrap` | `package.json`, `requirements.txt` |

## Impact métier
- Toute correction future risque de casser une autre route sans que personne ne
  s'en aperçoive.
- Un déploiement fait en suivant le dépôt échoue (`Dockerfile`), ou démarre
  **sans `SECRET_KEY`**, puisque `.env.example` l'omet. C'est ce qui rend
  AUDIT-DB-007 probable.

## Preuves
`02-discovery/technology-stack.md` ; `discovery-observations.md`, OBS-031 et 032.
Le `Dockerfile` n'a pas été exécuté (Docker absent du poste) : son échec est
déduit du code (`NOT VERIFIED` à l'exécution).

## Composants concernés
`Dockerfile`, `.env.example`, `docs/DOCUMENTATION.MD`, `server.ts`,
`requirements*.txt`, `package.json`.

## Localisation
- **Code :** voir le tableau.
- **Base :** —

## Cause racine
Héritage du prototype Google AI Studio, jamais mis à jour.

## Recommandation
1. **Tests d'API** (pytest + `TestClient`, sur une base jetable) :
   - un test d'**autorisation par route et par rôle** (anonyme, employé,
     comptable, admin) ;
   - un test de **non-régression** par finding corrigée.

   Les scénarios de `run_api_tests.py` en sont une base directement
   réutilisable.
2. Corriger le `Dockerfile` (`main:app`, Python 3.11, sans dépendances WeasyPrint).
3. Réécrire `.env.example` avec les vraies variables.
4. Mettre à jour la documentation de mise en place, en reprenant la procédure
   suivie le 2026-10-01.
5. Ajouter les tests au workflow `lint.yml`.

## Correctif proposé
Voir la recommandation. Ce sont des chantiers indépendants les uns des autres.

## Risques du correctif
Aucun.

## Validation
- La CI exécute les tests.
- `docker build` puis `docker run` démarrent l'API.
- Une nouvelle installation réussie en suivant uniquement la documentation.

## Effort estimé
M pour les tests de base ; S pour chacun des autres points.

## Dépendances
Aucune.

## Findings liés
AUDIT-DB-002, AUDIT-DB-007, AUDIT-DB-010, AUDIT-DB-012, AUDIT-DB-013.
