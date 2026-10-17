"""languages: users.locale, clients.locale, notifications.params

Revision ID: c9e2a7b4d610
Revises: b8d4f1a6c305
Create Date: 2026-10-18 02:00:00.000000

#135. French and English (decided on the issue).

- users.locale: the language an account reads, French by default. E-mails and
  notification texts follow it. The application role reads it, an admin edits
  it with the other columns; an account changes its own only through
  auth_set_locale(), which touches that one column of the caller's row - an
  UPDATE policy on users would have let an employee edit their own role too.
- clients.locale: the language a client's invoices are printed in, French by
  default, so the same invoice always prints the same way, whoever downloads it.
- notifications.params: the facts a notification is about (reference,
  counterparty, comment), so its text is rendered in the reader's language
  when read instead of being frozen in one language when written. `message`
  stays, for the rows written before and for SQL readers.

auth_account_by_email() also returns the locale, for the sign-in response.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c9e2a7b4d610'
down_revision = 'b8d4f1a6c305'
branch_labels = None
depends_on = None

LOCALES = "('fr', 'en')"

BY_EMAIL_WITH_LOCALE = """
CREATE FUNCTION auth_account_by_email(p_email text)
RETURNS TABLE (id text, email text, "firstName" text, "lastName" text, role text,
               department text, "avatarUrl" text, "isActive" boolean, "isVerified" boolean,
               "createdAt" timestamp, token_version integer, locale text, "hashedPassword" text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT u.id::text, u.email::text, u."firstName"::text, u."lastName"::text, u.role::text,
           u.department::text, u."avatarUrl"::text, u."isActive", u."isVerified", u."createdAt",
           u.token_version, u.locale::text, u."hashedPassword"::text
    FROM public.users u
    WHERE u.email = p_email
$$;
"""

BY_EMAIL_BEFORE = """
CREATE FUNCTION auth_account_by_email(p_email text)
RETURNS TABLE (id text, email text, "firstName" text, "lastName" text, role text,
               department text, "avatarUrl" text, "isActive" boolean, "isVerified" boolean,
               "createdAt" timestamp, token_version integer, "hashedPassword" text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT u.id::text, u.email::text, u."firstName"::text, u."lastName"::text, u.role::text,
           u.department::text, u."avatarUrl"::text, u."isActive", u."isVerified", u."createdAt",
           u.token_version, u."hashedPassword"::text
    FROM public.users u
    WHERE u.email = p_email
$$;
"""

SET_LOCALE = """
CREATE FUNCTION auth_set_locale(p_locale text)
RETURNS text
LANGUAGE sql VOLATILE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    -- The caller's own row and nothing else: the identity the request carries.
    UPDATE public.users SET locale = p_locale
     WHERE id = nullif(current_setting('app.user_id', true), '')
    RETURNING locale::text
$$;
"""


def _execute_for_app(function: str) -> str:
    return f"""
    DO $$
    BEGIN
        REVOKE ALL ON FUNCTION {function} FROM PUBLIC;
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
            GRANT EXECUTE ON FUNCTION {function} TO dixpertia_app;
        END IF;
    END
    $$;
    """


def _column_grants(privilege: str, column: str, grant: bool) -> str:
    verb = "GRANT" if grant else "REVOKE"
    direction = "TO" if grant else "FROM"
    return f"""
    DO $$
    BEGIN
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
            {verb} {privilege} ({column}) ON TABLE users {direction} dixpertia_app;
        END IF;
    END
    $$;
    """


def upgrade():
    op.add_column('users', sa.Column('locale', sa.String(length=2), server_default='fr', nullable=False))
    op.create_check_constraint('ck_users_locale', 'users', f"locale IN {LOCALES}")
    op.add_column('clients', sa.Column('locale', sa.String(length=2), server_default='fr', nullable=False))
    op.create_check_constraint('ck_clients_locale', 'clients', f"locale IN {LOCALES}")
    op.add_column('notifications', sa.Column('params', postgresql.JSONB(), nullable=True))

    # users is under column-level grants since #76: the new column needs its own.
    op.execute(_column_grants("SELECT", "locale", True))
    op.execute(_column_grants("UPDATE", "locale", True))

    op.execute("DROP FUNCTION auth_account_by_email(text)")
    op.execute(BY_EMAIL_WITH_LOCALE)
    op.execute(_execute_for_app("auth_account_by_email(text)"))
    op.execute(SET_LOCALE)
    op.execute(_execute_for_app("auth_set_locale(text)"))


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS auth_set_locale(text)")
    op.execute("DROP FUNCTION auth_account_by_email(text)")
    op.execute(BY_EMAIL_BEFORE)
    op.execute(_execute_for_app("auth_account_by_email(text)"))
    op.execute(_column_grants("UPDATE", "locale", False))
    op.execute(_column_grants("SELECT", "locale", False))
    op.drop_column('notifications', 'params')
    op.drop_constraint('ck_clients_locale', 'clients', type_='check')
    op.drop_column('clients', 'locale')
    op.drop_constraint('ck_users_locale', 'users', type_='check')
    op.drop_column('users', 'locale')
