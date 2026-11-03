"""demo previews: served from our own domain

Revision ID: 9d098021263d
Revises: 261d7bfed607
Create Date: 2026-11-03 12:00:00.000000

#232, decided with the design (#231): the website must not contact Google,
YouTube or Vimeo before a visitor presses Play. A preview image linked
directly from those hosts would be requested as soon as the page loads.

So the server fetches each demo's preview once, when the demo is saved,
re-encodes it as a JPEG (at most 1280 x 720, about 100-200 KB) and keeps it
here. The website reads it from our domain.

ACCESS, as for the demos themselves:
- demo_previews is the admin's only (demo_previews_managed_by_admin): the
  admin screen shows previews of hidden demos too.
- Visitors read through published_demo_preview(id), a SECURITY DEFINER
  function that returns the image of a PUBLISHED demo only.
- published_demos() now also returns preview_version, the time the preview
  was fetched, so the website can cache an image for a long time and still
  get the new one after a change. It is dropped and recreated, since its
  return type changes.

A demo's preview row goes with it (ON DELETE CASCADE). A preview that could
not be fetched is simply absent: the website shows its branded fallback.
DELETE is granted, as on demo_videos: when a demo's link changes and its new
preview cannot be fetched, the old image must go rather than show the wrong
video.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '9d098021263d'
down_revision = '261d7bfed607'
branch_labels = None
depends_on = None

ROLE = "nullif(current_setting('app.user_role', true), '')"

PUBLISHED_V2 = """
CREATE FUNCTION published_demos()
RETURNS TABLE (
    id integer, title_fr varchar, title_en varchar, description_fr text, description_en text,
    provider varchar, video_id varchar, thumbnail_url text, service varchar, "position" integer,
    preview_version bigint)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT d.id, d.title_fr, d.title_en, d.description_fr, d.description_en,
           d.provider, d.video_id, d.thumbnail_url, d.service, d.position,
           extract(epoch FROM p.fetched_at)::bigint
      FROM public.demo_videos d
      LEFT JOIN public.demo_previews p ON p.demo_id = d.id
     WHERE d.published
     ORDER BY d.position, d.id
$$;
"""

PUBLISHED_V1 = """
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

PREVIEW = """
CREATE FUNCTION published_demo_preview(p_demo_id integer)
RETURNS TABLE (content bytea, content_type varchar, fetched_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT p.content, p.content_type, p.fetched_at
      FROM public.demo_previews p
      JOIN public.demo_videos d ON d.id = p.demo_id
     WHERE p.demo_id = p_demo_id AND d.published
$$;
"""


def _grant(function):
    op.execute(f"REVOKE ALL ON FUNCTION {function} FROM PUBLIC")
    op.execute(f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT EXECUTE ON FUNCTION {function} TO dixpertia_app;
            END IF;
        END
        $$;
    """)


def upgrade():
    op.create_table(
        'demo_previews',
        sa.Column('demo_id', sa.Integer(), sa.ForeignKey('demo_videos.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('content', postgresql.BYTEA(), nullable=False),
        sa.Column('content_type', sa.String(length=40), nullable=False),
        sa.Column('source_url', sa.String(length=500), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        # The server re-encodes every preview to JPEG, at most 1280 x 720.
        sa.CheckConstraint("content_type = 'image/jpeg'", name='ck_demo_previews_content_type'),
        sa.CheckConstraint("octet_length(content) BETWEEN 1 AND 2000000", name='ck_demo_previews_size'),
    )
    op.execute("ALTER TABLE demo_previews ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE demo_previews FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY demo_previews_owner_all ON demo_previews
        FOR ALL TO dixpertia_owner USING (true) WITH CHECK (true)
    """)
    op.execute(f"""
        CREATE POLICY demo_previews_managed_by_admin ON demo_previews
        FOR ALL TO dixpertia_app USING ({ROLE} = 'admin') WITH CHECK ({ROLE} = 'admin')
    """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dixpertia_app') THEN
                GRANT DELETE ON TABLE demo_previews TO dixpertia_app;
            END IF;
        END
        $$;
    """)

    op.execute("DROP FUNCTION published_demos()")
    op.execute(PUBLISHED_V2)
    _grant("published_demos()")
    op.execute(PREVIEW)
    _grant("published_demo_preview(integer)")


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS published_demo_preview(integer)")
    op.execute("DROP FUNCTION published_demos()")
    op.execute(PUBLISHED_V1)
    _grant("published_demos()")
    op.drop_table('demo_previews')
