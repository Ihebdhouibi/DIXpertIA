"""gapless per-year invoice numbering

Revision ID: b806d5baf7f7
Revises: afd22894a4a3
Create Date: 2026-10-05 14:35:17.644851



The accountant requires invoice numbers to start at 1 and increase by exactly 1
with no gaps and no duplicates (#38). The series restarts each year, keeping the
FA-YYYY-NNNN format already in use.

WHY A COUNTER TABLE AND NOT A SEQUENCE. A PostgreSQL sequence is deliberately
not gapless: it does not roll back when a transaction fails, precisely so that
concurrent writers never block. An invoice number is a legal artefact, so the
opposite trade-off is wanted. Allocation is an UPDATE ... RETURNING inside the
creating transaction, which holds a row lock until commit:

    two concurrent creates serialise, so neither can take the same number
    a failed create rolls the counter back with it, so no number is burned

Invoice creation therefore serialises on one row per year. That is deliberate:
a gapless counter and high write concurrency are in tension, and this company
issues a few invoices a day.

WHAT REPLACED WHAT. The old number came from COUNT(*) + 1, which broke three
ways: deleting an invoice made the next create collide with an existing number
and fail with a 500; two concurrent creates computed the same number; and a
failed transaction left a hole nobody detected.

TWO TRIGGERS GUARD THE SERIES.

`invoice_number_is_sequential` refuses an inserted number that is not exactly
one more than the highest already issued for its year. It applies only to
numbers matching FA-YYYY-NNNN: that is the legal series, and a fixture using
another prefix is not part of it. The API never lets a caller choose a number -
it is generated server-side - so the only writer this governs is a direct SQL
insert.

`invoice_is_never_deleted` refuses every delete, not only the archived ones #41
already protected. Deleting any invoice would leave a hole in the series, which
is the thing the accountant asked to be impossible. An invoice issued in error
is cancelled, keeping its row and its number with statut ANNULEE, and corrected
by a credit note. That supersedes the delete branch of the #41 trigger, which
is left in place: it names the closed month in its message, which is the more
useful error when it applies.

With no deletes and a transactional counter, a gap cannot occur. It is also
detectable: db/verify_constraints.py probes the rule, and the query that finds
one is in db/README.md.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b806d5baf7f7'
down_revision = 'afd22894a4a3'
branch_labels = None
depends_on = None


# Only numbers in this shape belong to the legal series. A fixture using
# another prefix is outside it, by design - see the docstring.
SERIES = r"^FA-[0-9]{4}-[0-9]+$"

ROLE = "nullif(current_setting('app.user_role', true), '')"

SEQUENTIAL = r"""
CREATE OR REPLACE FUNCTION trg_invoice_number_is_sequential() RETURNS trigger AS $$
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
        RAISE EXCEPTION
            'invoice number % breaks the series: % was expected',
            NEW.numero,
            'FA-' || series_year || '-' || lpad((highest + 1)::text, 4, '0');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

NEVER_DELETED = """
CREATE OR REPLACE FUNCTION trg_invoice_is_never_deleted() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION
        'invoice % cannot be deleted: its number is part of a gapless series. '
        'Cancel it instead (statut ANNULEE), which keeps the row and the number',
        OLD.numero;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    op.create_table(
        'invoice_sequences',
        sa.Column('year', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('last_number', sa.Integer(), server_default='0', nullable=False),
        sa.CheckConstraint('last_number >= 0', name='ck_invoice_sequence_not_negative'),
        sa.CheckConstraint('year BETWEEN 2000 AND 2999', name='ck_invoice_sequence_year'),
        sa.PrimaryKeyConstraint('year'),
    )

    # Row-level security, as every other table carries. Anyone signed in may
    # read the counter; only the roles that may create an invoice may move it.
    op.execute("ALTER TABLE invoice_sequences ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoice_sequences FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invoice_sequences_owner_all ON invoice_sequences
        FOR ALL TO dixpertia_owner
        USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY invoice_sequences_read ON invoice_sequences
        FOR SELECT TO dixpertia_app
        USING ({ROLE} IS NOT NULL)
    """)
    op.execute(f"""
        CREATE POLICY invoice_sequences_write ON invoice_sequences
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)

    # Seed a counter row per year already present, so an existing database
    # continues its series instead of restarting at 1 and colliding.
    op.execute("""
        INSERT INTO invoice_sequences (year, last_number)
        SELECT substring(numero from 4 for 4)::integer,
               max(substring(numero from 9)::integer)
        FROM invoices
        WHERE numero ~ '^FA-[0-9]{4}-[0-9]+$'
        GROUP BY substring(numero from 4 for 4)::integer
        ON CONFLICT (year) DO NOTHING
    """)

    op.execute(SEQUENTIAL)
    op.execute("""
        CREATE TRIGGER invoice_number_is_sequential
        BEFORE INSERT ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_number_is_sequential()
    """)
    op.execute(NEVER_DELETED)
    op.execute("""
        CREATE TRIGGER invoice_is_never_deleted
        BEFORE DELETE ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_is_never_deleted()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS invoice_is_never_deleted ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_is_never_deleted()")
    op.execute("DROP TRIGGER IF EXISTS invoice_number_is_sequential ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_number_is_sequential()")
    op.drop_table('invoice_sequences')
