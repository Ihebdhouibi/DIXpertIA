"""leave entitlements: the paid leave an employee has for a year

Revision ID: 76f00c250ad1
Revises: c5e8a2d4f716
Create Date: 2026-11-19 08:32:35.902953

#121: real leave balances. A balance is the year's entitlement minus the
approved days, with the pending days shown apart.

LEAVE_ENTITLEMENTS holds one figure per employee, year and leave type. Only
paid leave (`paye`) has one: sick and unpaid leave are counted, not capped.
- The row of a year is created from the employee's `annual_entitlement_days`
  the first time that year's balance is read, then it is fixed: changing
  `annual_entitlement_days` later applies to the years still to come, never
  to one already recorded.
- An admin corrects a year (carry-over, arrival during the year) by editing
  its row. Accrual, carry-over and proration rules are #254.
- `ck_leave_entitlements_paid_only`: only `paye` has an entitlement.
- `ck_leave_entitlements_days`: between 0 and 365, as `annual_entitlement_days`.
- RESTRICT on the employee, like `leave_requests`: leave history outlives an
  attempt to delete the person.

Row-level security, forced like every other table:
- an admin reads and writes every row;
- anyone reads the rows of their own employee record;
- anyone may create the missing row of their own year, and only with the
  value of their `annual_entitlement_days`: an employee cannot give themselves
  more days. The row is created by GET /api/leaves/balances on their behalf.

No grant change: the default privileges of 001-roles-and-grants.sql give the
app role SELECT, INSERT and UPDATE on every new table, and no DELETE.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '76f00c250ad1'
down_revision = 'c5e8a2d4f716'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"
OWN_EMPLOYEE = """employee_id IN (
                SELECT id FROM employees
                WHERE user_id = nullif(current_setting('app.user_id', true), '')
            )"""


def upgrade():
    op.create_table(
        'leave_entitlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('type_conge', postgresql.ENUM('PAYE', 'MALADIE', 'SANS_SOLDE', name='leavetype',
                                                create_type=False), nullable=False),
        sa.Column('days', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'year', 'type_conge', name='uq_employee_year_type'),
        sa.CheckConstraint("type_conge = 'PAYE'", name='ck_leave_entitlements_paid_only'),
        sa.CheckConstraint('days >= 0 AND days <= 365', name='ck_leave_entitlements_days'),
    )
    op.create_index('ix_leave_entitlements_employee_id', 'leave_entitlements', ['employee_id'], unique=False)

    op.execute("ALTER TABLE leave_entitlements ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE leave_entitlements FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY leave_entitlements_owner_all ON leave_entitlements
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY leave_entitlements_read ON leave_entitlements
        FOR SELECT TO dixpertia_app
        USING ({ROLE} = 'admin' OR {OWN_EMPLOYEE})
    """)
    op.execute(f"""
        CREATE POLICY leave_entitlements_admin_write ON leave_entitlements
        FOR ALL TO dixpertia_app
        USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)
    op.execute(f"""
        CREATE POLICY leave_entitlements_create_own_year ON leave_entitlements
        FOR INSERT TO dixpertia_app
        WITH CHECK (
            {OWN_EMPLOYEE}
            AND days = (SELECT annual_entitlement_days FROM employees e WHERE e.id = employee_id)
        )
    """)


def downgrade():
    op.drop_index('ix_leave_entitlements_employee_id', table_name='leave_entitlements')
    # Dropping the table drops its policies.
    op.drop_table('leave_entitlements')
