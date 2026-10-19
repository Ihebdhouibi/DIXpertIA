"""accounting periods: totals by currency

Revision ID: bc66d5b01ae9
Revises: b26fef1399de
Create Date: 2026-10-18 22:00:00.000000

#195 brings invoices in EUR, USD and GBP. A month close records its totals
(#99), and adding dollars to dinars gives a figure that means nothing.

`totals_by_currency` records, at the close, one entry per currency the month
used: HT and TTC, outgoing and incoming, amounts as strings so they stay
exact. The existing total_* columns keep the TND part. No closed period holds
a foreign invoice yet, so nothing recorded so far changes meaning.

Nullable: an open period has no totals, and the periods closed before this
migration have none to backfill.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'bc66d5b01ae9'
down_revision = 'b26fef1399de'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('accounting_periods', sa.Column('totals_by_currency', postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column('accounting_periods', 'totals_by_currency')
