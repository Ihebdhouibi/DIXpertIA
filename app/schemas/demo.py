"""Demo videos (#232): what the admin sends, and what the admin and the website read."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Service = Literal["cloud", "security", "software"]


def _text(limit: int):
    def check(value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("this field is required")
        if len(value) > limit:
            raise ValueError(f"at most {limit} characters")
        return value
    return check


def _link(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > 500:
        raise ValueError("at most 500 characters")
    return value


class DemoIn(BaseModel):
    """A new demo. The link is checked by the route, which answers in the caller's language."""

    title_fr: str
    title_en: str
    description_fr: str
    description_en: str
    video_url: str
    # Optional; "" means none.
    thumbnail_url: str | None = None
    service: Service | None = None
    published: bool = False

    _titles = field_validator("title_fr", "title_en")(_text(80))
    _descriptions = field_validator("description_fr", "description_en")(_text(300))
    _links = field_validator("video_url", "thumbnail_url")(_link)


class DemoUpdate(BaseModel):
    """A correction: only the fields sent change. thumbnail_url "" removes the image."""

    title_fr: str | None = None
    title_en: str | None = None
    description_fr: str | None = None
    description_en: str | None = None
    video_url: str | None = None
    thumbnail_url: str | None = None
    service: Service | None = None
    published: bool | None = None

    _titles = field_validator("title_fr", "title_en")(_text(80))
    _descriptions = field_validator("description_fr", "description_en")(_text(300))
    _links = field_validator("video_url", "thumbnail_url")(_link)


class DemoOrder(BaseModel):
    """The full order of the demos, first shown first: every demo, each once."""

    ids: list[int] = Field(min_length=1)


class DemoOut(BaseModel):
    """A demo as the admin manages it."""

    id: int
    title_fr: str
    title_en: str
    description_fr: str
    description_en: str
    video_url: str
    provider: str
    video_id: str
    thumbnail_url: str | None
    service: str | None
    position: int
    published: bool
    created_at: datetime
    updated_at: datetime
    # Built by the server from the provider and the video id.
    embed_url: str
    preview_image: str | None


class PublicDemoOut(BaseModel):
    """A published demo as the website shows it: both languages, so the FR/EN switch needs no reload."""

    id: int
    title_fr: str
    title_en: str
    description_fr: str
    description_en: str
    provider: str
    service: str | None
    embed_url: str
    # None when there is none to show (a Vimeo video without an image): the
    # website shows its branded fallback.
    preview_image: str | None
