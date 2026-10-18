"""invoice commercial transitions: paid and cancelled

Revision ID: a7c3e5f9d218
Revises: f6a2d9c4e1b7
Create Date: 2026-10-17 23:30:00.000000

#126. Nothing could mark an invoice paid or cancelled. Decided on the issue:

- PAID, by the admin or the accountant, for invoices we issue and bills we
  received: a payment date, in full. paid_on is not before the issue date nor
  in the future. Partial payments are not modelled.
- CANCELLED, by the admin, always with a reason. A draft has no legal number
  (#118), so cancelling it leaves no gap. An approved or sent invoice keeps
  its number in the series as ANNULEE; the credit note that answers it in the
  books is a separate document, not issued here.

trg_invoice_commercial_transitions holds the legal moves, so a direct SQL write
is refused too:

    BROUILLON          -> ENVOYEE (#118: approved first), ANNULEE
    ENVOYEE, EN_RETARD -> PAYEE, ANNULEE, and between each other (#117)
    PAYEE, ANNULEE     -> nothing: both are final

and refuses to cancel an invoice under verification (it is frozen until the
accountant decides, as for edits) or one whose month is closed (correct it in
the open month). Payment stays possible after the close: late payment is the
reason `statut` was left out of the archived seal (#41).

CHECKs tie the columns to the status: paid_on is set exactly when PAYEE, the
reason and time exactly when ANNULEE. Rows already PAYEE or ANNULEE come only
from development seed scripts (nothing is deployed): they are back-filled with
the issue date and a reason saying none was recorded.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7c3e5f9d218'
down_revision = 'f6a2d9c4e1b7'
branch_labels = None
depends_on = None

REF = "coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'))"

TRANSITIONS = f"""
CREATE OR REPLACE FUNCTION trg_invoice_commercial_transitions() RETURNS trigger AS $$
BEGIN
    IF OLD.statut IN ('PAYEE', 'ANNULEE') THEN
        IF NEW.statut IS DISTINCT FROM OLD.statut
           OR NEW.paid_on IS DISTINCT FROM OLD.paid_on
           OR NEW.cancelled_at IS DISTINCT FROM OLD.cancelled_at
           OR NEW.cancellation_reason IS DISTINCT FROM OLD.cancellation_reason THEN
            RAISE EXCEPTION 'invoice % is % and final', {REF}, lower(OLD.statut::text);
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.statut IS NOT DISTINCT FROM OLD.statut THEN
        RETURN NEW;
    END IF;

    IF NOT (
           (OLD.statut = 'BROUILLON' AND NEW.statut IN ('ENVOYEE', 'ANNULEE'))
        OR (OLD.statut IN ('ENVOYEE', 'EN_RETARD') AND NEW.statut IN ('PAYEE', 'ANNULEE', 'ENVOYEE', 'EN_RETARD'))
    ) THEN
        RAISE EXCEPTION 'invoice % cannot go from % to %', {REF},
            lower(OLD.statut::text), lower(NEW.statut::text);
    END IF;

    IF NEW.statut = 'ANNULEE' THEN
        IF OLD.review_status = 'SUBMITTED' THEN
            RAISE EXCEPTION 'invoice % is waiting for verification; the accountant approves or '
                'rejects it before it can be cancelled', {REF};
        END IF;
        IF OLD.processing_status = 'ARCHIVED' THEN
            RAISE EXCEPTION 'invoice % belongs to a closed month and cannot be cancelled; '
                'correct it with a credit note in the open month', {REF};
        END IF;
    END IF;

    IF NEW.statut = 'PAYEE' AND NEW.paid_on > current_date THEN
        RAISE EXCEPTION 'invoice % cannot be paid on %, a date in the future', {REF}, NEW.paid_on;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    op.add_column('invoices', sa.Column('paid_on', sa.Date(), nullable=True))
    op.add_column('invoices', sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invoices', sa.Column('cancellation_reason', sa.Text(), nullable=True))

    # Seed-script rows only; see the docstring. The triggers watching statut
    # do not fire: only these three new columns change.
    op.execute("UPDATE invoices SET paid_on = date_emission WHERE statut = 'PAYEE'")
    op.execute("""
        UPDATE invoices
           SET cancelled_at = now(),
               cancellation_reason = 'Cancelled before #126; no reason was recorded'
         WHERE statut = 'ANNULEE'
    """)

    op.create_check_constraint(
        'ck_invoices_paid_has_date', 'invoices',
        "(statut = 'PAYEE') = (paid_on IS NOT NULL)")
    op.create_check_constraint(
        'ck_invoices_paid_after_issue', 'invoices',
        "paid_on IS NULL OR paid_on >= date_emission")
    op.create_check_constraint(
        'ck_invoices_cancelled_has_reason', 'invoices',
        "(statut = 'ANNULEE') = (cancelled_at IS NOT NULL AND btrim(coalesce(cancellation_reason, '')) <> '')")

    op.execute(TRANSITIONS)
    op.execute("""
        CREATE TRIGGER invoice_commercial_transitions
        BEFORE UPDATE ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_commercial_transitions()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS invoice_commercial_transitions ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_commercial_transitions()")
    for name in ('ck_invoices_cancelled_has_reason', 'ck_invoices_paid_after_issue', 'ck_invoices_paid_has_date'):
        op.drop_constraint(name, 'invoices', type_='check')
    op.drop_column('invoices', 'cancellation_reason')
    op.drop_column('invoices', 'cancelled_at')
    op.drop_column('invoices', 'paid_on')
