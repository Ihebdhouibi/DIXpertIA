"""demo videos: their own rate-limit bucket

Revision ID: c5e8a2d4f716
Revises: 9d098021263d
Create Date: 2026-11-17 12:00:00.000000

#246: the website's demo routes (the list and the preview images, #232) used
the same per-address limit as sign-in, activation, password reset, two-factor
and the contact form. A few visitors behind one address browsing the demos
could use it up, and then sign-in and the contact form answered 429 to that
whole office for up to a minute.

The demo routes now count in their own bucket, `public_demo_ip`, with their
own setting (PUBLIC_DEMO_REQUESTS_PER_MINUTE). auth_attempts accepts only the
buckets its check lists, so the check is widened, as #44 did for
`mfa_account`. Nothing else changes: same table, same functions, same grants.

The downgrade drops this bucket's rows first, since the narrower check would
refuse them.
"""
from alembic import op

revision = 'c5e8a2d4f716'
down_revision = '9d098021263d'
branch_labels = None
depends_on = None

BUCKETS_BEFORE = ('login_account', 'login_ip', 'reset_mail', 'public_ip', 'mfa_account')
BUCKETS_AFTER = BUCKETS_BEFORE + ('public_demo_ip',)


def _bucket_check(buckets):
    op.drop_constraint('ck_auth_attempts_bucket', 'auth_attempts', type_='check')
    op.create_check_constraint('ck_auth_attempts_bucket', 'auth_attempts',
                               f"bucket IN ({', '.join(repr(b) for b in buckets)})")


def upgrade():
    _bucket_check(BUCKETS_AFTER)


def downgrade():
    op.execute("DELETE FROM auth_attempts WHERE bucket = 'public_demo_ip'")
    _bucket_check(BUCKETS_BEFORE)
