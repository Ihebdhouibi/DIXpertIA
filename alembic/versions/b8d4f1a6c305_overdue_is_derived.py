"""overdue is derived from the due date, never stored

Revision ID: b8d4f1a6c305
Revises: a7c3e5f9d218
Create Date: 2026-10-18 00:30:00.000000

#117. A stored EN_RETARD went stale the day after it was written, and nothing
in the application ever set it, so a late invoice showed as merely sent.
"Overdue" is now computed when an invoice is read: sent, and its due date has
passed (Invoice.displayed_status, and the same condition in the list filter).

Rows stored as EN_RETARD - only seed scripts wrote them - go back to ENVOYEE,
from which they are derived as overdue again if their due date has passed.
ck_invoices_overdue_is_derived then refuses storing it. The enum value stays:
PostgreSQL cannot drop one without rebuilding the type, and the API still
accepts it as a filter value meaning "derived overdue".
"""
from alembic import op

revision = 'b8d4f1a6c305'
down_revision = 'a7c3e5f9d218'
branch_labels = None
depends_on = None


def upgrade():
    # Allowed by trg_invoice_commercial_transitions (#126): sent and overdue
    # move between each other.
    op.execute("UPDATE invoices SET statut = 'ENVOYEE' WHERE statut = 'EN_RETARD'")
    op.create_check_constraint('ck_invoices_overdue_is_derived', 'invoices', "statut <> 'EN_RETARD'")


def downgrade():
    # The rows are not moved back: which ones were stored as overdue was never
    # meaningful, and the derived status still shows them correctly.
    op.drop_constraint('ck_invoices_overdue_is_derived', 'invoices', type_='check')
