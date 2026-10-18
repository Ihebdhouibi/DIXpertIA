"""model incoming and outgoing invoices with a suppliers table

Revision ID: 60fef7016faf
Revises: 5524c45c0c4d
Create Date: 2026-10-05 17:02:44.903155

Half the accountant's work had no representation: the system modelled only
invoices we issue (#40). Storing a supplier's bill meant inventing a row in
`clients`, so the client list silently mixed people who pay us with people we
pay, and two suppliers using the same house number - "2026-001" is ordinary -
collided on the global UNIQUE on `numero`.

ONE TABLE WITH A DIRECTION, not a second table. The monthly close, the periods,
the line items and every report want to see both, and a separate table would
have meant duplicating or UNIONing all of it. The counterparty columns are both
nullable with a CHECK that exactly the right one is set for the direction.

TWO NUMBERS PER BILL, which is how accounting systems do it. `numero` is always
ours - FA-YYYY-NNNN for what we issue, FF-YYYY-NNNN as an internal filing
reference for what we receive. `supplier_reference` is the supplier's own
number, stored exactly as printed. They never share a column: if they did,
every report and filter would mix their numbering with ours.

UNIQUE PER SUPPLIER, NOT GLOBALLY. uq_supplier_reference is
(supplier_id, supplier_reference). Globally unique would reject a second
supplier's "2026-001"; no uniqueness at all would let the same bill be entered
twice and paid twice. Scoped this way it is a real control against both
duplication and resubmission.

THE CHRONOLOGICAL RULE NOW APPLIES TO OUTGOING ONLY. Supplier bills arrive out
of date order by nature - one dated the 3rd is routinely booked after one dated
the 20th - so #39's rule would have rejected ordinary bookkeeping. Until now it
was scoped by matching the FA- pattern, which spared incoming invoices by
accident; it is scoped on `direction` here, which is what it always meant.

The gapless rule applies to BOTH, each in its own series. `invoice_sequences`
gains `series` as the other half of its key, because a shared counter would
interleave the two: FA-2026-0003 could be followed by FA-2026-0007 with the gap
taken by a purchase.

The accounting period keeps using `date_emission` for both directions, so a
supplier bill belongs to the month it was issued in, not the month it arrived.
Confirmed as the accrual and VAT treatment. The consequence is deliberate: a
bill arriving after its month has closed cannot be booked to it, so a month
should be closed only once its supplier bills are in.

Autogenerate detected the new table, columns and indexes but, as before, none of
the CHECK constraints, the client_id nullability change, the primary key change
on invoice_sequences, the triggers, or row-level security.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '60fef7016faf'
down_revision = '5524c45c0c4d'
branch_labels = None
depends_on = None

DIRECTION = postgresql.ENUM('OUTGOING', 'INCOMING', name='invoicedirection',
                            create_type=False)

ROLE = "nullif(current_setting('app.user_role', true), '')"

COUNTERPARTY = (
    "(direction = 'OUTGOING' AND client_id IS NOT NULL"
    " AND supplier_id IS NULL AND supplier_reference IS NULL)"
    " OR (direction = 'INCOMING' AND supplier_id IS NOT NULL"
    " AND client_id IS NULL AND supplier_reference IS NOT NULL)"
)

# Both series are policed for gaplessness; only the number's own series is
# consulted, so FA and FF never interfere with each other.
SEQUENTIAL = """
CREATE OR REPLACE FUNCTION trg_invoice_number_is_sequential() RETURNS trigger AS $BODY$
DECLARE
    series      text;
    series_year text;
    allocated   integer;
    highest     integer;
