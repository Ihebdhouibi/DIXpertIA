"""add the accountant processing status to invoices

Revision ID: 6cafb780b3ed
Revises: 79239abcd291
Create Date: 2026-10-04 17:54:00.725373

Adds `processing_status` as a SECOND status axis on invoices (#41), alongside
the existing commercial `statut`. See InvoiceProcessingStatus in
app/models/invoicing.py for why these are two fields rather than one.

Archived is terminal, enforced here rather than in the application. Once an
invoice belongs to a closed month it cannot move back, and its number, client,
dates and amounts can no longer change: a mistake found after the close is
corrected by issuing a new document in the open month, never by editing a
closed one. That is what makes a closed month's totals final, and it is the
assumption the gapless-numbering rule in #38 is built on.

`statut` is deliberately NOT frozen by that rule. A client can pay in November
an invoice that was archived with October's books, and the commercial state
must be free to record it. Needing exactly that is why the two axes are
separate fields.

Autogenerate produced a downgrade that dropped the column but left the
`invoiceprocessingstatus` type behind, so a second upgrade failed with "type
already exists" - the same defect found in f1f441a6bc13. The type is dropped
explicitly below.
"""
from alembic import op
import sqlalchemy as sa

revision = '6cafb780b3ed'
down_revision = '79239abcd291'
branch_labels = None
depends_on = None

PROCESSING_STATUS = sa.Enum(
    'PENDING', 'PROCESSED', 'COMPLETED', 'ARCHIVED',
    name='invoiceprocessingstatus',
)

# Columns frozen once the invoice is archived. `statut` is absent on purpose:
# late payment of an invoice in a closed month must still be recordable.
FROZEN = ('numero', 'client_id', 'date_emission', 'date_echeance',
          'montant_ht', 'montant_ttc')

# Built by concatenation rather than %-formatting: the SQL below contains "%"
# as RAISE EXCEPTION's own placeholder, which Python's % operator would try to
# interpret as a format specifier and reject.
_FROZEN_CHANGED = "\n           OR ".join(
    f"NEW.{c} IS DISTINCT FROM OLD.{c}" for c in FROZEN
)

ARCHIVED_IS_FINAL = """
CREATE OR REPLACE FUNCTION trg_invoice_archived_is_final() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.processing_status = 'ARCHIVED' THEN
            RAISE EXCEPTION
                'invoice % belongs to a closed month and cannot be deleted; '
                'issue a credit note in the open month instead', OLD.numero;
        END IF;
        RETURN OLD;
    END IF;

    IF OLD.processing_status = 'ARCHIVED' THEN
        IF NEW.processing_status IS DISTINCT FROM OLD.processing_status THEN
            RAISE EXCEPTION
                'invoice % is archived; its month is closed and the processing '
                'status cannot move back', OLD.numero;
        END IF;
        IF """ + _FROZEN_CHANGED + """ THEN
            RAISE EXCEPTION
                'invoice % is archived and read-only; correct it with a new '
                'document in the open month', OLD.numero;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    PROCESSING_STATUS.create(op.get_bind(), checkfirst=True)
    op.add_column(
        'invoices',
        sa.Column('processing_status', PROCESSING_STATUS,
                  server_default='PENDING', nullable=False),
    )
    # Composite rather than a single column - see the model for the measured
    # reason. The paginated list uses neither; this earns its place on the
    # unbounded "awaiting me" count and the month-scoped close query.
    op.create_index('ix_invoices_processing_status', 'invoices',
                    ['processing_status', 'date_emission'], unique=False)
    op.execute(ARCHIVED_IS_FINAL)
    op.execute("""
        CREATE TRIGGER invoice_archived_is_final
        BEFORE UPDATE OR DELETE ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_archived_is_final()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS invoice_archived_is_final ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_archived_is_final()")
    op.drop_index('ix_invoices_processing_status', table_name='invoices')
    op.drop_column('invoices', 'processing_status')
    # Dropping the column does not drop the type it used.
    PROCESSING_STATUS.drop(op.get_bind(), checkfirst=True)
