"""audit trail

Revision ID: d4b8e2f61a73
Revises: 7c1e5a9d2b40
Create Date: 2026-10-17 19:00:00.000000

#63 (AUDIT-DB-017): nothing recorded who did what. Approvals, invoice changes,
user creation and password resets could be neither attributed nor
reconstructed. `audit_events` holds one row per sensitive action, written by
app.services.audit.record_event() in the action's own transaction.

APPEND-ONLY, three ways:
- the application role holds INSERT and SELECT only: UPDATE, which the default
  privileges would grant, is revoked here and in db/sql/001-roles-and-grants.sql
  so re-running the grants does not restore it;
- trg_audit_events_are_append_only refuses UPDATE and DELETE from anyone,
  owner included, so a privileged mistake is refused too;
- TRUNCATE is never granted to the application role (it bypasses row triggers).

ROW-LEVEL SECURITY. Only the admin reads the trail. Any request may write to it,
but only in its own name: actor_id and actor_role must equal the identity the
request carries, or be NULL when nobody is signed in (the password-reset steps).
Code cannot record an action as somebody else.

The actor is a foreign key with RESTRICT: an account that acted cannot be
deleted from under its trail. Accounts are deactivated, not deleted (#62).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'd4b8e2f61a73'
down_revision = '7c1e5a9d2b40'
branch_labels = None
depends_on = None

UID = "nullif(current_setting('app.user_id', true), '')"
ROLE = "nullif(current_setting('app.user_role', true), '')"

APPEND_ONLY = """
CREATE OR REPLACE FUNCTION trg_audit_events_are_append_only() RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    RAISE EXCEPTION
        'audit event % cannot be changed or deleted: the audit trail is append-only',
        OLD.id;
END;
$$;
"""

REVOKE_CHANGES = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
        REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_events FROM dixpertia_app;
        GRANT SELECT, INSERT ON TABLE audit_events TO dixpertia_app;
        GRANT USAGE, SELECT ON SEQUENCE audit_events_id_seq TO dixpertia_app;
    END IF;
END
$$;
"""


def upgrade():
    op.create_table(
        'audit_events',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor_id', sa.String(), nullable=True),
        sa.Column('actor_role', sa.String(length=20), nullable=True),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('entity', sa.String(length=40), nullable=False),
        sa.Column('entity_id', sa.String(length=60), nullable=False),
        sa.Column('before', postgresql.JSONB(), nullable=True),
        sa.Column('after', postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    # The admin's filters: by date, by record, by person.
    op.create_index('ix_audit_events_occurred_at', 'audit_events', ['occurred_at'])
    op.create_index('ix_audit_events_entity', 'audit_events', ['entity', 'entity_id'])
    op.create_index('ix_audit_events_actor', 'audit_events', ['actor_id', 'occurred_at'])

    op.execute(APPEND_ONLY)
    op.execute("""
        CREATE TRIGGER audit_events_are_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION trg_audit_events_are_append_only()
    """)
    op.execute(REVOKE_CHANGES)

    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY audit_events_owner_all ON audit_events
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY audit_events_read_by_admin ON audit_events
        FOR SELECT TO dixpertia_app
        USING ({ROLE} = 'admin')
    """)
    op.execute(f"""
        CREATE POLICY audit_events_written_in_own_name ON audit_events
        FOR INSERT TO dixpertia_app
        WITH CHECK (actor_id IS NOT DISTINCT FROM {UID}
                    AND actor_role IS NOT DISTINCT FROM {ROLE})
    """)


def downgrade():
    for policy in ('audit_events_written_in_own_name', 'audit_events_read_by_admin',
                   'audit_events_owner_all'):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_are_append_only ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS trg_audit_events_are_append_only()")
    op.drop_index('ix_audit_events_actor', table_name='audit_events')
    op.drop_index('ix_audit_events_entity', table_name='audit_events')
    op.drop_index('ix_audit_events_occurred_at', table_name='audit_events')
    op.drop_table('audit_events')
