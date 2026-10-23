"""two-factor authentication: TOTP secrets and recovery codes

Revision ID: e9c3a1f7b204
Revises: a4f8c2e6d1b3
Create Date: 2026-10-23 12:00:00.000000

#44: a second factor - a 6-digit code from an authenticator app - on top of
the password, with single-use recovery codes for a lost phone.

STORAGE. Two tables, neither readable by the application role:
- user_mfa: one row per account that began enrolment. `secret_enc` is the
  TOTP secret ENCRYPTED by the API (Fernet, MFA_ENCRYPTION_KEY, a key that
  never enters the database): read access to the database alone cannot mint
  codes. `last_step` is the time step of the last code accepted, so a code
  cannot be replayed inside its 30-second window.
- user_mfa_recovery: an HMAC of each recovery code, keyed with the same
  secret key, never the code itself; `used_at` once spent.

ACCESS. As for sign-in (#76) and the rate limits (#175), the application
reaches these rows only through SECURITY DEFINER functions, each doing one
thing. The ones that change an account's second factor check that the caller
IS that account (app.user_id), or the admin for a reset; the ones the sign-in
needs before anyone is identified only read the state or spend a code.
Enabling, disabling or resetting the second factor bumps the account's
token_version: every session issued before is refused (#62).

RATE LIMIT. A new auth_attempts bucket, `mfa_account`: code attempts per
account, so the million 6-digit codes cannot be tried.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e9c3a1f7b204'
down_revision = 'a4f8c2e6d1b3'
branch_labels = None
depends_on = None

ME = "nullif(current_setting('app.user_id', true), '')"
ROLE = "nullif(current_setting('app.user_role', true), '')"

FUNCTIONS = {
    # The state the sign-in needs: whether the second factor is on, the
    # encrypted secret to check a code against, the last step used.
    'auth_mfa_state(text)': """
CREATE FUNCTION auth_mfa_state(p_user_id text)
RETURNS TABLE (enabled boolean, secret_enc text, last_step bigint, recovery_left integer)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT m.enabled, m.secret_enc, m.last_step,
           (SELECT count(*)::integer FROM public.user_mfa_recovery r
             WHERE r.user_id = m.user_id AND r.used_at IS NULL)
      FROM public.user_mfa m
     WHERE m.user_id = p_user_id
$$;
""",
    # Enrolment, step 1: a new secret, not yet active. Refused while a second
    # factor is active: switching phones goes through disable, then enrol.
    'auth_mfa_begin(text, text)': f"""
