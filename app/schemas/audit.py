from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    """One audit event as the admin reads it (#63). camelCase, like the rest of the API."""

    id: str
    occurredAt: datetime
    actorId: Optional[str] = None
    actorRole: Optional[str] = None
    action: str
    entity: str
    entityId: str
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None

    @classmethod
    def from_orm_row(cls, row) -> "AuditEventOut":
        return cls(
            id=str(row.id),
            occurredAt=row.occurred_at,
            actorId=row.actor_id,
            actorRole=row.actor_role,
            action=row.action,
            entity=row.entity,
            entityId=row.entity_id,
            before=row.before,
            after=row.after,
        )


class InvoiceHistoryEventOut(BaseModel):
    """One step in an invoice's life, as the details dialog shows it (#115).

    Read from the audit trail; `label` is the step in words, built by the
    server so the UI does not have to know the shape of each event.
    """

    id: str
    occurredAt: datetime
    action: str
    label: str
    actorName: str
    actorRole: Optional[str] = None
