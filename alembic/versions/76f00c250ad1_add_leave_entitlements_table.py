"""add leave_entitlements table

Revision ID: 76f00c250ad1
Revises: c5e8a2d4f716
Create Date: 2026-11-19 08:32:35.902953

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '76f00c250ad1'
down_revision = 'c5e8a2d4f716'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'leave_entitlements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('type_conge', postgresql.ENUM('PAYE', 'MALADIE', 'SANS_SOLDE', name='leavetype', create_type=False), nullable=False),
        sa.Column('days', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'year', 'type_conge', name='uq_employee_year_type')
    )
    op.create_index('ix_leave_entitlements_employee_id', 'leave_entitlements', ['employee_id'], unique=False)

    op.execute("ALTER TABLE leave_entitlements ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY leave_entitlements_owner_all ON leave_entitlements
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute("""
        CREATE POLICY leave_entitlements_app_select ON leave_entitlements
        FOR SELECT TO dixpertia_app
        USING (
            employee_id = (SELECT id FROM employees WHERE user_id = current_setting('app.user_id', true))
            OR current_setting('app.role', true) IN ('admin', 'accountant')
        )
    """)

def downgrade():
    op.execute("DROP POLICY IF EXISTS leave_entitlements_app_select ON leave_entitlements")
    op.execute("DROP POLICY IF EXISTS leave_entitlements_owner_all ON leave_entitlements")
    op.drop_index('ix_leave_entitlements_employee_id', table_name='leave_entitlements')
    op.drop_table('leave_entitlements')
