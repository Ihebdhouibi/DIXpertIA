# Structure du projet

> Phase 1 — Discovery · 2026-10-01 · `develop` @ `34453a4` · 50 commits

## Arborescence utile à l'audit

```text
DIXpertIA/
├── main.py                    # POINT D'ENTRÉE RÉEL de l'API (518 lignes) : routes auth, users,
│                              #   congés, équipe, factures (morte), devices, /api/data
├── app/
│   ├── core/
│   │   ├── config.py          # Settings : DATABASE_URL, SECRET_KEY, SMTP_*, FRONTEND_URL
│   │   ├── database.py        # engine, SessionLocal, Base (declarative_base), get_db
│   │   ├── security.py        # 2e implémentation JWT/hash (passlib)
│   │   └── deps.py            # get_current_user + require_roles(*roles)
│   ├── models/                # MODÈLES ORM (5 fichiers, 9 classes)
│   │   ├── user.py            # User
│   │   ├── payroll.py         # Payslip
│   │   ├── leaves.py          # LeaveRequest + Enum LeaveType, LeaveStatus
│   │   ├── service.py         # Service, TeamMember
│   │   └── invoicing.py       # Client, Invoice, InvoiceItem, Device + Enum InvoiceStatus
│   ├── routers/
│   │   ├── invoicing.py       # SEUL ROUTER MONTÉ (main.py:40) : clients, factures, PDF
│   │   ├── auth.py            # NON MONTÉ — code mort
│   │   ├── payroll.py         # NON MONTÉ — volontairement (main.py:35-39)
│   │   ├── leaves.py          # NON MONTÉ — code mort
│   │   └── services.py        # NON MONTÉ — code mort
│   ├── schemas/               # Schémas Pydantic (utilisés par le router invoicing uniquement)
│   └── services/
│       └── invoice_generator.py   # génération PDF ReportLab
├── alembic/
│   ├── env.py                 # branché sur Base.metadata et settings.DATABASE_URL
│   └── versions/              # VIDE — aucune migration
├── alembic.ini                # URL fictive, écrasée par env.py
├── tables.py                  # crée le schéma via Base.metadata.create_all()
├── seed_users.py              # importe les comptes de db.json + crée/réinitialise un admin
├── migrate_data.py            # migration db.json → PostgreSQL (incompatible avec les modèles)
├── insert_invoices.py         # insère 5 clients + 5 factures de démonstration (compatible)
├── db.json                    # ancien stockage JSON — VERSIONNÉ, contient 3 hash bcrypt
├── src/                       # Frontend React
│   ├── App.tsx                # état global, persistance localStorage, appels API
│   ├── types.ts               # types frontend (camelCase, anglais)
│   ├── data.ts                # DONNÉES FICTIVES initiales (bulletins, congés, équipe, factures, projets)
│   └── components/            # 15 vues
├── server.ts                  # passerelle Express alternative (héritage AI Studio)
├── vite.config.ts             # proxy /api → 127.0.0.1:8000
├── Dockerfile                 # point d'entrée incorrect (app.main:app)
├── docs/DOCUMENTATION.MD      # obsolète (décrit le backend JSON)
└── design/                    # kit de marque, non versionné
```

## Localisation des éléments demandés par la mission

| # | Élément | Localisation | Statut |
|---|---|---|---|
| 1 | Framework | FastAPI (`main.py`) + React/Vite (`src/`) | CONFIRMED |
| 2 | ORM | SQLAlchemy 2.0, `declarative_base` (`app/core/database.py:8`) | CONFIRMED |
| 3 | SGBD | PostgreSQL 17 (`app/core/config.py:8`, service local) | CONFIRMED |
| 4 | Modèles | `app/models/*.py` | CONFIRMED |
| 5 | Migrations | `alembic/versions/` — **vide** ; schéma créé par `tables.py` | CONFIRMED |
| 6 | Relations | `ForeignKey()` et `relationship()` dans `app/models/` ; seules `invoicing.py` déclare des `relationship()` | CONFIRMED |
| 7 | Rôles et permissions | chaîne libre `User.role` ; contrôles dans `main.py` (`current_user.role` / `current_user['role']`) et `app/core/deps.py:require_roles` | CONFIRMED |
| 8 | Authentification | `POST /api/login` (`main.py:195`), JWT HS256 | CONFIRMED |
| 9 | Autorisation | contrôles de rôle par endpoint, **absents sur plusieurs endpoints** | CONFIRMED (code) — voir `authentication-and-authorization.md` |
| 10 | Usage des données par les fonctionnalités | voir `application-data-flow.md` | CONFIRMED |
| 11–12 | Entités et relations | voir `database-overview.md` | partiellement : catalogue DB `NOT VERIFIED` (serveur indisponible) |
| 13 | Données sensibles | voir `database-overview.md` § Tables sensibles | CONFIRMED (code) |
| 14 | Parties critiques | voir `discovery-observations.md` | CONFIRMED (code) |

## Conventions de nommage observées

Le projet mélange **deux conventions incompatibles** dans le même schéma :

| Convention | Tables | Exemples de colonnes | Clés primaires |
|---|---|---|---|
| camelCase anglais | `users`, `team_members`, `devices` | `firstName`, `hashedPassword`, `serialNumber`, `createdAt` | chaîne (`USR-001`, `TM-001`, `DEV-001`) |
| snake_case français | `payslips`, `leave_requests`, `services`, `clients`, `invoices`, `invoice_items` | `montant_brut`, `date_emission`, `cree_par_id`, `taux_tva` | entier auto-incrémenté |

L'API (`main.py`) et le frontend (`src/types.ts`) parlent la première
convention. Le schéma des entités métier suit la seconde. C'est la cause de la
scission documentée dans la PR #35 et le ticket #37.
