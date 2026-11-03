"""Demo videos shown on the public website (#230, #232).

No file is stored: a demo holds a link to a video hosted on Google Drive,
YouTube or Vimeo, and the provider and video id recognised in it. The admin
manages demos; visitors read the published ones through published_demos(),
a SECURITY DEFINER function (migration 261d7bfed607).
"""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import BYTEA

from app.core.database import Base

#: Where a demo's video can be hosted; mirrors ck_demo_videos_provider.
PROVIDERS = ("drive", "youtube", "vimeo")
#: The services a demo can belong to; mirrors ck_demo_videos_service.
SERVICES = ("cloud", "security", "software")


class DemoVideo(Base):
    __tablename__ = "demo_videos"

    id = Column(Integer, primary_key=True)
    title_fr = Column(String(80), nullable=False)
    title_en = Column(String(80), nullable=False)
    description_fr = Column(Text, nullable=False)
    description_en = Column(Text, nullable=False)
    # As the admin pasted it, and what was recognised in it.
    video_url = Column(String(500), nullable=False)
    provider = Column(String(10), nullable=False)
    video_id = Column(String(100), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    service = Column(String(20), nullable=True)
    position = Column(Integer, nullable=False, default=0, server_default=text("0"))
    published = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    created_by_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    updated_by_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        CheckConstraint("char_length(btrim(title_fr)) BETWEEN 1 AND 80", name="ck_demo_videos_title_fr"),
        CheckConstraint("char_length(btrim(title_en)) BETWEEN 1 AND 80", name="ck_demo_videos_title_en"),
        CheckConstraint("char_length(btrim(description_fr)) BETWEEN 1 AND 300", name="ck_demo_videos_description_fr"),
        CheckConstraint("char_length(btrim(description_en)) BETWEEN 1 AND 300", name="ck_demo_videos_description_en"),
        CheckConstraint("provider IN ('drive', 'youtube', 'vimeo')", name="ck_demo_videos_provider"),
        CheckConstraint("video_id ~ '^[A-Za-z0-9_-]{1,100}$'", name="ck_demo_videos_video_id"),
        CheckConstraint("service IS NULL OR service IN ('cloud', 'security', 'software')",
                        name="ck_demo_videos_service"),
        CheckConstraint("position >= 0", name="ck_demo_videos_position"),
        CheckConstraint("video_url LIKE 'https://%'", name="ck_demo_videos_video_url_https"),
        CheckConstraint("thumbnail_url IS NULL OR thumbnail_url LIKE 'https://%'",
                        name="ck_demo_videos_thumbnail_url_https"),
        Index("ix_demo_videos_published_position", "published", "position"),
    )


class DemoPreview(Base):
    """A demo's preview image, fetched once by the server and served from our domain (#232).

    JPEG, at most 1280 x 720. Visitors read it through published_demo_preview()
    (migration 9d098021263d); the admin reads it directly.
    """

    __tablename__ = "demo_previews"

    demo_id = Column(Integer, ForeignKey("demo_videos.id", ondelete="CASCADE"), primary_key=True)
    content = Column(BYTEA, nullable=False)
    content_type = Column(String(40), nullable=False)
    source_url = Column(String(500), nullable=False)
    fetched_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        CheckConstraint("content_type = 'image/jpeg'", name="ck_demo_previews_content_type"),
        CheckConstraint("octet_length(content) BETWEEN 1 AND 2000000", name="ck_demo_previews_size"),
    )
