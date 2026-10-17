from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class AuditEvent(Base):
    """One sensitive action, recorded when it happens (#63).

    Append-only: the application role may insert and the admin may read, and a
    trigger refuses UPDATE and DELETE from anyone, owner included. Written by
    app.services.audit.record_event() inside the action's own transaction, so a
    rolled-back action leaves no event and a committed one always has one.

        actor_id     who did it; NULL for an anonymous step (password reset)
        actor_role   their role at the time, since a role can change later
        action       e.g. "invoice.approved", "leave_request.rejected"
        entity       e.g. "invoice"; entity_id is that row's id, as text
        before/after the fields the action changed, never secrets
    """

    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    # RESTRICT: an account that acted cannot be deleted from under its trail.
    actor_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    actor_role = Column(String(20), nullable=True)
    action = Column(String(60), nullable=False)
    entity = Column(String(40), nullable=False)
    entity_id = Column(String(60), nullable=False)
    before = Column(JSONB, nullable=True)
    after = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index("ix_audit_events_entity", "entity", "entity_id"),
        Index("ix_audit_events_actor", "actor_id", "occurred_at"),
    )
