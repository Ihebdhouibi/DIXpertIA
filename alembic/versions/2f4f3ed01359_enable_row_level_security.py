"""enable row level security

Revision ID: 2f4f3ed01359
Revises: 7f6f8270faad
Create Date: 2026-10-03 18:14:40.795686

"""
from alembic import op
import sqlalchemy as sa


revision = '2f4f3ed01359'
down_revision = '7f6f8270faad'
branch_labels = None
depends_on = None


# Tables placed under RLS, with the rule each one enforces for dixpertia_app.
#
# `users` is deliberately NOT included - see the issue comment. Login,
# forgot-password and reset-password all read `users` with no authenticated
# identity, so a policy there would break authentication outright. Closing that
# properly needs SECURITY DEFINER lookup functions, which is its own change.
PROTECTED = ("payslips", "leave_requests", "invoices", "invoice_items",
             "clients", "team_members", "devices")

# current_setting(..., true) yields NULL when never set, but '' once a
# transaction-local value has been set and the transaction has ended. Both mean
# "no identity", so every policy funnels through this and compares against NULL.
UID = "nullif(current_setting('app.user_id', true), '')"
ROLE = "nullif(current_setting('app.user_role', true), '')"


def upgrade() -> None:
    for table in PROTECTED:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        # FORCE so the table owner is subject too. Without it, dixpertia_owner
        # would bypass silently by virtue of ownership.
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

        # Maintenance path. Under FORCE, migrations and admin scripts would
        # otherwise be locked out of their own tables. Scoped to the owner role
        # by name rather than to a settable flag: a GUC-based escape hatch could
        # be flipped by dixpertia_app itself, which would defeat the policies.
        op.execute(f"""
            CREATE POLICY {table}_owner_all ON {table}
            FOR ALL TO dixpertia_owner
            USING (true) WITH CHECK (true)
        """)

    # --- payslips: an employee sees only their own ---------------------------
    op.execute(f"""
        CREATE POLICY payslips_read ON payslips
        FOR SELECT TO dixpertia_app
        USING (
            {ROLE} IN ('admin', 'accountant')
            OR ({ROLE} = 'employee' AND employee_id = {UID})
        )
    """)
    op.execute(f"""
        CREATE POLICY payslips_write ON payslips
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)

    # --- leave_requests: employee sees own, admin sees all -------------------
    # Accountants are excluded, matching the decision recorded on #10.
    op.execute(f"""
        CREATE POLICY leave_requests_read ON leave_requests
        FOR SELECT TO dixpertia_app
        USING (
            {ROLE} = 'admin'
            OR ({ROLE} = 'employee' AND employee_id = {UID})
        )
    """)
    op.execute(f"""
        CREATE POLICY leave_requests_write ON leave_requests
        FOR ALL TO dixpertia_app
        USING ({ROLE} = 'admin' OR ({ROLE} = 'employee' AND employee_id = {UID}))
        WITH CHECK ({ROLE} = 'admin' OR ({ROLE} = 'employee' AND employee_id = {UID}))
    """)

    # --- billing: admin and accountant only ----------------------------------
    for table in ("invoices", "invoice_items", "clients"):
        op.execute(f"""
            CREATE POLICY {table}_billing ON {table}
            FOR ALL TO dixpertia_app
            USING ({ROLE} IN ('admin', 'accountant'))
            WITH CHECK ({ROLE} IN ('admin', 'accountant'))
        """)

    # --- directory data: any authenticated caller ----------------------------
    # Read for everyone who is signed in; writes restricted to admin, matching
    # require_admin on POST /api/team-members.
    op.execute(f"""
        CREATE POLICY team_members_read ON team_members
        FOR SELECT TO dixpertia_app
        USING ({UID} IS NOT NULL)
    """)
    op.execute(f"""
        CREATE POLICY team_members_write ON team_members
        FOR ALL TO dixpertia_app
        USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)
    op.execute(f"""
        CREATE POLICY devices_read ON devices
        FOR SELECT TO dixpertia_app
        USING ({UID} IS NOT NULL)
    """)
    op.execute(f"""
        CREATE POLICY devices_write ON devices
        FOR ALL TO dixpertia_app
        USING ({ROLE} IN ('admin', 'accountant'))
        WITH CHECK ({ROLE} IN ('admin', 'accountant'))
    """)


def downgrade() -> None:
    for table in PROTECTED:
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_owner_all ON {table}")
    for policy, table in (
        ("payslips_read", "payslips"), ("payslips_write", "payslips"),
        ("leave_requests_read", "leave_requests"), ("leave_requests_write", "leave_requests"),
        ("invoices_billing", "invoices"), ("invoice_items_billing", "invoice_items"),
        ("clients_billing", "clients"),
        ("team_members_read", "team_members"), ("team_members_write", "team_members"),
        ("devices_read", "devices"), ("devices_write", "devices"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
