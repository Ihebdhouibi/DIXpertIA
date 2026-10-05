"""monthly accounting period with an irreversible close

Revision ID: afd22894a4a3
Revises: 6cafb780b3ed
Create Date: 2026-10-05 10:21:14.882190

The accountant works the books a month at a time (#42). This adds the period
itself, the row-level security that every other table already carries, and the
rule that gives a close its meaning.

A table rather than a month derived from date_emission, because closing is an
event and not a property of the invoices: it has an actor, a moment and a
result. Deriving the month would record none of those.

THE RULE WITH TEETH: once a period is closed, no invoice may be created or
moved into it. Without that, closing changes nothing - an invoice dated into
January could still appear after January was reported as final, and the closing
totals recorded on the period row would quietly stop matching the invoices they
counted. Enforced by a trigger, not in the API, because migrate_data.py and
insert_invoices.py write to this database directly.

Closing is irreversible, following the decision on #41 that an archived invoice
is terminal. A reopen could not un-archive the invoices anyway - the #41 trigger
refuses that - so a period that reopened would be able to gain new invoices
while its existing ones stayed frozen, and its recorded totals would be wrong
either way. There is deliberately no reopen path.

Grants are not repeated here: db/sql/001-roles-and-grants.sql sets default
privileges for tables the owner creates, so dixpertia_app receives SELECT,
INSERT and UPDATE on this table automatically. Row-level security is NOT
automatic and is set up below.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'afd22894a4a3'
down_revision = '6cafb780b3ed'
branch_labels = None
depends_on = None

# create_type=False matters: sa.Enum inside a create_table emits its own
# CREATE TYPE, which collides with the explicit create below and fails the
# migration with "type periodstate already exists". Creating it once,
# explicitly, is also what lets downgrade drop it.
PERIOD_STATE = postgresql.ENUM('OPEN', 'CLOSED', name='periodstate',
                               create_type=False)

# Same funnel as 2f4f3ed01359: current_setting(..., true) gives NULL when never
# set but '' after a transaction-local value has gone out of scope, and both
# mean "no identity".
ROLE = "nullif(current_setting('app.user_role', true), '')"

CLOSED_PERIOD_IS_SEALED = """
CREATE OR REPLACE FUNCTION trg_invoice_period_is_open() RETURNS trigger AS $$
DECLARE
    period_state text;
BEGIN
    SELECT state INTO period_state
    FROM accounting_periods
    WHERE periode = date_trunc('month', NEW.date_emission)::date;

    IF period_state = 'CLOSED' THEN
        RAISE EXCEPTION
            'the accounting period % is closed; an invoice cannot be dated '
            'into it. Issue it in the open month instead',
            to_char(NEW.date_emission, 'YYYY-MM');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    PERIOD_STATE.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'accounting_periods',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('periode', sa.Date(), nullable=False),
        sa.Column('state', PERIOD_STATE, server_default='OPEN', nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_id', sa.String(), nullable=True),
        sa.Column('invoice_count', sa.Integer(), nullable=True),
        sa.Column('total_ht', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('total_ttc', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.CheckConstraint('extract(day FROM periode) = 1',
                           name='ck_period_is_month_start'),
        sa.CheckConstraint(
            "(state = 'OPEN' AND closed_at IS NULL AND closed_by_id IS NULL"
            " AND invoice_count IS NULL AND total_ht IS NULL AND total_ttc IS NULL)"
            " OR (state = 'CLOSED' AND closed_at IS NOT NULL AND closed_by_id IS NOT NULL"
            " AND invoice_count IS NOT NULL AND total_ht IS NOT NULL"
            " AND total_ttc IS NOT NULL)",
            name='ck_period_close_is_complete'),
        sa.ForeignKeyConstraint(['closed_by_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('periode'),
    )
    # Not for reads: closed_by_id is ON DELETE RESTRICT, so deleting a user who
    # has closed nothing would otherwise scan the whole table to prove it (#61).
    op.create_index('ix_accounting_periods_closed_by_id', 'accounting_periods',
                    ['closed_by_id'], unique=False)

    # --- row-level security, matching every other table ---------------------
    op.execute("ALTER TABLE accounting_periods ENABLE ROW LEVEL SECURITY")
    # FORCE so the owner is subject too, as in 2f4f3ed01359.
    op.execute("ALTER TABLE accounting_periods FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY accounting_periods_owner_all ON accounting_periods
        FOR ALL TO dixpertia_owner
        USING (true) WITH CHECK (true)
    """)
    # Everyone signed in may see which months are open: an employee filing an
    # expense has a legitimate reason to know. Only the two roles that keep the
    # books may write, matching who may move an invoice's processing status.
    op.execute(f"""
        CREATE POLICY accounting_periods_read ON accounting_periods
        FOR SELECT TO dixpertia_app
        USING ({ROLE} IS NOT NULL)
    """)
    op.execute(f"""
        CREATE POLICY accounting_periods_write ON accounting_periods
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)

    # --- a closed month admits no further invoices --------------------------
    op.execute(CLOSED_PERIOD_IS_SEALED)
    op.execute("""
        CREATE TRIGGER invoice_period_is_open
        BEFORE INSERT OR UPDATE OF date_emission ON invoices
        FOR EACH ROW EXECUTE FUNCTION trg_invoice_period_is_open()
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS invoice_period_is_open ON invoices")
    op.execute("DROP FUNCTION IF EXISTS trg_invoice_period_is_open()")
    op.drop_index('ix_accounting_periods_closed_by_id',
                  table_name='accounting_periods')
    op.drop_table('accounting_periods')
    # Dropping the table does not drop the type it used.
    PERIOD_STATE.drop(op.get_bind(), checkfirst=True)
