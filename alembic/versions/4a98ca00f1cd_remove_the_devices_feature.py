"""remove the devices feature

Revision ID: 4a98ca00f1cd
Revises: 35237b3a0712
Create Date: 2026-10-04 15:56:24.291018

"""
from alembic import op
import sqlalchemy as sa


revision = '4a98ca00f1cd'
down_revision = '35237b3a0712'
branch_labels = None
depends_on = None


# DI Xpertia does not sell devices, parts or repairs. The table came from the
# original prototype and models a business the company is not in (#90).
#
# Nothing used it: #18 shipped only the backend, DevicesView.tsx was never
# merged, there was no Devices tab, and the "mark as Sold when invoiced" logic
# lived in the shadowed invoice handler removed in #59.
#
# Earlier revisions are left untouched - they are history. This drops what they
# built.


def upgrade() -> None:
    # Policies first: a table cannot be dropped while they reference it.
    for policy in ("devices_read", "devices_write", "devices_owner_all"):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON devices")
    op.execute("DROP INDEX IF EXISTS ux_devices_serial")
    op.drop_table("devices")


def downgrade() -> None:
    # Recreates the table as the baseline defined it, plus what #43, #58 and
    # #70 added, so a downgrade lands on the schema that existed before.
    op.create_table(
        "devices",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("serialNumber", sa.String(), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("createdAt", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("price >= 0", name="ck_devices_price"),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=False)
    op.execute(
        'CREATE UNIQUE INDEX ux_devices_serial ON devices ("serialNumber") '
        'WHERE "serialNumber" IS NOT NULL'
    )
    op.execute("ALTER TABLE devices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE devices FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY devices_owner_all ON devices "
        "FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)"
    )
    op.execute(
        "CREATE POLICY devices_read ON devices FOR SELECT TO dixpertia_app "
        "USING (nullif(current_setting('app.user_id', true), '') IS NOT NULL)"
    )
    op.execute(
        "CREATE POLICY devices_write ON devices FOR ALL TO dixpertia_app "
        "USING (nullif(current_setting('app.user_role', true), '') IN ('admin', 'accountant')) "
        "WITH CHECK (nullif(current_setting('app.user_role', true), '') IN ('admin', 'accountant'))"
    )
