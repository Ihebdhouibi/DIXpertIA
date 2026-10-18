"""account lifecycle: revocable sessions, single-use account tokens

Revision ID: e5f1c3a8b902
Revises: d4b8e2f61a73
Create Date: 2026-10-17 21:00:00.000000

#62 (AUDIT-DB-004, -005, -024).

- users.token_version: every access token carries the version it was issued
  under, and a request is refused once the account's version has moved on.
  Deactivation, a role change and a password change bump it, which revokes
  every session already issued. Before this a token stayed valid for its whole
  lifetime, whatever happened to the account.

- account_tokens replaces users.resetToken / resetTokenExpiry. The reset token
  was a JWT signed with the session key and stored in clear, so it worked as a
  session token and a database read handed it out. Reset and activation tokens
  are now opaque random strings; only their SHA-256 is stored, each is single
  use (used_at) and expires (1 h for a reset, 72 h for an activation). No
  DELETE is needed: a token is spent, never removed.

- Activation replaces the temporary password returned by POST /api/users: a
  new account cannot log in until its owner sets a password through the link.
  Accounts that exist already were created under the old flow and are in use,
  so they are marked verified here; isVerified only starts to mean something
  from now on.

Outstanding reset links stop working, which is acceptable: they expire within
the hour anyway, and nothing is deployed yet.
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f1c3a8b902'
down_revision = 'd4b8e2f61a73'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('token_version', sa.Integer(), server_default='0', nullable=False))
    op.execute('UPDATE users SET "isVerified" = true WHERE "isVerified" IS DISTINCT FROM true')
    op.alter_column('users', 'isVerified', existing_type=sa.Boolean(),
                    server_default=sa.text('false'), nullable=False)

    op.create_table(
        'account_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(length=20), nullable=False),
        # SHA-256 in hex. The token itself is never stored.
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_account_tokens_hash'),
        sa.CheckConstraint("purpose IN ('reset', 'activation')", name='ck_account_tokens_purpose'),
        sa.CheckConstraint("expires_at > created_at", name='ck_account_tokens_expiry'),
    )
    op.create_index('ix_account_tokens_user_live', 'account_tokens', ['user_id', 'purpose'],
                    postgresql_where=sa.text('used_at IS NULL'))

    op.drop_column('users', 'resetTokenExpiry')
    op.drop_column('users', 'resetToken')


def downgrade():
    op.add_column('users', sa.Column('resetToken', sa.String(), nullable=True))
    op.add_column('users', sa.Column('resetTokenExpiry', sa.DateTime(), nullable=True))
    op.drop_index('ix_account_tokens_user_live', table_name='account_tokens')
    op.drop_table('account_tokens')
    op.alter_column('users', 'isVerified', existing_type=sa.Boolean(), server_default=None, nullable=True)
    op.drop_column('users', 'token_version')
