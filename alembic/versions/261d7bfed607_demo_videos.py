"""demo videos: managed by the admin, read anonymously through one function

Revision ID: 261d7bfed607
Revises: e9c3a1f7b204
Create Date: 2026-11-02 12:00:00.000000

#232 (part of #230): the admin publishes demo videos, shown in a Demo section
of the public website.

NO FILE IS STORED. A demo holds a link to a video hosted elsewhere (Google
Drive for now, YouTube or Vimeo later); the API recognises the link and keeps
its provider and video id, which are all the website needs to embed it.

ACCESS.
- The admin reads and writes demo_videos (demo_videos_managed_by_admin). No
  other role sees the table, not even published rows.
- The website's visitors are anonymous. As for the contact form (#98), they
  never touch the table: published_demos() is a SECURITY DEFINER function that
  returns the public fields of published demos, in display order. The
  application role may call it and nothing more anonymous; there is no SELECT
  policy for an anonymous caller, so a hidden demo or an internal column
  cannot leak through a careless query.
- DELETE is granted on this table, for existing databases here and in
  db/sql/001-roles-and-grants.sql for new ones. A demo is site content, not an
  accounting record; the audit trail keeps what was deleted.

Lengths follow the design brief: titles 1-80 characters, descriptions 1-300,
both in French and English.
"""
from alembic import op
import sqlalchemy as sa

revision = '261d7bfed607'
down_revision = 'e9c3a1f7b204'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"
PROVIDERS = ('drive', 'youtube', 'vimeo')
SERVICES = ('cloud', 'security', 'software')
FUNCTION = 'published_demos()'

PUBLISHED = """
CREATE FUNCTION published_demos()
RETURNS TABLE (
    id integer, title_fr varchar, title_en varchar, description_fr text, description_en text,
    provider varchar, video_id varchar, thumbnail_url text, service varchar, "position" integer)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT d.id, d.title_fr, d.title_en, d.description_fr, d.description_en,
           d.provider, d.video_id, d.thumbnail_url, d.service, d.position
      FROM public.demo_videos d
     WHERE d.published
     ORDER BY d.position, d.id
$$;
"""


def _in(values):
    return ", ".join(repr(v) for v in values)


def upgrade():
    op.create_table(
        'demo_videos',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title_fr', sa.String(length=80), nullable=False),
        sa.Column('title_en', sa.String(length=80), nullable=False),
        sa.Column('description_fr', sa.Text(), nullable=False),
        sa.Column('description_en', sa.Text(), nullable=False),
        sa.Column('video_url', sa.String(length=500), nullable=False),
        sa.Column('provider', sa.String(length=10), nullable=False),
        sa.Column('video_id', sa.String(length=100), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('service', sa.String(length=20), nullable=True),
        sa.Column('position', sa.Integer(), server_default='0', nullable=False),
        sa.Column('published', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_id', sa.String(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('updated_by_id', sa.String(), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.CheckConstraint("char_length(btrim(title_fr)) BETWEEN 1 AND 80", name='ck_demo_videos_title_fr'),
        sa.CheckConstraint("char_length(btrim(title_en)) BETWEEN 1 AND 80", name='ck_demo_videos_title_en'),
        sa.CheckConstraint("char_length(btrim(description_fr)) BETWEEN 1 AND 300",
                           name='ck_demo_videos_description_fr'),
        sa.CheckConstraint("char_length(btrim(description_en)) BETWEEN 1 AND 300",
                           name='ck_demo_videos_description_en'),
        sa.CheckConstraint(f"provider IN ({_in(PROVIDERS)})", name='ck_demo_videos_provider'),
        sa.CheckConstraint("video_id ~ '^[A-Za-z0-9_-]{1,100}$'", name='ck_demo_videos_video_id'),
        sa.CheckConstraint(f"service IS NULL OR service IN ({_in(SERVICES)})", name='ck_demo_videos_service'),
        sa.CheckConstraint("position >= 0", name='ck_demo_videos_position'),
        sa.CheckConstraint("video_url LIKE 'https://%'", name='ck_demo_videos_video_url_https'),
        sa.CheckConstraint("thumbnail_url IS NULL OR thumbnail_url LIKE 'https://%'",
                           name='ck_demo_videos_thumbnail_url_https'),
    )
    op.create_index('ix_demo_videos_published_position', 'demo_videos', ['published', 'position'])

    op.execute("ALTER TABLE demo_videos ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE demo_videos FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY demo_videos_owner_all ON demo_videos
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY demo_videos_managed_by_admin ON demo_videos
        FOR ALL TO dixpertia_app USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)

    op.execute(PUBLISHED)
    op.execute(f"REVOKE ALL ON FUNCTION {FUNCTION} FROM PUBLIC")
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT EXECUTE ON FUNCTION {FUNCTION} TO dixpertia_app;
                GRANT DELETE ON TABLE demo_videos TO dixpertia_app;
            END IF;
        END
        $$;
    """)


def downgrade():
    op.execute(f"DROP FUNCTION IF EXISTS {FUNCTION}")
    op.drop_index('ix_demo_videos_published_position', table_name='demo_videos')
    op.drop_table('demo_videos')
