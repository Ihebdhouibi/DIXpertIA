from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.contact import CONTACT_TOPICS

Topic = Literal["security_audit", "cloud_migration", "custom_development", "support_subscription", "other"]
assert set(Topic.__args__) == set(CONTACT_TOPICS)  # one list, checked at import


class ContactIn(BaseModel):
    """What the public contact form sends (#98).

    Strict on purpose: the endpoint is anonymous. The name goes into an
    e-mail subject, so it may not hold a line break (header injection), and
    every field has a length cap. `website` is a honeypot: hidden from people,
    filled in by bots, and an enquiry with it set is answered but not kept.
    """

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    topic: Topic
    message: str = Field(min_length=10, max_length=5000)
    website: str = Field(default="", max_length=200)

    @field_validator("name")
    @classmethod
    def one_line(cls, value: str) -> str:
        value = value.strip()
        if not value or any(c in value for c in "\r\n"):
            raise ValueError("the name must be one non-empty line")
        return value

    @field_validator("message")
    @classmethod
    def trimmed(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("the message must be at least 10 characters")
        return value


class ContactRequestOut(BaseModel):
    """An enquiry as the admin reads it."""

    id: str
    createdAt: datetime
    name: str
    email: str
    topic: str
    message: str
    handledAt: Optional[datetime] = None
    handledBy: Optional[str] = None

    @classmethod
    def from_row(cls, row, handled_by: str | None = None) -> "ContactRequestOut":
        return cls(id=str(row.id), createdAt=row.created_at, name=row.name, email=row.email,
                   topic=row.topic, message=row.message, handledAt=row.handled_at, handledBy=handled_by)
