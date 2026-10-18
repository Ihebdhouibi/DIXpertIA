"""server-side notifications

Revision ID: ba22aef318bc
Revises: 0a9e93edb45b
Create Date: 2026-10-14 18:30:00.000000

#116: notifications were made in the browser and lived only in the session,
so the accountant was never told an invoice was waiting for verification
unless she happened to look, and nothing survived a reload or another device.
They are now rows on the server, one per recipient, written by the server on
workflow events (#118: submitted, rejected, approved).

- `kind` names the event; `tone` is how the UI shows it; `link` is the screen
  to open; `ref_type`/`ref_id` point at the record it is about.
- `read_at` is the read state. `dismissed_at` is "cleared" from the list: a
  soft dismissal, so the application role needs no DELETE on this table
  (db/sql/001-roles-and-grants.sql keeps DELETE to the tables that need it).

ROW-LEVEL SECURITY. A user reads, marks and dismisses only their own
notifications. Writing one is different: the person acting is rarely the one
to be told - the admin submits, the accountants are notified - so any signed-in
role may insert, for any recipient. The insert policy only requires an
identity, and the API never lets a client choose recipients: notify() is
called by the server on events.
"""
from alembic import op
import sqlalchemy as sa

revision = 'ba22aef318bc'
down_revision = '0a9e93edb45b'
branch_labels = None
depends_on = None

UID = "nullif(current_setting('app.user_id', true), '')"
ROLE = "nullif(current_setting('app.user_role', true), '')"


def upgrade():
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('kind', sa.String(length=40), nullable=False),
        sa.Column('tone', sa.String(length=10), server_default='info', nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('link', sa.String(length=40), server_default='', nullable=False),
        sa.Column('ref_type', sa.String(length=30), nullable=True),
        sa.Column('ref_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        # A notification belongs to its recipient: it goes with the account.
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("tone IN ('info', 'success', 'warning', 'error')", name='ck_notifications_tone'),
    )
    # The bell's query: this user's live notifications, newest first.
    op.create_index('ix_notifications_user_live', 'notifications', ['user_id', 'created_at'],
                    postgresql_where=sa.text('dismissed_at IS NULL'))

    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY notifications_owner_all ON notifications
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY notifications_read_own ON notifications
        FOR SELECT TO dixpertia_app
        USING (user_id = {UID})
    """)
    op.execute(f"""
        CREATE POLICY notifications_update_own ON notifications
        FOR UPDATE TO dixpertia_app
        USING (user_id = {UID}) WITH CHECK (user_id = {UID})
    """)
    op.execute(f"""
        CREATE POLICY notifications_written_by_the_server ON notifications
        FOR INSERT TO dixpertia_app
        WITH CHECK ({ROLE} IS NOT NULL)
    """)


def downgrade():
    for policy in ('notifications_written_by_the_server', 'notifications_update_own',
                   'notifications_read_own', 'notifications_owner_all'):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON notifications")
    op.drop_index('ix_notifications_user_live', table_name='notifications')
    op.drop_table('notifications')
