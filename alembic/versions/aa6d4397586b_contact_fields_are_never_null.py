"""contact fields are never null

Revision ID: aa6d4397586b
Revises: 2a1cdf8dd27c
Create Date: 2026-10-12 18:30:00.000000

`email`, `telephone` and `adresse` on clients and suppliers had a default of
"" on the PYTHON side only (`Column(..., default="")`). SQLAlchemy applies that
on ORM inserts; anything else - raw SQL, a data migration, a CSV import,
insert_invoices.py - left the column NULL. The invoice PDF then crashed on the
first NULL address with "argument of type 'NoneType' is not iterable" (#86),
and every other reader of these fields had the same trap waiting.

The empty string already means "not given" everywhere in the app, so NULL
carried no extra meaning. Existing NULLs become '', the columns get a server
default of '' and become NOT NULL: a NULL can no longer be stored by any path.
"""
from alembic import op
import sqlalchemy as sa

revision = 'aa6d4397586b'
down_revision = '2a1cdf8dd27c'
branch_labels = None
depends_on = None

COLUMNS = (
    ('email', sa.String(length=100)),
    ('telephone', sa.String(length=30)),
    ('adresse', sa.Text()),
)
TABLES = ('clients', 'suppliers')


def upgrade():
    for table in TABLES:
        for column, type_ in COLUMNS:
            op.execute(f"UPDATE {table} SET {column} = '' WHERE {column} IS NULL")
            op.alter_column(table, column, existing_type=type_,
                            server_default=sa.text("''"), nullable=False)


def downgrade():
    for table in TABLES:
        for column, type_ in COLUMNS:
            op.alter_column(table, column, existing_type=type_,
                            server_default=None, nullable=True)
