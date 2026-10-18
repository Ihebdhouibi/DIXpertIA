"""invoice numbers run in issue-date order

Revision ID: 5524c45c0c4d
Revises: b806d5baf7f7
Create Date: 2026-10-05 15:48:03.117429

The accountant requires that invoice numbers run in the same order as their
issue dates: invoice 3 cannot be dated before invoice 2 (#39). Formally, within
one year's series, numero_a < numero_b implies date_emission_a <=
date_emission_b.

It held by accident until now. date_emission was hardcoded to date.today() and
InvoiceCreate never accepted it, so invoices could only be created in order.
That is an implementation detail, not a guarantee, and it breaks the moment
anything backdates, imports history, or edits a date.

The invariant holds BETWEEN rows, so a CHECK cannot express it; CHECK sees one
row. A trigger can, and a trigger is also the only place that catches
migrate_data.py and insert_invoices.py, which write to this database directly.

Dates may repeat. Several invoices are routinely issued on one day, so the rule
is "not earlier than", not "strictly later than" - otherwise the second invoice
of any morning would be refused.

Both directions are checked, because an UPDATE can break the order from either
side: moving an early invoice's date forward past a later one, or a later
invoice's date back before an earlier one.

Also adds a partial expression index over the series year and number. Both this
trigger and the gapless-series trigger from #38 extract those from `numero`
with substring(), which no ordinary index on `numero` can serve, so without it
every invoice insert scanned the table twice.
"""
from alembic import op

revision = '5524c45c0c4d'
down_revision = 'b806d5baf7f7'
branch_labels = None
depends_on = None

SERIES = "numero ~ '^FA-[0-9]{4}-[0-9]+$'"
YEAR = "substring(numero from 4 for 4)"
NUMBER = "substring(numero from 9)::integer"

CHRONOLOGICAL = f"""
CREATE OR REPLACE FUNCTION trg_invoice_number_follows_date() RETURNS trigger AS $$
DECLARE
    series_year text;
    this_number integer;
    clash       record;
BEGIN
    IF NOT (NEW.{SERIES}) THEN
        RETURN NEW;
    END IF;

    series_year := substring(NEW.numero from 4 for 4);
    this_number := substring(NEW.numero from 9)::integer;

    -- A lower number dated after this one.
    SELECT numero, date_emission INTO clash
    FROM invoices
    WHERE {SERIES}
      AND {YEAR} = series_year
      AND {NUMBER} < this_number
      AND date_emission > NEW.date_emission
    ORDER BY date_emission DESC
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION
            'invoice % dated % would come before %, which is numbered lower '
            'but dated %. Invoice numbers must follow issue dates',
            NEW.numero, NEW.date_emission, clash.numero, clash.date_emission;
    END IF;

    -- A higher number dated before this one.
    SELECT numero, date_emission INTO clash
    FROM invoices
    WHERE {SERIES}
      AND {YEAR} = series_year
      AND {NUMBER} > this_number
      AND date_emission < NEW.date_emission
    ORDER BY date_emission ASC
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION
            'invoice % dated % would come after %, which is numbered higher '
            'but dated %. Invoice numbers must follow issue dates',
            NEW.numero, NEW.date_emission, clash.numero, clash.date_emission;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    # Serves the substring() lookups in this trigger and in the #38 one. Partial,
    # because only the legal series is extracted this way.
    op.execute(f"""
        CREATE INDEX ix_invoices_series ON invoices
        (({YEAR}), ({NUMBER}))
        WHERE {SERIES}
    """)
    op.execute(CHRONOLOGICAL)
    op.execute("""
        CREATE TRIGGER invoice_number_follows_date
        BEFORE INSERT OR UPDATE OF date_emission, numero ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_number_follows_date()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS invoice_number_follows_date ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_number_follows_date()")
    op.execute("DROP INDEX IF EXISTS ix_invoices_series")