CREATE FUNCTION auth_mfa_begin(p_user_id text, p_secret_enc text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF {ME} IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'mfa: only the account itself can enrol' USING ERRCODE = '42501';
    END IF;
    IF EXISTS (SELECT 1 FROM public.user_mfa WHERE user_id = p_user_id AND enabled) THEN
        RETURN false;
    END IF;
    INSERT INTO public.user_mfa (user_id, secret_enc) VALUES (p_user_id, p_secret_enc)
    ON CONFLICT (user_id) DO UPDATE SET secret_enc = EXCLUDED.secret_enc, last_step = NULL,
                                        created_at = now();
    RETURN true;
END;
$$;
""",
    # Enrolment, step 2: a working code was proven. Activates, stores the
    # recovery codes, and signs every other session out.
    'auth_mfa_enable(text, bigint, text[])': f"""
CREATE FUNCTION auth_mfa_enable(p_user_id text, p_step bigint, p_recovery_hashes text[])
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF {ME} IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'mfa: only the account itself can enrol' USING ERRCODE = '42501';
    END IF;
    UPDATE public.user_mfa SET enabled = true, confirmed_at = now(), last_step = p_step
     WHERE user_id = p_user_id AND NOT enabled AND (last_step IS NULL OR last_step < p_step);
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    DELETE FROM public.user_mfa_recovery WHERE user_id = p_user_id;
    INSERT INTO public.user_mfa_recovery (user_id, code_hash)
    SELECT p_user_id, h FROM unnest(p_recovery_hashes) AS h;
    UPDATE public.users SET token_version = token_version + 1 WHERE id = p_user_id;
    RETURN true;
END;
$$;
""",
    # A code was accepted at sign-in: record its step, atomically. False when
    # this step, or a later one, was already used - a replay.
    'auth_mfa_use_step(text, bigint)': """
CREATE FUNCTION auth_mfa_use_step(p_user_id text, p_step bigint)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    UPDATE public.user_mfa SET last_step = p_step
     WHERE user_id = p_user_id AND enabled AND (last_step IS NULL OR last_step < p_step);
    RETURN FOUND;
END;
$$;
""",
    # A recovery code at sign-in: spent once, atomically.
    'auth_mfa_use_recovery(text, text)': """
CREATE FUNCTION auth_mfa_use_recovery(p_user_id text, p_code_hash text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    UPDATE public.user_mfa_recovery SET used_at = now()
     WHERE user_id = p_user_id AND code_hash = p_code_hash AND used_at IS NULL
       AND EXISTS (SELECT 1 FROM public.user_mfa m WHERE m.user_id = p_user_id AND m.enabled);
    RETURN FOUND;
END;
$$;
""",
    # New recovery codes, replacing the old ones. The account itself only.
    'auth_mfa_replace_recovery(text, text[])': f"""
CREATE FUNCTION auth_mfa_replace_recovery(p_user_id text, p_recovery_hashes text[])
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF {ME} IS DISTINCT FROM p_user_id THEN
        RAISE EXCEPTION 'mfa: only the account itself can renew its codes' USING ERRCODE = '42501';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM public.user_mfa WHERE user_id = p_user_id AND enabled) THEN
        RETURN false;
    END IF;
    DELETE FROM public.user_mfa_recovery WHERE user_id = p_user_id;
    INSERT INTO public.user_mfa_recovery (user_id, code_hash)
    SELECT p_user_id, h FROM unnest(p_recovery_hashes) AS h;
    RETURN true;
END;
$$;
""",
    # Remove the second factor: the account itself, or the admin (a lost
    # phone). Signs every session of the account out.
    'auth_mfa_remove(text)': f"""
CREATE FUNCTION auth_mfa_remove(p_user_id text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF {ME} IS DISTINCT FROM p_user_id AND {ROLE} IS DISTINCT FROM 'admin' THEN
        RAISE EXCEPTION 'mfa: only the account itself or the admin' USING ERRCODE = '42501';
    END IF;
    DELETE FROM public.user_mfa_recovery WHERE user_id = p_user_id;
    DELETE FROM public.user_mfa WHERE user_id = p_user_id;
    IF NOT FOUND THEN
        RETURN false;
    END IF;
    UPDATE public.users SET token_version = token_version + 1 WHERE id = p_user_id;
    RETURN true;
END;
$$;
""",
}

BUCKETS_BEFORE = ('login_account', 'login_ip', 'reset_mail', 'public_ip')
BUCKETS_AFTER = BUCKETS_BEFORE + ('mfa_account',)


def _bucket_check(buckets):
    op.drop_constraint('ck_auth_attempts_bucket', 'auth_attempts', type_='check')
    op.create_check_constraint('ck_auth_attempts_bucket', 'auth_attempts',
                               f"bucket IN ({', '.join(repr(b) for b in buckets)})")


def upgrade():
    op.create_table(
        'user_mfa',
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True),
        sa.Column('secret_enc', sa.Text(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_step', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("enabled = (confirmed_at IS NOT NULL)", name='ck_user_mfa_confirmed'),
    )
    op.create_table(
        'user_mfa_recovery',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("code_hash ~ '^[0-9a-f]{64}$'", name='ck_user_mfa_recovery_hash'),
        sa.UniqueConstraint('user_id', 'code_hash', name='uq_user_mfa_recovery_code'),
    )

    # Owner only: the application reaches these through the functions.
    for table in ('user_mfa', 'user_mfa_recovery'):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_owner_all ON {table}
            FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
        """)

    for ddl in FUNCTIONS.values():
        op.execute(ddl)
    for signature in FUNCTIONS:
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    grants = "\n".join(f"GRANT EXECUTE ON FUNCTION {s} TO dixpertia_app;" for s in FUNCTIONS)
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                REVOKE ALL ON TABLE user_mfa, user_mfa_recovery FROM dixpertia_app;
                REVOKE ALL ON SEQUENCE user_mfa_recovery_id_seq FROM dixpertia_app;
                {grants}
            END IF;
        END
        $$;
    """)

    _bucket_check(BUCKETS_AFTER)


def downgrade():
    op.execute("DELETE FROM auth_attempts WHERE bucket = 'mfa_account'")
    _bucket_check(BUCKETS_BEFORE)
    for signature in FUNCTIONS:
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.drop_table('user_mfa_recovery')
    op.drop_table('user_mfa')
