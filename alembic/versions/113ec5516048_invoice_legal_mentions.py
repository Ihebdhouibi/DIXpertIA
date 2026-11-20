"""invoice legal mentions: stamp duty, business clients

Revision ID: 113ec5516048
Revises: c5e8a2d4f716
Create Date: 2026-11-18 12:00:00.000000

#189: every invoice we issue carries the mentions Tunisian law requires.

INVOICES get `droit_timbre`, the stamp duty (timbre fiscal), in TND with
millimes. The API sets it from STAMP_DUTY_AMOUNT when an outgoing draft is
created or edited, so the accountant verifies the amount the client will pay.
It is kept apart from montant_ttc: ttc - ht stays the VAT the books and the
VAT return read (#40). The amount due is montant_ttc + droit_timbre.
- `ck_invoices_stamp_duty`: never negative, and 0 on an export invoice, which
  carries none (#195), and on an invoice in another currency than TND: the
  stamp duty is an amount in dinars.
- `invoice_draft_is_editable` now also watches `droit_timbre`: once a draft is
  submitted, the stamp duty is fixed with the totals, and an issued invoice
  reprints as issued whatever the setting becomes.

Existing invoices: every invoice already approved keeps 0, because it was
issued without stamp duty and must not change. Outgoing drafts not yet
approved, not export and in TND get 1.000, the default of STAMP_DUTY_AMOUNT, so that
none is approved without it. That includes drafts numbered before #118 moved
numbering to approval: a number does not make a draft issued. This runs
before the trigger watches the column.

CLIENTS get `entreprise`: a business rather than a private person. A business
in Tunisia must have its matricule fiscal (identifiant_fiscal). The rule lives
in the API and in the approval check, not in a CHECK, so that a client
recorded before it can still be opened and completed. Existing clients are
recorded as private persons until someone says otherwise.

CLIENTS: the currency rule of #195 becomes symmetric. An export client pays
in a foreign currency, and now a client in Tunisia pays in TND, so that a
domestic invoice never shows the stamp duty in euros.
`ck_clients_currency_follows_export` replaces
`ck_clients_export_in_foreign_currency`. A client in Tunisia recorded in a
foreign currency makes this migration fail on the CHECK: correct it first
(none existed when this was written). Whether such a client may pay in euros
is an open question for the accountant (#195).

No grant or policy change: the columns belong to tables whose policies and
grants already cover every column.
"""
from alembic import op
import sqlalchemy as sa

revision = '113ec5516048'
down_revision = 'c5e8a2d4f716'
branch_labels = None
depends_on = None

# #118's function (0a9e93edb45b), with droit_timbre among the frozen amounts.
DRAFT_IS_EDITABLE = """
CREATE OR REPLACE FUNCTION trg_invoice_draft_is_editable() RETURNS trigger AS $$
BEGIN
    IF OLD.direction = 'OUTGOING'
       AND (OLD.statut <> 'BROUILLON' OR OLD.review_status IN ('SUBMITTED', 'APPROVED'))
       AND (   NEW.date_echeance IS DISTINCT FROM OLD.date_echeance
            OR NEW.montant_ht IS DISTINCT FROM OLD.montant_ht
            OR NEW.montant_ttc IS DISTINCT FROM OLD.montant_ttc
            OR NEW.droit_timbre IS DISTINCT FROM OLD.droit_timbre) THEN
        RAISE EXCEPTION
            'invoice % is under review or no longer a draft and cannot be edited',
            coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

# Exactly as 0a9e93edb45b left it, for the downgrade.
DRAFT_IS_EDITABLE_BEFORE = """
CREATE OR REPLACE FUNCTION trg_invoice_draft_is_editable() RETURNS trigger AS $$
BEGIN
    IF OLD.direction = 'OUTGOING'
       AND (OLD.statut <> 'BROUILLON' OR OLD.review_status IN ('SUBMITTED', 'APPROVED'))
       AND (   NEW.date_echeance IS DISTINCT FROM OLD.date_echeance
            OR NEW.montant_ht IS DISTINCT FROM OLD.montant_ht
            OR NEW.montant_ttc IS DISTINCT FROM OLD.montant_ttc) THEN
        RAISE EXCEPTION
            'invoice % is under review or no longer a draft and cannot be edited',
            coalesce(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _trigger(columns: str):
    op.execute("DROP TRIGGER IF EXISTS invoice_draft_is_editable ON invoices")
    op.execute(f"""
        CREATE TRIGGER invoice_draft_is_editable
        BEFORE UPDATE OF {columns} ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_draft_is_editable()
    """)


def upgrade():
    op.add_column('clients', sa.Column('entreprise', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.drop_constraint('ck_clients_export_in_foreign_currency', 'clients', type_='check')
    op.create_check_constraint('ck_clients_currency_follows_export', 'clients', "(export) = (devise <> 'TND')")

    op.add_column('invoices', sa.Column('droit_timbre', sa.Numeric(10, 3), server_default='0', nullable=False))
    op.create_check_constraint('ck_invoices_stamp_duty', 'invoices',
                               "droit_timbre >= 0 AND (droit_timbre = 0 OR (NOT export AND devise = 'TND'))")
    op.execute("""
        UPDATE invoices SET droit_timbre = 1.000
        WHERE direction = 'OUTGOING' AND NOT export AND devise = 'TND'
          AND statut = 'BROUILLON' AND review_status <> 'APPROVED'
    """)

    op.execute(DRAFT_IS_EDITABLE)
    _trigger("date_echeance, montant_ht, montant_ttc, droit_timbre")


def downgrade():
    op.execute(DRAFT_IS_EDITABLE_BEFORE)
    _trigger("date_echeance, montant_ht, montant_ttc")
    op.drop_constraint('ck_invoices_stamp_duty', 'invoices', type_='check')
    op.drop_column('invoices', 'droit_timbre')
    op.drop_constraint('ck_clients_currency_follows_export', 'clients', type_='check')
    op.create_check_constraint('ck_clients_export_in_foreign_currency', 'clients', "NOT export OR devise <> 'TND'")
    op.drop_column('clients', 'entreprise')
