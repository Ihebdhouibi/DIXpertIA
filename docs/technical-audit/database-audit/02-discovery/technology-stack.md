# Stack technique

> Phase 1 — Discovery · rédigé le 2026-10-01 · état du code : `develop` @ `34453a4`
>
> Chaque affirmation renvoie à un fichier vérifiable. Ce qui n'a pas pu être
> vérifié est marqué `NOT VERIFIED`.

## Vue d'ensemble

| Couche | Technologie | Version | Source |
|---|---|---|---|
| SGBD | PostgreSQL | 17 (17.11 observé le 2026-10-01) | service Windows `postgresql-x64-17` |
| Pilote base | psycopg2-binary | 2.9.9 | `requirements.txt` |
| ORM | SQLAlchemy (API classique `declarative_base`) | 2.0.31 | `requirements.txt`, `app/core/database.py` |
| Migrations | Alembic | 1.13.2 | `requirements.txt`, `alembic/` |
| Framework API | FastAPI | 0.111.0 | `requirements.txt` |
| Serveur ASGI | Uvicorn | 0.30.1 | `requirements.txt` |
| Validation | Pydantic | 2.7.4 | `requirements.txt` |
| Authentification | python-jose (JWT HS256), bcrypt, passlib | 3.3.0 / 4.2.0 / 1.7.4 | `requirements.txt` |
| PDF | ReportLab | 4.2.2 | `app/services/invoice_generator.py` |
| E-mail | `smtplib` (stdlib) ; `mailtrap` 2.0.0 installé | — | `main.py:64-91` |
| Langage backend | Python | 3.11 (CI, venv local) | `.github/workflows/lint.yml`, `pyproject.toml` |
| Frontend | React | 19 | `package.json` |
| Build frontend | Vite | 6 | `package.json`, `vite.config.ts` |
| CSS | Tailwind CSS | 4 | `src/index.css` |
| Langage frontend | TypeScript | ~5.8 | `package.json`, `tsconfig.json` |
| Passerelle Node (alternative) | Express + http-proxy-middleware | 4.x | `server.ts` |

## Points de vigilance relevés pendant la Discovery

Ce sont des observations factuelles. Leur gravité éventuelle sera établie dans
les phases suivantes.

1. **Deux implémentations JWT coexistent.**
   - `main.py:58-114` définit `SECRET_KEY`, `create_access_token`,
     `decode_token` et `get_current_user` avec `bcrypt`.
   - `app/core/security.py` et `app/core/deps.py` définissent les mêmes
     fonctions avec `passlib` et `app.core.config.settings`.

   Les deux lisent la même variable `SECRET_KEY` avec la même valeur de repli
   codée en dur (`main.py:58`, `app/core/config.py:9`). Une valeur de repli
   identique est donc utilisée si la variable est absente : voir
   `discovery-observations.md`, OBS-014.

2. **Deux points d'entrée concurrents.**
   - `npm run dev` lance Vite seul (`package.json`). Le proxy `/api` vers
     `127.0.0.1:8000` est défini dans `vite.config.ts:10-15`, et le backend se
     lance séparément.
   - `server.ts` lance Express et démarre lui-même `python3 -m uvicorn main:app`.
     Il hérite de Google AI Studio (`metadata.json`). Aucun script npm ne
     l'appelle. Sous Windows, `python3` n'est en général pas disponible :
     `NOT VERIFIED`.

3. **Le `Dockerfile` ne correspond pas au code.**
   - Il lance `uvicorn app.main:app` alors que `app/main.py` n'existe pas :
     l'application est dans `main.py` à la racine.
   - Il utilise `python:3.12-slim` alors que la CI et le venv sont en 3.11.
   - Il installe des bibliothèques Pango/Cairo (WeasyPrint) alors que le PDF
     est produit par ReportLab.

4. **Des dépendances sont déclarées mais inutilisées.**
   - `@google/genai` n'est référencé ni dans `src/` ni dans `server.ts`.
   - `mailtrap` est installé, mais l'envoi d'e-mails passe par `smtplib`.

5. **Le schéma n'est pas versionné.**
   - `alembic/versions/` est vide.
   - `alembic.ini:3` contient l'URL fictive `driver://user:pass@localhost/dbname`,
     écrasée à l'exécution par `alembic/env.py:13`.
   - Le schéma réel est créé par `Base.metadata.create_all()` (`tables.py:33`,
     `migrate_data.py:12`).

## Outillage qualité

- **ruff 0.6.9** (`pyproject.toml`) : règles E, F, W, T20 (pas de `print`),
  S105 et S106 (mots de passe codés en dur).
- **Hooks pre-commit** (`.pre-commit-config.yaml`) : contrôle des emoji dans
  les fichiers Python, `detect-private-key`, `check-added-large-files`.
- **CI GitHub Actions** (`.github/workflows/lint.yml`) : ruff, contrôle des
  emoji, `tsc --noEmit`. Il n'y a **aucun test automatisé** : aucun dossier
  `tests/`, ni pytest, ni vitest.
- **La protection de branche est impossible** sur le plan gratuit d'un dépôt
  privé (commentaire en tête de `lint.yml`).
