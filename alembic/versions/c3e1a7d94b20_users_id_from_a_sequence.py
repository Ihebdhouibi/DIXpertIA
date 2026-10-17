"""users.id from a sequence

Revision ID: c3e1a7d94b20
Revises: ba22aef318bc
Create Date: 2026-10-17 18:00:00.000000

#85: POST /api/users allocated the id from a row count, USR-{count + 1}. A
count is not a sequence: once ids are sparse (USR-001, USR-003) the count names
a live primary key and the insert fails with a UniqueViolation (500). Two
concurrent creations also read the same count and compute the same id.

The database now allocates the id. `users_id_seq` is set past the highest
USR-NNN already in the table, and `next_user_id()` formats its next value as the
column default. nextval() never hands the same number out twice, whatever the
concurrency, and never goes back, so a deleted user's id is not reused.

The id does not need to be gapless the way an invoice number does (#38): a
rolled-back insert leaves a hole, which is harmless here.

USR-NNN stays the primary key. Replacing it with an integer or UUID would touch
every foreign key to users, the token subject and the row-level security
policies that compare against it; that belongs with the schema rework of #60,
not with this fix.
"""
from alembic import op

revision = 'c3e1a7d94b20'
down_revision = 'ba22aef318bc'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE users_id_seq OWNED BY users.id")
    # Start after the highest numbered id, ignoring ids that are not USR-NNN
    # (fixture accounts such as TEST-ADMIN). On an empty table the first id is
    # USR-001.
    op.execute("""
        SELECT setval('users_id_seq',
                      coalesce(max(substring(id FROM '^USR-([0-9]+)$')::bigint), 0) + 1,
                      false)
        FROM users
    """)
    # A function rather than an inline expression because the value is needed
    # twice: lpad() alone truncates, so USR-1000 would come out as USR-100.
    op.execute("""
        CREATE FUNCTION next_user_id() RETURNS text
        LANGUAGE sql VOLATILE
        SET search_path = pg_catalog, public
        AS $$
            SELECT 'USR-' || CASE WHEN n < 1000 THEN lpad(n::text, 3, '0')
                                  ELSE n::text END
            FROM nextval('users_id_seq') AS n
        $$
    """)
    op.execute("ALTER TABLE users ALTER COLUMN id SET DEFAULT next_user_id()")
    # The app role normally receives this through the default privileges of
    # db/sql/001-roles-and-grants.sql, but only for objects dixpertia_owner
    # creates. A migration run as another role would leave it without one.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT USAGE, SELECT, UPDATE ON SEQUENCE users_id_seq TO dixpertia_app;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute("ALTER TABLE users ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP FUNCTION next_user_id()")
    op.execute("DROP SEQUENCE users_id_seq")
