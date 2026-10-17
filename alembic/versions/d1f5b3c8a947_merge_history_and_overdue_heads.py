"""merge the #115 and #117 migration heads

Revision ID: d1f5b3c8a947
Revises: a7d3f0c2b915, b8d4f1a6c305
Create Date: 2026-10-18 03:00:00.000000

#115 (accountant reads invoice history) and #117 (overdue is derived) were
written in parallel, both on a7c3e5f9d218 (#126). Each passed CI alone; merged
together they left two heads, and `alembic upgrade head` refused to choose, so
every test setup on develop failed.

They touch unrelated things - a read policy on audit_events, a CHECK on
invoices - so the order between them does not matter and this revision
changes nothing. It only joins the history back into one line.
"""

revision = 'd1f5b3c8a947'
down_revision = ('a7d3f0c2b915', 'b8d4f1a6c305')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
