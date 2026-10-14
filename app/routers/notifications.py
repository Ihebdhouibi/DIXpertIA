"""A user's own notifications (#116).

Every route acts on the caller's notifications only. The filter on user_id
says so in the query, and row-level security holds it underneath: a
notification of someone else is not found, rather than forbidden, which also
avoids revealing that it exists.

Writing notifications is not exposed here. The server writes them on events
through app.services.notifications.notify(); a client never chooses who is
notified of what.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.notifications import Notification
from app.models.user import User
from app.schemas.notifications import NotificationOut

router = APIRouter()

MAX_PAGE_SIZE = 200


def _live(db: Session, user: User):
    """The caller's notifications that have not been dismissed."""
    return db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.dismissed_at.is_(None),
    )


def _own(db: Session, user: User, notification_id: int) -> Notification:
    notification = _live(db, user).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Unread first, then newest first.

    X-Total-Count is the number of live notifications and X-Unread-Count the
    number not read yet - what the bell shows - so the bell needs no second
    request and no page has to hold them all.
    """
    query = _live(db, current_user)
    response.headers["X-Total-Count"] = str(query.count())
    response.headers["X-Unread-Count"] = str(query.filter(Notification.read_at.is_(None)).count())
    rows = (
        query.order_by(Notification.read_at.isnot(None), Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [NotificationOut.from_orm_row(n) for n in rows]


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    notification = _own(db, current_user, notification_id)
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)
    return NotificationOut.from_orm_row(notification)


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated = (
        _live(db, current_user)
        .filter(Notification.read_at.is_(None))
        .update({Notification.read_at: datetime.now(timezone.utc)}, synchronize_session=False)
    )
    db.commit()
    return {"updated": updated}


@router.post("/notifications/{notification_id}/dismiss", status_code=204)
def dismiss(notification_id: int, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    """Clear one notification from the list. Soft: the row stays, with dismissed_at."""
    notification = _own(db, current_user, notification_id)
    notification.dismissed_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=204)


@router.post("/notifications/dismiss-all")
def dismiss_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    dismissed = _live(db, current_user).update(
        {Notification.dismissed_at: datetime.now(timezone.utc)}, synchronize_session=False)
    db.commit()
    return {"dismissed": dismissed}
