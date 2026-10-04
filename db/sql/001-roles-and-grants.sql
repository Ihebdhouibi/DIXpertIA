-- =============================================================================
-- Least-privilege database roles for DI Xpertia
-- =============================================================================
-- Re-runnable. Every statement is guarded or idempotent, so applying it twice
-- changes nothing.
--
-- Why: the application connected as `postgres`, which holds rolsuper,
-- rolcreaterole, rolcreatedb and rolbypassrls. Any application or dependency
-- flaw gave full control of the database server (AUDIT-DB-006). A superuser
-- also bypasses row-level security entirely, so #43 cannot work until this
-- lands.
--
-- Two roles, deliberately separated:
--   dixpertia_owner - owns the schema; used ONLY by tables.py and Alembic
--   dixpertia_app   - used by the running application; cannot alter the schema
--
-- Placeholders :app_password and :owner_password are substituted by
-- db/setup_roles.py. Do not commit real passwords here.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Roles
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_owner') THEN
        CREATE ROLE dixpertia_owner LOGIN PASSWORD :'owner_password';
    ELSE
        ALTER ROLE dixpertia_owner WITH LOGIN PASSWORD :'owner_password';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        CREATE ROLE dixpertia_app LOGIN PASSWORD :'app_password';
    ELSE
        ALTER ROLE dixpertia_app WITH LOGIN PASSWORD :'app_password';
    END IF;
END
$$;

-- Explicit, not inherited from defaults: these are the attributes the audit
-- checks for.
ALTER ROLE dixpertia_owner NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
ALTER ROLE dixpertia_app   NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;

-- A runaway query should not hold connections open indefinitely. Set on the
-- role so it applies to every session regardless of how the app connects.
ALTER ROLE dixpertia_app SET statement_timeout = '30s';
ALTER ROLE dixpertia_app SET idle_in_transaction_session_timeout = '60s';

-- ---------------------------------------------------------------------------
-- 2. Schema
-- ---------------------------------------------------------------------------
-- PUBLIC may create objects in `public` by default on PostgreSQL < 15, and
-- revoking is harmless on later versions.
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

ALTER SCHEMA public OWNER TO dixpertia_owner;
GRANT USAGE ON SCHEMA public TO dixpertia_app;
GRANT CREATE ON SCHEMA public TO dixpertia_owner;

-- Hand existing objects to the owner role so it can run migrations on them.
DO $$
DECLARE
    obj record;
BEGIN
    FOR obj IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER TABLE public.%I OWNER TO dixpertia_owner', obj.tablename);
    END LOOP;
    FOR obj IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' LOOP
        EXECUTE format('ALTER SEQUENCE public.%I OWNER TO dixpertia_owner', obj.sequencename);
    END LOOP;
END
$$;

-- ---------------------------------------------------------------------------
-- 3. Privileges for the application role
-- ---------------------------------------------------------------------------
-- Start from nothing, then grant only what the code actually performs.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM dixpertia_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM dixpertia_app;

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO dixpertia_app;

-- DELETE is granted only where the application deletes rows:
--   app/routers/services.py:44   db.delete(service)
-- Nothing else deletes, so nothing else gets DELETE. In particular `users`,
-- `invoices`, `payslips` and `leave_requests` are append/update only - an
-- accounting record must not be removable by the application role.
-- Guarded: on a fresh database this script runs BEFORE the tables exist
-- (database created -> roles -> migrations -> re-run for table grants). An
-- unguarded GRANT would abort the whole script with UndefinedTable.
DO $$
DECLARE
    tbl text;
BEGIN
    FOREACH tbl IN ARRAY ARRAY['services'] LOOP
        IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = tbl) THEN
            EXECUTE format('GRANT DELETE ON TABLE public.%I TO dixpertia_app', tbl);
        ELSE
            RAISE NOTICE 'Table public.% does not exist yet; re-run this script after migrations to grant DELETE.', tbl;
        END IF;
    END LOOP;
END
$$;

-- Integer primary keys draw from sequences; UPDATE is required by nextval().
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO dixpertia_app;

-- TRUNCATE and REFERENCES are never granted: TRUNCATE bypasses row triggers
-- and audit trails (#63), and is not something the application should do.

-- ---------------------------------------------------------------------------
-- 4. Future objects
-- ---------------------------------------------------------------------------
-- Tables created later by the owner (Alembic, #56) inherit the same grants,
-- so a new migration cannot silently leave the app role without access - or
-- with too much.
ALTER DEFAULT PRIVILEGES FOR ROLE dixpertia_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE ON TABLES TO dixpertia_app;
ALTER DEFAULT PRIVILEGES FOR ROLE dixpertia_owner IN SCHEMA public
    GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO dixpertia_app;
