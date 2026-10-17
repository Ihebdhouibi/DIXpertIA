"""Recording sensitive actions in the audit trail (#63).

record_event() adds the row to the caller's session and does not commit, like
notify(): the event is part of the action's transaction, so an action that
fails or rolls back records nothing, and one that commits is always recorded.

The actor is the signed-in identity of the request, never an argument. The
INSERT policy holds the same rule at the database (actor_id must be the
caller, or NULL when nobody is signed in), so code cannot record an action in
someone else's name.

Values in before/after are the fields the action changed. Never pass a
password, a hash, a token or a temporary password: the trail is kept for years
and read by people who must not see them.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.core.identity import get_identity
from app.models.audit import AuditEvent


def _jsonable(value: Any) -> Any:
    """Decimal, dates and enums as JSON: amounts as strings, so 12.30 stays exact."""
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def record_event(
    db: Session,
    action: str,
    entity: str,
    entity_id: Any,
    *,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Queue one audit event in the current transaction."""
    actor_id, actor_role = get_identity()
    # A Core INSERT without RETURNING, not db.add(): the ORM reads the new row
    # back, and PostgreSQL holds RETURNING to the SELECT policy, which only
    # lets the admin read the trail. An accountant's approval would fail on its
    # own audit event. Same reason as notify().
    db.execute(insert(AuditEvent.__table__).inline(), [{
        "actor_id": actor_id,
        "actor_role": actor_role,
        "action": action,
        "entity": entity,
        "entity_id": str(entity_id),
        "before": _jsonable(before) if before is not None else None,
        "after": _jsonable(after) if after is not None else None,
    }])