BEGIN
    IF NEW.numero !~ '^(FA|FF)-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;

    series      := substring(NEW.numero from 1 for 2);
    series_year := substring(NEW.numero from 4 for 4);
    allocated   := substring(NEW.numero from 9)::integer;

    SELECT coalesce(max(substring(numero from 9)::integer), 0) INTO highest
    FROM invoices
    WHERE numero ~ ('^' || series || '-' || series_year || '-[0-9]+$');

    IF allocated <> highest + 1 THEN
        RAISE EXCEPTION
            'invoice number % breaks the % series: % was expected',
            NEW.numero, series,
            series || '-' || series_year || '-' || lpad((highest + 1)::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
"""

# Outgoing only. A supplier's bills arrive out of date order, so applying this
# to incoming invoices would refuse ordinary bookkeeping.
CHRONOLOGICAL = """
CREATE OR REPLACE FUNCTION trg_invoice_number_follows_date() RETURNS trigger AS $BODY$
DECLARE
    series_year text;
    this_number integer;
    clash       record;
BEGIN
    IF NEW.direction <> 'OUTGOING' OR NEW.numero !~ '^FA-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;

    series_year := substring(NEW.numero from 4 for 4);
    this_number := substring(NEW.numero from 9)::integer;

    SELECT numero, date_emission INTO clash
    FROM invoices
    WHERE direction = 'OUTGOING'
      AND numero ~ '^FA-[0-9]{4}-[0-9]+$'
      AND substring(numero from 4 for 4) = series_year
      AND substring(numero from 9)::integer < this_number
      AND date_emission > NEW.date_emission
    ORDER BY date_emission DESC
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION
            'invoice % dated % would come before %, which is numbered lower '
            'but dated %. Invoice numbers must follow issue dates',
            NEW.numero, NEW.date_emission, clash.numero, clash.date_emission;
    END IF;

    SELECT numero, date_emission INTO clash
    FROM invoices
    WHERE direction = 'OUTGOING'
      AND numero ~ '^FA-[0-9]{4}-[0-9]+$'
      AND substring(numero from 4 for 4) = series_year
      AND substring(numero from 9)::integer > this_number
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
$BODY$ LANGUAGE plpgsql;
"""

# The pre-#40 bodies, restored on downgrade: they knew nothing about direction.
SEQUENTIAL_BEFORE_40 = """
CREATE OR REPLACE FUNCTION trg_invoice_number_is_sequential() RETURNS trigger AS $BODY$
DECLARE
    series_year text;
    allocated   integer;
    highest     integer;
BEGIN
    IF NEW.numero !~ '^FA-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;
    series_year := substring(NEW.numero from 4 for 4);
    allocated   := substring(NEW.numero from 9)::integer;
    SELECT coalesce(max(substring(numero from 9)::integer), 0) INTO highest
    FROM invoices
    WHERE numero ~ ('^FA-' || series_year || '-[0-9]+$');
    IF allocated <> highest + 1 THEN
        RAISE EXCEPTION 'invoice number % breaks the series: % was expected',
            NEW.numero,
            'FA-' || series_year || '-' || lpad((highest + 1)::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
"""

CHRONOLOGICAL_BEFORE_40 = """
CREATE OR REPLACE FUNCTION trg_invoice_number_follows_date() RETURNS trigger AS $BODY$
DECLARE
    series_year text;
    this_number integer;
    clash       record;
BEGIN
    IF NEW.numero !~ '^FA-[0-9]{4}-[0-9]+$' THEN
        RETURN NEW;
    END IF;
    series_year := substring(NEW.numero from 4 for 4);
    this_number := substring(NEW.numero from 9)::integer;
    SELECT numero, date_emission INTO clash FROM invoices
    WHERE numero ~ '^FA-[0-9]{4}-[0-9]+$'
      AND substring(numero from 4 for 4) = series_year
      AND substring(numero from 9)::integer < this_number
      AND date_emission > NEW.date_emission
    ORDER BY date_emission DESC LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION
            'invoice % dated % would come before %, which is numbered lower '
            'but dated %. Invoice numbers must follow issue dates',
            NEW.numero, NEW.date_emission, clash.numero, clash.date_emission;
    END IF;
    SELECT numero, date_emission INTO clash FROM invoices
    WHERE numero ~ '^FA-[0-9]{4}-[0-9]+$'
      AND substring(numero from 4 for 4) = series_year
      AND substring(numero from 9)::integer > this_number
      AND date_emission < NEW.date_emission
    ORDER BY date_emission ASC LIMIT 1;
    IF FOUND THEN
        RAISE EXCEPTION
            'invoice % dated % would come after %, which is numbered higher '
            'but dated %. Invoice numbers must follow issue dates',
            NEW.numero, NEW.date_emission, clash.numero, clash.date_emission;
    END IF;
    RETURN NEW;
END;
$BODY$ LANGUAGE plpgsql;
"""


def upgrade():
    # --- suppliers ----------------------------------------------------------
    op.create_table(
        'suppliers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nom', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('telephone', sa.String(length=30), nullable=True),
        sa.Column('adresse', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.execute("CREATE UNIQUE INDEX ux_suppliers_nom_ci ON suppliers (lower(nom))")

    op.execute("ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE suppliers FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY suppliers_owner_all ON suppliers
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    # The same shape as the clients policy: the roles that keep the books.
    op.execute(f"""
        CREATE POLICY suppliers_billing ON suppliers
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)

    # --- invoices: direction and the second counterparty --------------------
    DIRECTION.create(op.get_bind(), checkfirst=True)
    # Every existing invoice is one we issued, so OUTGOING is the right backfill.
    op.add_column('invoices', sa.Column('direction', DIRECTION,
                                        server_default='OUTGOING', nullable=False))
    op.add_column('invoices', sa.Column('supplier_id', sa.Integer(), nullable=True))
    op.add_column('invoices', sa.Column('supplier_reference', sa.String(length=60),
                                        nullable=True))
    op.create_foreign_key('invoices_supplier_id_fkey', 'invoices', 'suppliers',
                          ['supplier_id'], ['id'], ondelete='RESTRICT')
    # An incoming invoice has no client, so this can no longer be mandatory at
    # the column level. The CHECK below keeps it mandatory for outgoing ones.
    op.alter_column('invoices', 'client_id', existing_type=sa.Integer(),
                    nullable=True)
    op.create_check_constraint('ck_invoice_counterparty', 'invoices', COUNTERPARTY)
    op.create_unique_constraint('uq_supplier_reference', 'invoices',
                                ['supplier_id', 'supplier_reference'])
    op.create_index('ix_invoices_supplier_id', 'invoices', ['supplier_id'])
    op.create_index('ix_invoices_direction', 'invoices',
                    ['direction', 'date_emission'])

    # --- one counter per series, not per year alone -------------------------
    op.add_column('invoice_sequences',
                  sa.Column('series', sa.String(length=2), nullable=True))
    op.execute("UPDATE invoice_sequences SET series = 'FA' WHERE series IS NULL")
    op.alter_column('invoice_sequences', 'series', nullable=False)
    op.drop_constraint('invoice_sequences_pkey', 'invoice_sequences', type_='primary')
    op.create_primary_key('invoice_sequences_pkey', 'invoice_sequences',
                          ['series', 'year'])
    op.create_check_constraint('ck_invoice_sequence_series', 'invoice_sequences',
                               "series IN ('FA', 'FF')")

    # --- the series index now covers both prefixes --------------------------
    op.execute("DROP INDEX IF EXISTS ix_invoices_series")
    op.execute("""
        CREATE INDEX ix_invoices_series ON invoices
        ((substring(numero from 1 for 2)),
         (substring(numero from 4 for 4)),
         (substring(numero from 9)::integer))
        WHERE numero ~ '^(FA|FF)-[0-9]{4}-[0-9]+$'
    """)

    op.execute(SEQUENTIAL)
    op.execute(CHRONOLOGICAL)

    # --- a period's totals split by direction -------------------------------
    # One pair of totals now adds revenue to cost and means nothing. Split, the
    # same columns also give the VAT return: ttc - ht is VAT collected on the
    # outgoing side and VAT deductible on the incoming one.
    op.drop_constraint('ck_period_close_is_complete', 'accounting_periods',
                       type_='check')
    for column in ('total_ht_outgoing', 'total_ttc_outgoing',
                   'total_ht_incoming', 'total_ttc_incoming'):
        op.add_column('accounting_periods',
                      sa.Column(column, sa.Numeric(precision=12, scale=2),
                                nullable=True))
    # Everything closed so far was outgoing only, so its totals belong there.
    op.execute("""
        UPDATE accounting_periods
        SET total_ht_outgoing = total_ht, total_ttc_outgoing = total_ttc,
            total_ht_incoming = 0, total_ttc_incoming = 0
        WHERE state = 'CLOSED'
    """)
    op.drop_column('accounting_periods', 'total_ht')
    op.drop_column('accounting_periods', 'total_ttc')
    op.create_check_constraint(
        'ck_period_close_is_complete', 'accounting_periods',
        "(state = 'OPEN' AND closed_at IS NULL AND closed_by_id IS NULL"
        " AND invoice_count IS NULL AND total_ht_outgoing IS NULL"
        " AND total_ttc_outgoing IS NULL AND total_ht_incoming IS NULL"
        " AND total_ttc_incoming IS NULL)"
        " OR (state = 'CLOSED' AND closed_at IS NOT NULL AND closed_by_id IS NOT NULL"
        " AND invoice_count IS NOT NULL AND total_ht_outgoing IS NOT NULL"
        " AND total_ttc_outgoing IS NOT NULL AND total_ht_incoming IS NOT NULL"
        " AND total_ttc_incoming IS NOT NULL)",
    )


def downgrade():
    op.drop_constraint('ck_period_close_is_complete', 'accounting_periods',
                       type_='check')
    for column in ('total_ht', 'total_ttc'):
        op.add_column('accounting_periods',
                      sa.Column(column, sa.Numeric(precision=12, scale=2),
                                nullable=True))
    # Only the outgoing side survives: the pre-#40 schema had nowhere to put
    # expenses, which is the gap this revision filled.
    op.execute("""
        UPDATE accounting_periods
        SET total_ht = total_ht_outgoing, total_ttc = total_ttc_outgoing
        WHERE state = 'CLOSED'
    """)
    for column in ('total_ht_outgoing', 'total_ttc_outgoing',
                   'total_ht_incoming', 'total_ttc_incoming'):
        op.drop_column('accounting_periods', column)
    op.create_check_constraint(
        'ck_period_close_is_complete', 'accounting_periods',
        "(state = 'OPEN' AND closed_at IS NULL AND closed_by_id IS NULL"
        " AND invoice_count IS NULL AND total_ht IS NULL AND total_ttc IS NULL)"
        " OR (state = 'CLOSED' AND closed_at IS NOT NULL AND closed_by_id IS NOT NULL"
        " AND invoice_count IS NOT NULL AND total_ht IS NOT NULL"
        " AND total_ttc IS NOT NULL)",
    )

    op.execute(SEQUENTIAL_BEFORE_40)
    op.execute(CHRONOLOGICAL_BEFORE_40)

    op.execute("DROP INDEX IF EXISTS ix_invoices_series")
    op.execute("""
        CREATE INDEX ix_invoices_series ON invoices
        ((substring(numero from 4 for 4)), (substring(numero from 9)::integer))
        WHERE numero ~ '^FA-[0-9]{4}-[0-9]+$'
    """)

    op.drop_constraint('ck_invoice_sequence_series', 'invoice_sequences',
                       type_='check')
    op.drop_constraint('invoice_sequences_pkey', 'invoice_sequences', type_='primary')
    op.execute("DELETE FROM invoice_sequences WHERE series <> 'FA'")
    op.create_primary_key('invoice_sequences_pkey', 'invoice_sequences', ['year'])
    op.drop_column('invoice_sequences', 'series')

    op.drop_index('ix_invoices_direction', table_name='invoices')
    op.drop_index('ix_invoices_supplier_id', table_name='invoices')
    op.drop_constraint('uq_supplier_reference', 'invoices', type_='unique')
    op.drop_constraint('ck_invoice_counterparty', 'invoices', type_='check')
    # An incoming invoice has no client, so it cannot survive the column
    # becoming mandatory again. Deleting them needs the #38 guard stepped past.
    op.execute("ALTER TABLE invoices DISABLE TRIGGER invoice_is_never_deleted")
    op.execute("DELETE FROM invoices WHERE direction = 'INCOMING'")
    op.execute("ALTER TABLE invoices ENABLE TRIGGER invoice_is_never_deleted")
    op.alter_column('invoices', 'client_id', existing_type=sa.Integer(),
                    nullable=False)
    op.drop_constraint('invoices_supplier_id_fkey', 'invoices', type_='foreignkey')
    op.drop_column('invoices', 'supplier_reference')
    op.drop_column('invoices', 'supplier_id')
    op.drop_column('invoices', 'direction')
    DIRECTION.drop(op.get_bind(), checkfirst=True)

    op.drop_table('suppliers')
