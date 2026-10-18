from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, text

from app.core.database import Base

#: The subjects a visitor may pick on the contact form (#98). The database
#: holds the same set as a CHECK (ck_contact_requests_topic).
CONTACT_TOPICS = ("security_audit", "cloud_migration", "custom_development", "support_subscription", "other")


class ContactRequest(Base):
    """An enquiry sent from the public contact form (#98).

    Written only by submit_contact_request(), a SECURITY DEFINER function,
    because the sender is anonymous; read and marked handled by the admin.
    `sender_hash` is an HMAC of the sender's IP, never the IP itself: enough
    to count one sender's messages for the rate limit.
    """

    __tablename__ = "contact_requests"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    name = Column(String(120), nullable=False)
    email = Column(String(254), nullable=False)
    topic = Column(String(40), nullable=False)
    message = Column(Text, nullable=False)
    sender_hash = Column(String(64), nullable=False)
    handled_at = Column(DateTime(timezone=True), nullable=True)
    handled_by_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    __table_args__ = (
        # The rate limit counts one sender's recent messages, then everyone's.
        Index("ix_contact_requests_sender", "sender_hash", "created_at"),
        Index("ix_contact_requests_created_at", "created_at"),
    )
