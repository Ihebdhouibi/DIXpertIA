from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Notification(Base):
    """One message for one user, written by the server on an event (#116).

    Replaces notifications made in the browser, which lived only in the
    session. Row-level security lets a user read, mark and dismiss only their
    own; any signed-in role may write one for someone else, because the person
    acting is rarely the one to be told. See the migration for the policies.

        kind          the event, e.g. "invoice_submitted"
        tone          how the UI shows it: info, success, warning, error
        link          the screen to open, e.g. "invoices"
        ref_type/id   the record it is about, e.g. ("invoice", 26)
        read_at       when the user read it; NULL while unread
        dismissed_at  when the user cleared it from the list (soft: no DELETE)
    """

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(40), nullable=False)
    tone = Column(String(10), nullable=False, default="info", server_default="info")
    message = Column(Text, nullable=False)
    link = Column(String(40), nullable=False, default="", server_default="")
    ref_type = Column(String(30), nullable=True)
    ref_id = Column(Integer, nullable=True)
    # The facts the text is made of (#135), so it is rendered in the reader's
    # language when read. NULL on rows written before: `message` is shown then.
    params = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    read_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("tone IN ('info', 'success', 'warning', 'error')", name="ck_notifications_tone"),
        Index("ix_notifications_user_live", "user_id", "created_at",
              postgresql_where=text("dismissed_at IS NULL")),
    )
