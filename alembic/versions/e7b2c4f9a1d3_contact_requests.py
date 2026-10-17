"""contact requests from the public website

Revision ID: e7b2c4f9a1d3
Revises: c9e2a7b4d610
Create Date: 2026-10-18 23:00:00.000000

#98: the contact form validated its fields, then showed "Message received"
while nothing left the browser, so every genuine enquiry was lost. Each one is
now a row, every active admin is notified, and an e-mail goes to CONTACT_INBOX
once it is configured.

ACCESS. The sender is anonymous, so - as for the sign-in steps of #157 - the
form never touches a table directly. submit_contact_request() is a SECURITY
DEFINER function that does one thing: check the limits, store the enquiry and
notify the admins, under an advisory lock so concurrent submissions count
exactly. The application role may call it and nothing more anonymous: there is
no INSERT policy on contact_requests. Only the admin reads and updates them.

PRIVACY. The sender's IP is not stored, only an HMAC of it (sender_hash),
computed by the API with its secret: enough to count one sender's messages,
not to recover the address.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e7b2c4f9a1d3'
down_revision = 'c9e2a7b4d610'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"
SIGNATURE = 'submit_contact_request(text, text, text, text, text, integer, integer)'
TOPICS = ('security_audit', 'cloud_migration', 'custom_development', 'support_subscription', 'other')

SUBMIT = """
CREATE FUNCTION submit_contact_request(
    p_name text, p_email text, p_topic text, p_message text, p_sender_hash text,
    p_per_sender_per_hour integer, p_total_per_hour integer)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_id integer;
BEGIN
    -- One submission at a time, so two concurrent ones cannot both pass a limit.
    PERFORM pg_advisory_xact_lock(hashtext('contact_requests'));

    IF (SELECT count(*) FROM public.contact_requests
         WHERE sender_hash = p_sender_hash AND created_at > now() - interval '1 hour') >= p_per_sender_per_hour THEN
        RETURN -1;  -- this sender, too many this hour
    END IF;
    IF (SELECT count(*) FROM public.contact_requests
         WHERE created_at > now() - interval '1 hour') >= p_total_per_hour THEN
        RETURN -2;  -- everyone together, too many this hour
    END IF;

    INSERT INTO public.contact_requests (name, email, topic, message, sender_hash)
    VALUES (p_name, p_email, p_topic, p_message, p_sender_hash)
    RETURNING id INTO v_id;

    -- Every active admin is told, in their own language when they read it (#135).
    INSERT INTO public.notifications (user_id, kind, tone, message, link, ref_type, ref_id, params)
    SELECT u.id, 'contact_request', 'info',
           'New enquiry from ' || p_name || ' about ' || p_topic || '.',
           'enquiries', 'contact_request', v_id,
           jsonb_build_object('name', p_name, 'topic', p_topic)
      FROM public.users u
     WHERE u.role = 'admin' AND u."isActive";

    RETURN v_id;
END;
$$;
"""


def upgrade():
    op.create_table(
        'contact_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('email', sa.String(length=254), nullable=False),
        sa.Column('topic', sa.String(length=40), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sender_hash', sa.String(length=64), nullable=False),
        sa.Column('handled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('handled_by_id', sa.String(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=True),
        sa.CheckConstraint(f"topic IN ({', '.join(repr(t) for t in TOPICS)})", name='ck_contact_requests_topic'),
        sa.CheckConstraint("char_length(message) BETWEEN 10 AND 5000", name='ck_contact_requests_message'),
        sa.CheckConstraint("char_length(btrim(name)) BETWEEN 1 AND 120", name='ck_contact_requests_name'),
        sa.CheckConstraint("(handled_at IS NULL) = (handled_by_id IS NULL)", name='ck_contact_requests_handled'),
    )
    op.create_index('ix_contact_requests_sender', 'contact_requests', ['sender_hash', 'created_at'])
    op.create_index('ix_contact_requests_created_at', 'contact_requests', ['created_at'])

    op.execute("ALTER TABLE contact_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE contact_requests FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY contact_requests_owner_all ON contact_requests
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY contact_requests_read_by_admin ON contact_requests
        FOR SELECT TO dixpertia_app USING ({ROLE} = 'admin')
    """)
    op.execute(f"""
        CREATE POLICY contact_requests_handled_by_admin ON contact_requests
        FOR UPDATE TO dixpertia_app USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)

    op.execute(SUBMIT)
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
    op.drop_index('ix_contact_requests_created_at', table_name='contact_requests')
    op.drop_index('ix_contact_requests_sender', table_name='contact_requests')
    op.drop_table('contact_requests')
