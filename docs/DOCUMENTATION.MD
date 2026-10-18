# DIXpertIA - Enterprise IT Solutions Portal

## Overview

DIXpertIA is a full-stack employee portal and admin dashboard for an IT services company.

- Public corporate homepage (Services, About, Contact with form + FAQ).
- Authentication with role-based access:
  - **Employee**: payslips, leave requests, team directory.
  - **Accountant**: payslips, invoices, users (read-only).
  - **Admin (HR)**: invoices, projects, users, team, approve/reject leave.
- Dynamic role-aware notifications.
- Responsive UI: sidebar, mobile drawer, notification bell.

## Tech Stack

### Frontend
- React 18 + TypeScript
- Vite
- Tailwind CSS (custom design tokens)
- Lucide React, Motion

### Backend
- FastAPI + Uvicorn
- Pydantic v2
- SQLAlchemy 2
- Alembic (migrations)
- PostgreSQL 17
- ReportLab (PDF generation)
- JWT (python-jose) + bcrypt (passlib)

## Project Structure

    app/
      core/       config, database, security, deps, identity
      models/     SQLAlchemy models
      routers/    API endpoints
      schemas/    Pydantic schemas
      services/   PDF generators
    alembic/      Database migrations
    db/           Role setup SQL, verification scripts, README
    src/          React frontend
    main.py       FastAPI entry point
    seed_users.py Seeds an initial user
    db/README.md  Verified database procedure

## Setup

The verified database procedure lives in `db/README.md`. Summary:

### 1. Install PostgreSQL 17 and create the database

    CREATE DATABASE dixpertia;

### 2. Create the least-privilege roles

    python db/setup_roles.py --superuser-url postgresql://postgres:PASS@localhost:5432/dixpertia

Record the two URLs it prints; they go into `.env`.

### 3. Create the virtual environment

    python -m venv .venv
    .venv\Scripts\activate          # Windows
    source .venv/bin/activate       # macOS / Linux
    pip install -r requirements-dev.txt

### 4. Configure .env

    copy .env.example .env

Set at minimum `DATABASE_URL`, `SECRET_KEY` (>= 32 chars), and
`SCHEMA_DATABASE_URL`. Generate a key with:

    python -c "import secrets; print(secrets.token_urlsafe(32))"

### 5. Build the schema

    alembic upgrade head

### 6. Re-run role grants (tables now exist, DELETE grants apply)

    python db/setup_roles.py --superuser-url postgresql://postgres:PASS@localhost:5432/dixpertia --app-password <from step 2> --owner-password <from step 2>

### 7. Seed the first administrator

    python seed_users.py --email admin@dixpertia.tn

### 8. Run the apps

Backend (terminal 1):

    uvicorn main:app --reload --port 8000

Frontend (terminal 2):

    npm install
    npm run dev

Frontend: http://localhost:3000 - Backend docs: http://localhost:8000/docs

### 9. Enable pre-commit hooks

    pip install pre-commit
    pre-commit install

## Database rules

Never edit the database by hand, and never use `Base.metadata.create_all()`.
Schema changes go through Alembic:

    alembic revision --autogenerate -m "short description"
    alembic upgrade head      # apply
    alembic downgrade -1      # roll back one revision
    alembic check             # fail if models and database have drifted

## Environment Variables

See `.env.example`. Required: `DATABASE_URL`, `SECRET_KEY`.
There are no fallbacks: the process refuses to start without them.