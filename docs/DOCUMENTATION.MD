# DIXpertIA - Enterprise IT Solutions Portal

## Overview

DIXpertIA is a full-stack employee portal and admin dashboard for an IT services company.

- Public corporate homepage (Services, About, Contact with form + FAQ).
- Authentication with role-based views:
  - **Employee**: payslips, leave requests, team directory.
  - **Accountant**: payslips, invoices, users (read-only).
  - **Admin (HR)**: invoices, projects, users, team, approve/reject leave.
- Dynamic notifications that respect user roles.
- Responsive UI: persistent sidebar, mobile drawer, notification bell.

## Tech Stack

### Frontend

- React 18 + TypeScript
- Vite (dev server, build tool)
- Tailwind CSS (custom design tokens)
- Lucide React, Motion (Framer Motion)

### Backend
- FastAPI + Uvicorn
- Pydantic v2 (validation)
- SQLAlchemy 2 (ORM)
- Alembic (migrations)
- PostgreSQL (database)
- ReportLab (PDF generation: payslips, invoices)
- JWT (python-jose) + bcrypt (passlib) for auth

## Project Structure

    app/
      core/       config, database, security, deps
      models/     SQLAlchemy models (user, payroll, leaves, invoicing, service)
      routers/    API endpoints
      schemas/    Pydantic schemas
      services/   PDF generators
    alembic/      Database migrations
    db/           Role setup SQL, verification scripts
    src/          React frontend
    main.py       FastAPI entry point
    seed_users.py Seeds an initial admin user
    tables.py     Creates the schema (dev only)

## Setup & Running

### 1. Install PostgreSQL and create the database

    CREATE DATABASE dixpertia;

Create the application and owner roles (see `db/README.md`):

    python db/setup_roles.py --superuser-url postgresql://postgres:PASS@HOST:5432/dixpertia

### 2. Create the virtual environment and install dependencies

    python -m venv venv
    venv\Scripts\activate          # Windows
    source venv/bin/activate       # macOS / Linux
    pip install -r requirements-dev.txt

### 3. Configure .env

    copy .env.example .env

Open `.env` and set at minimum `DATABASE_URL` and `SECRET_KEY` (>= 32 chars):

    python -c "import secrets; print(secrets.token_urlsafe(32))"

### 4. Create the schema

    python tables.py
    # Once Alembic migrations are the source of truth:
    # alembic upgrade head

### 5. Seed an admin user

    python seed_users.py --admin admin@dixpertia.tn

### 6. Run the apps

Backend (terminal 1):

    uvicorn main:app --reload --port 8000

Frontend (terminal 2):

    npm install
    npm run dev

Frontend: http://localhost:3000 - Backend: http://localhost:8000/docs

### 7. Enable pre-commit hooks

    pip install pre-commit
    pre-commit install

## Environment Variables

See `.env.example`. Required: `DATABASE_URL`, `SECRET_KEY`.
Optional: `SCHEMA_DATABASE_URL`, `ACCESS_TOKEN_EXPIRE_MINUTES`,
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`,
`FRONTEND_URL`.

There are no fallbacks for required values: the process refuses to start
without them.
