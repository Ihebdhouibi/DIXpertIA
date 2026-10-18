"""the reminder job reads the verification flow

Revision ID: 7c1e5a9d2b40
Revises: c3e1a7d94b20
Create Date: 2026-10-17 16:00:00.000000

#134: a periodic job reminds whoever has to act on an invoice stuck in the
verification flow (#118). It acts for nobody, so it does not borrow a user's
identity: it sets app.user_role to "reminders", and these policies let that
role READ what it needs - invoices, their review history, clients for the
message, and notifications to avoid writing the same reminder twice. Nothing
more: no update, no delete, no other table. It writes its reminders through
notifications_written_by_the_server, like any server event.

No account can hold the role: ck_users_role limits users.role to admin,
employee and accountant, and identity comes from a token issued for a user.
"""
from alembic import op

revision = '7c1e5a9d2b40'
down_revision = 'c3e1a7d94b20'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"
TABLES = ("invoices", "invoice_reviews", "clients", "notifications")


def upgrade():
    for table in TABLES:
        op.execute(f"""
            CREATE POLICY {table}_read_by_the_reminder_job ON {table}
            FOR SELECT TO dixpertia_app
            USING ({ROLE} = 'reminders')
        """)


def downgrade():
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_read_by_the_reminder_job ON {table}")
