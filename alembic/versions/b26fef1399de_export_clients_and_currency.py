"""export clients and the invoice currency

Revision ID: b26fef1399de
Revises: 7f7ade292b74
Create Date: 2026-10-18 21:00:00.000000

#195: our clients abroad are billed for an export of services. Under the Code
de la TVA (art. 3-I and 11-I) a service used abroad carries no Tunisian VAT,
and the invoice says so. They pay in their own currency.

CLIENTS get three columns:
- `export`: the client is abroad and the service is used there. This flag,
  not the currency, is what removes the VAT - the legal criterion is where
  the service is used.
- `devise`: the currency their invoices are in, TND, EUR, USD or GBP.
- `identifiant_fiscal`: an optional tax ID (a foreign VAT number, or a
  Tunisian client's matricule fiscal, #189), printed only when filled.

`ck_clients_export_in_foreign_currency` holds the rule decided for this
release: an export client always pays in a foreign currency. It may be lifted
later; it lives in this one constraint, so dropping it is enough.

INVOICES get `devise` and `export`, copied from the client when the invoice is
created and never changed after (`invoice_currency_is_fixed`). An issued
invoice must reprint exactly as the client received it, whatever happens to
the client record later. Existing invoices are in TND and not export.

`export_lines_carry_no_vat` on invoice_items: a line of an export invoice has
no VAT. The API checks it first and answers with the line; the trigger makes
sure a direct write cannot get round it either.

No grant or policy change: the columns belong to tables whose policies already
cover every column. Supplier bills keep the defaults (TND, not export).
"""
from alembic import op
import sqlalchemy as sa

revision = 'b26fef1399de'
down_revision = '7f7ade292b74'
branch_labels = None
depends_on = None

CURRENCIES = "devise IN ('TND', 'EUR', 'USD', 'GBP')"

CURRENCY_IS_FIXED = """
CREATE OR REPLACE FUNCTION trg_invoice_currency_is_fixed() RETURNS trigger AS $$
BEGIN
    IF NEW.devise IS DISTINCT FROM OLD.devise OR NEW.export IS DISTINCT FROM OLD.export THEN
        RAISE EXCEPTION
            'the currency and export status of invoice % are set when it is created; they cannot change',
            COALESCE(OLD.numero, 'BR-' || lpad(OLD.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

EXPORT_LINES_CARRY_NO_VAT = """
CREATE OR REPLACE FUNCTION trg_export_lines_carry_no_vat() RETURNS trigger AS $$
DECLARE
    parent record;
BEGIN
    SELECT id, numero, export INTO parent FROM invoices WHERE id = NEW.invoice_id;
    IF parent.export AND COALESCE(NEW.taux_tva, 0) <> 0 THEN
        RAISE EXCEPTION
            'invoice % is an export of services; its lines carry no VAT',
            COALESCE(parent.numero, 'BR-' || lpad(parent.id::text, 4, '0'));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    op.add_column('clients', sa.Column('export', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('clients', sa.Column('devise', sa.String(3), server_default='TND', nullable=False))
    op.add_column('clients', sa.Column('identifiant_fiscal', sa.String(50), nullable=True))
    op.create_check_constraint('ck_clients_devise', 'clients', CURRENCIES)
    op.create_check_constraint('ck_clients_export_in_foreign_currency', 'clients', "NOT export OR devise <> 'TND'")

    op.add_column('invoices', sa.Column('devise', sa.String(3), server_default='TND', nullable=False))
    op.add_column('invoices', sa.Column('export', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_check_constraint('ck_invoices_devise', 'invoices', CURRENCIES)

    op.execute(CURRENCY_IS_FIXED)
    op.execute("""
        CREATE TRIGGER invoice_currency_is_fixed
        BEFORE UPDATE OF devise, export ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_currency_is_fixed()
    """)
    op.execute(EXPORT_LINES_CARRY_NO_VAT)
    op.execute("""
        CREATE TRIGGER export_lines_carry_no_vat
        BEFORE INSERT OR UPDATE OF taux_tva, invoice_id ON invoice_items
        FOR EACH ROW EXECUTE FUNCTION trg_export_lines_carry_no_vat()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS export_lines_carry_no_vat ON invoice_items")
    op.execute("DROP FUNCTION IF EXISTS trg_export_lines_carry_no_vat()")
    op.execute("DROP TRIGGER IF EXISTS invoice_currency_is_fixed ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_currency_is_fixed()")
    op.drop_constraint('ck_invoices_devise', 'invoices', type_='check')
    op.drop_column('invoices', 'export')
    op.drop_column('invoices', 'devise')
    op.drop_constraint('ck_clients_export_in_foreign_currency', 'clients', type_='check')
    op.drop_constraint('ck_clients_devise', 'clients', type_='check')
    op.drop_column('clients', 'identifiant_fiscal')
    op.drop_column('clients', 'devise')
    op.drop_column('clients', 'export')
