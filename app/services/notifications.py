"""Writing notifications on workflow events (#116).

notify() adds the rows to the caller's session and does not commit: the
notification is part of the event's transaction, so an event that fails or
rolls back tells nobody, and one that commits always does.
"""

from typing import Iterable

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.models.notifications import Notification
from app.models.user import User

TONES = ("info", "success", "warning", "error")


def users_with_role(db: Session, role: str) -> list[str]:
    """Ids of the active accounts holding `role`, e.g. every accountant."""
    rows = db.query(User.id).filter(User.role == role, User.isActive.is_(True)).all()
    return [r[0] for r in rows]


def notify(
    db: Session,
    user_ids: Iterable[str],
    *,
    kind: str,
    message: str,
    tone: str = "info",
    link: str = "",
    ref_type: str | None = None,
    ref_id: int | None = None,
    exclude: str | None = None,
) -> int:
    """Queue one notification per recipient in the current transaction.

    `exclude` leaves out the person who acted: nobody needs telling about what
    they just did themselves. Returns how many were queued.
    """
    if tone not in TONES:
        raise ValueError(f"unknown notification tone {tone!r}")
    recipients = sorted({u for u in user_ids if u and u != exclude})
    if recipients:
        # A Core INSERT without RETURNING, not db.add(): the ORM reads the new
        # row back (RETURNING id), and PostgreSQL holds RETURNING to the SELECT
        # policy, under which the actor may not see a row addressed to someone
        # else. The admin's submit would fail on the accountant's notification.
        db.execute(insert(Notification.__table__).inline(), [
            {"user_id": user_id, "kind": kind, "message": message, "tone": tone,
             "link": link, "ref_type": ref_type, "ref_id": ref_id}
            for user_id in recipients
        ])
    return len(recipients)
