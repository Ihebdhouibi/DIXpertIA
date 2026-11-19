"""add leave_entitlements table

Revision ID: 76f00c250ad1
Revises: e9c3a1f7b204
Create Date: 2026-11-19 08:32:35.902953

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '76f00c250ad1'
down_revision = 'e9c3a1f7b204'
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
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', 'year', 'type_conge', name='uq_employee_year_type')
    )
    op.create_index('ix_leave_entitlements_employee_id', 'leave_entitlements', ['employee_id'], unique=False)


def downgrade():
    op.drop_index('ix_leave_entitlements_employee_id', table_name='leave_entitlements')
    op.drop_table('leave_entitlements')
