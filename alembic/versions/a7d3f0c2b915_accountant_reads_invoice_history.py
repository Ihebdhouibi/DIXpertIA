"""the accountant reads the invoice events of the audit trail

Revision ID: a7d3f0c2b915
Revises: a7c3e5f9d218
Create Date: 2026-10-18 10:00:00.000000

#115: an invoice's history - who created, corrected, submitted, approved,
rejected, sent it and moved it through the books, and when - is already in
the audit trail of #63, which only the admin may read. The accountant is the
one who books invoices and needs that history, so she may now read the events
whose entity is an invoice. Every other event (accounts, leave, periods) stays
admin-only. Read only: the trail stays append-only for everyone.
"""
from alembic import op

revision = 'a7d3f0c2b915'
down_revision = 'a7c3e5f9d218'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"


def upgrade():
    op.execute(f"""
        CREATE POLICY audit_events_invoice_history_read_by_accountant ON audit_events
        FOR SELECT TO dixpertia_app
        USING ({ROLE} = 'accountant' AND entity = 'invoice')
    """)


def downgrade():
    op.execute("DROP POLICY IF EXISTS audit_events_invoice_history_read_by_accountant ON audit_events")
