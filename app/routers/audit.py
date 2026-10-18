"""Reading the audit trail (#63). Admin only.

Nothing here writes: events are recorded by the server through
app.services.audit.record_event(), in the transaction of the action itself.
Row-level security holds the admin-only rule underneath, so the trail stays
closed even to a query that forgets the dependency.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.audit import AuditEvent
from app.schemas.audit import AuditEventOut

router = APIRouter(dependencies=[Depends(require_roles("admin"))])

MAX_PAGE_SIZE = 200


@router.get("/audit-events", response_model=list[AuditEventOut])
def list_audit_events(
    response: Response,
    db: Session = Depends(get_db),
    actor_id: Optional[str] = Query(None, alias="actorId"),
    entity: Optional[str] = None,
    entity_id: Optional[str] = Query(None, alias="entityId"),
    action: Optional[str] = None,
    since: Optional[date] = Query(None, description="first day included, YYYY-MM-DD"),
    until: Optional[date] = Query(None, description="last day included, YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Newest first. X-Total-Count is the number of events matching the filters."""
    query = db.query(AuditEvent)
    if actor_id:
        query = query.filter(AuditEvent.actor_id == actor_id)
    if entity:
        query = query.filter(AuditEvent.entity == entity)
    if entity_id:
        query = query.filter(AuditEvent.entity_id == entity_id)
    if action:
        query = query.filter(AuditEvent.action == action)
    if since:
        query = query.filter(AuditEvent.occurred_at >= since)
    if until:
        # Inclusive of the whole last day.
        query = query.filter(AuditEvent.occurred_at < until + timedelta(days=1))
    response.headers["X-Total-Count"] = str(query.count())
    rows = (
        query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [AuditEventOut.from_orm_row(e) for e in rows]
