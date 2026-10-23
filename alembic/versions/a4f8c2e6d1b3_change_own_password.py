"""changing one's own password

Revision ID: a4f8c2e6d1b3
Revises: bc66d5b01ae9
Create Date: 2026-10-23 18:00:00.000000

#220: the Settings "Change password" form submitted nothing, and the API had
no route for it, so a user who "changed" their password kept the old one and
was then locked out by #175 trying the new one.

The application role cannot write users."hashedPassword" (column grants,
#76): only auth_spend_account_token() could, through a reset link. This adds
auth_set_own_password(), a SECURITY DEFINER function for the signed-in
account, and only that account (app.user_id): it sets the new hash and bumps
token_version, which signs every other session out (#62). The API checks the
current password before calling it.
"""
from alembic import op

revision = 'a4f8c2e6d1b3'
down_revision = 'bc66d5b01ae9'
branch_labels = None
depends_on = None

SIGNATURE = 'auth_set_own_password(text, text)'
ME = "nullif(current_setting('app.user_id', true), '')"

FUNCTION = f"""
CREATE FUNCTION auth_set_own_password(p_user_id text, p_password_hash text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF {ME} IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'password: only the account itself can change its password' USING ERRCODE = '42501';
    END IF;
    UPDATE public.users SET "hashedPassword" = p_password_hash, token_version = token_version + 1
     WHERE id = p_user_id AND "isActive" AND "isVerified";
    RETURN FOUND;
END;
$$;
"""


def upgrade():
    op.execute(FUNCTION)
    op.execute(f"REVOKE ALL ON FUNCTION {SIGNATURE} FROM PUBLIC")
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT EXECUTE ON FUNCTION {SIGNATURE} TO dixpertia_app;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute(f"DROP FUNCTION IF EXISTS {SIGNATURE}")
