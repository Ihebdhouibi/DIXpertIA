"""row-level security on users, and no password hash for the application role

Revision ID: f6a2d9c4e1b7
Revises: e5f1c3a8b902
Create Date: 2026-10-17 23:00:00.000000

#76. #43 put row-level security on the business tables but left `users` out,
because sign-in reads the table before anyone is identified. Closed here, in
two layers:

COLUMNS. The application role no longer reads users."hashedPassword" at all,
not even on its own row: SELECT is granted column by column, without it.
UPDATE is limited to the columns an admin edits; the password is set only
through the functions below. INSERT stays table-wide (a new account is created
with an unusable placeholder hash). db/sql/001-roles-and-grants.sql repeats
this after its blanket grant, so re-running it does not give the column back.

ROWS. Admin, accountant and the reminder job (#134) read every account:
payslips and the invoice review history show other people's names, and the
reminders are e-mailed to accountants. Everyone else reads only their own row.
Only the admin creates or edits accounts.

The steps that run before anyone is identified go through SECURITY DEFINER
functions, owned by the schema owner, which the users_owner_all policy lets
through. Each returns only what its step needs, pins search_path, and is
executable by the application role alone (EXECUTE revoked from PUBLIC):

- auth_account_by_email(email): sign-in and forgot-password. The only way the
  hash reaches the application, for the one comparison bcrypt makes.
- auth_session(user id): the per-request check of #62 - role, status and
  token_version, no hash.
- auth_spend_account_token(token, purpose, new hash): a reset or activation
  link. It takes the token itself and hashes it here, so reading
  account_tokens (which holds only hashes) is no way to set a password. One
  statement checks the link is live, spends it, sets the password, activates
  the account if that is the purpose, and bumps token_version.

A dedicated BYPASSRLS role, as the issue proposed, was not needed: the owner
already passes the policies, and a new role would mean another superuser
provisioning step for no narrower access to these two tables.
"""
from alembic import op

revision = 'f6a2d9c4e1b7'
down_revision = 'e5f1c3a8b902'
branch_labels = None
depends_on = None

UID = "nullif(current_setting('app.user_id', true), '')"
ROLE = "nullif(current_setting('app.user_role', true), '')"

READABLE = ('id', 'email', '"firstName"', '"lastName"', 'role', 'department', '"avatarUrl"',
            '"isActive"', '"isVerified"', '"createdAt"', 'token_version')
EDITABLE = ('"firstName"', '"lastName"', 'role', 'department', '"avatarUrl"',
            '"isActive"', '"isVerified"', 'token_version')

COLUMN_GRANTS = f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        REVOKE SELECT, UPDATE ON TABLE users FROM dixpertia_app;
        GRANT SELECT ({', '.join(READABLE)}) ON TABLE users TO dixpertia_app;
        GRANT UPDATE ({', '.join(EDITABLE)}) ON TABLE users TO dixpertia_app;
    END IF;
END
$$;
"""

BY_EMAIL = """
CREATE FUNCTION auth_account_by_email(p_email text)
RETURNS TABLE (id text, email text, "firstName" text, "lastName" text, role text,
               department text, "avatarUrl" text, "isActive" boolean, "isVerified" boolean,
               "createdAt" timestamp, token_version integer, "hashedPassword" text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    -- Explicit casts: the columns are varchar, the declared results text.
    SELECT u.id::text, u.email::text, u."firstName"::text, u."lastName"::text, u.role::text,
           u.department::text, u."avatarUrl"::text, u."isActive", u."isVerified", u."createdAt",
           u.token_version, u."hashedPassword"::text
    FROM public.users u
    WHERE u.email = p_email
$$;
"""

SESSION = """
CREATE FUNCTION auth_session(p_user_id text)
RETURNS TABLE (role text, "isActive" boolean, "isVerified" boolean, token_version integer)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT u.role::text, u."isActive", u."isVerified", u.token_version
    FROM public.users u
    WHERE u.id = p_user_id
$$;
"""

SPEND = """
CREATE FUNCTION auth_spend_account_token(p_token text, p_purpose text, p_password_hash text)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id text;
BEGIN
    -- Spend the link only if it is live, for this purpose, and its account is
    -- active. The UPDATE takes the row lock, so two requests cannot both spend it.
    UPDATE public.account_tokens t
       SET used_at = now()
      FROM public.users u
     WHERE t.token_hash = encode(sha256(convert_to(p_token, 'UTF8')), 'hex')
       AND t.purpose = p_purpose
       AND t.used_at IS NULL
       AND t.expires_at > now()
       AND u.id = t.user_id
       AND u."isActive"
    RETURNING t.user_id INTO v_user_id;

    IF v_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    UPDATE public.users
       SET "hashedPassword" = p_password_hash,
           "isVerified" = "isVerified" OR p_purpose = 'activation',
           token_version = token_version + 1
     WHERE id = v_user_id;
    RETURN v_user_id;
END;
$$;
"""

FUNCTIONS = ('auth_account_by_email(text)', 'auth_session(text)',
             'auth_spend_account_token(text, text, text)')

EXECUTE_GRANTS = f"""
DO $$
BEGIN
    {' '.join(f'REVOKE ALL ON FUNCTION {f} FROM PUBLIC;' for f in FUNCTIONS)}
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        {' '.join(f'GRANT EXECUTE ON FUNCTION {f} TO dixpertia_app;' for f in FUNCTIONS)}
    END IF;
END
$$;
"""


def upgrade():
    op.execute(BY_EMAIL)
    op.execute(SESSION)
    op.execute(SPEND)
    op.execute(EXECUTE_GRANTS)
    op.execute(COLUMN_GRANTS)

    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_owner_all ON users
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY users_read ON users
        FOR SELECT TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant', 'reminders') OR id = {UID})
    """)
    op.execute(f"""
        CREATE POLICY users_created_by_admin ON users
        FOR INSERT TO dixpertia_app
        WITH CHECK ({ROLE} = 'admin')
    """)
    op.execute(f"""
        CREATE POLICY users_edited_by_admin ON users
        FOR UPDATE TO dixpertia_app
        USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)


def downgrade():
    for policy in ('users_edited_by_admin', 'users_created_by_admin', 'users_read', 'users_owner_all'):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON users")
    op.execute("ALTER TABLE users NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT SELECT, UPDATE ON TABLE users TO dixpertia_app;
            END IF;
        END
        $$;
    """)
    for function in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {function}")
