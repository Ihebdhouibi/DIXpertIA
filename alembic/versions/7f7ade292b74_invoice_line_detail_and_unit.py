"""invoice lines: an optional detail and unit

Revision ID: 7f7ade292b74
Revises: b3d7f1a9c2e5
Create Date: 2026-10-18 18:00:00.000000

#194: the new invoice layout prints, for each line, a description under the
designation and the unit under the quantity ("days", "flat fee"). A line had
only a 255-character designation, so neither had anywhere to live.

Both columns are nullable: existing lines are left as they are and print as
before. The detail is capped at 1000 characters, as the API is (#58: the API
answers 422 with the field name instead of the database raising a 500). The
unit is a varchar(30), which caps it by itself.

No grant or policy changes: the columns belong to invoice_items, whose
policies and the invoice_lines_follow_their_invoice trigger (#125) already
cover every column - a line of an approved invoice cannot change, detail and
unit included.
"""
from alembic import op
import sqlalchemy as sa

revision = '7f7ade292b74'
down_revision = 'b3d7f1a9c2e5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('invoice_items', sa.Column('detail', sa.Text(), nullable=True))
    op.add_column('invoice_items', sa.Column('unite', sa.String(30), nullable=True))
    op.create_check_constraint('ck_invoice_items_detail', 'invoice_items', 'char_length(detail) <= 1000')


def downgrade():
    op.drop_constraint('ck_invoice_items_detail', 'invoice_items', type_='check')
    op.drop_column('invoice_items', 'unite')
    op.drop_column('invoice_items', 'detail')
