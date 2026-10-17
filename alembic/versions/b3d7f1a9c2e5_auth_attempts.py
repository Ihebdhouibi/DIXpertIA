"""auth attempts: sign-in lockout and limits on the public routes

Revision ID: b3d7f1a9c2e5
Revises: e7b2c4f9a1d3
Create Date: 2026-10-18 12:00:00.000000

#175: nothing limited how often a caller may try. Sign-in accepted any number
of password guesses, forgot-password any number of reset e-mails.

Each attempt that counts against a limit is one row of auth_attempts: a
bucket (what is limited), a key (who), a time. A limit is "at most N rows in
this bucket for this key in the last W seconds". Kept in the database, not in
the API's memory, so it holds across workers and survives a restart.

ACCESS. The callers are anonymous, so - as for the contact form of #98 - the
application never touches the table: it has no policy on it and no grant.
Three SECURITY DEFINER functions do the work:
- auth_throttle_hit(): check a limit and, if there is room, record one
  attempt, under an advisory lock so concurrent attempts count exactly.
  Returns the attempt's id, or minus the seconds to wait.
- auth_throttle_forget(): drop one attempt (a sign-in that succeeded is not
  held against the address it came from).
- auth_throttle_clear(): drop a key's attempts in a bucket (a successful
  sign-in resets the account's failure counter).

PRIVACY. The key is an HMAC computed by the API with its secret, of the IP or
of the e-mail - never the address itself. Rows older than a day are deleted
on the way: no limit looks further back.
"""
from alembic import op
import sqlalchemy as sa

revision = 'b3d7f1a9c2e5'
down_revision = 'e7b2c4f9a1d3'
branch_labels = None
depends_on = None

BUCKETS = ('login_account', 'login_ip', 'reset_mail', 'public_ip')

HIT = 'auth_throttle_hit(text, text, integer, integer)'
FORGET = 'auth_throttle_forget(bigint)'
CLEAR = 'auth_throttle_clear(text, text)'

FUNCTIONS = """
CREATE FUNCTION auth_throttle_hit(p_bucket text, p_key text, p_limit integer, p_window_seconds integer)
RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_window interval := make_interval(secs => p_window_seconds);
    v_oldest_that_counts timestamptz;
    v_id bigint;
BEGIN
    -- One attempt per key at a time, so a burst of parallel requests cannot
    -- all pass the check before any of them is recorded.
    PERFORM pg_advisory_xact_lock(hashtext('auth_attempts:' || p_bucket || ':' || p_key));

    -- No limit looks back more than a day.
    DELETE FROM public.auth_attempts WHERE created_at < now() - interval '1 day';

    -- The p_limit-th most recent attempt in the window: while it is in the
    -- window, the key is at its limit, and it leaves the window first.
    SELECT created_at INTO v_oldest_that_counts
      FROM public.auth_attempts
     WHERE bucket = p_bucket AND key_hash = p_key AND created_at > now() - v_window
     ORDER BY created_at DESC
     OFFSET p_limit - 1 LIMIT 1;
    IF FOUND THEN
        RETURN -greatest(1, ceil(extract(epoch FROM v_oldest_that_counts + v_window - now())))::bigint;
    END IF;

    INSERT INTO public.auth_attempts (bucket, key_hash) VALUES (p_bucket, p_key) RETURNING id INTO v_id;
    RETURN v_id;
END;
$$;

CREATE FUNCTION auth_throttle_forget(p_id bigint)
RETURNS void
LANGUAGE sql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    DELETE FROM public.auth_attempts WHERE id = p_id;
$$;

CREATE FUNCTION auth_throttle_clear(p_bucket text, p_key text)
RETURNS void
LANGUAGE sql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    DELETE FROM public.auth_attempts WHERE bucket = p_bucket AND key_hash = p_key;
$$;
"""


def upgrade():
    op.create_table(
        'auth_attempts',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('bucket', sa.String(length=20), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(f"bucket IN ({', '.join(repr(b) for b in BUCKETS)})", name='ck_auth_attempts_bucket'),
        sa.CheckConstraint("key_hash ~ '^[0-9a-f]{64}$'", name='ck_auth_attempts_key_hash'),
    )
    op.create_index('ix_auth_attempts_key', 'auth_attempts', ['bucket', 'key_hash', 'created_at'])
    op.create_index('ix_auth_attempts_created_at', 'auth_attempts', ['created_at'])

    # Owner only. The application reaches the rows through the functions below.
    op.execute("ALTER TABLE auth_attempts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE auth_attempts FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY auth_attempts_owner_all ON auth_attempts
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)

    op.execute(FUNCTIONS)
    for signature in (HIT, FORGET, CLEAR):
        op.execute(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                REVOKE ALL ON TABLE auth_attempts FROM dixpertia_app;
                REVOKE ALL ON SEQUENCE auth_attempts_id_seq FROM dixpertia_app;
                GRANT EXECUTE ON FUNCTION {HIT} TO dixpertia_app;
                GRANT EXECUTE ON FUNCTION {FORGET} TO dixpertia_app;
                GRANT EXECUTE ON FUNCTION {CLEAR} TO dixpertia_app;
            END IF;
        END
        $$;
    """)


def downgrade():
    for signature in (CLEAR, FORGET, HIT):
        op.execute(f"DROP FUNCTION IF EXISTS {signature}")
    op.drop_index('ix_auth_attempts_created_at', table_name='auth_attempts')
    op.drop_index('ix_auth_attempts_key', table_name='auth_attempts')
    op.drop_table('auth_attempts')
