from typing import Optional

from pydantic import BaseModel


class NotificationOut(BaseModel):
    """A notification as the UI reads it (#116).

    `type` and `read` keep the shape the bell and the notifications page
    already used when notifications lived in the browser, so the UI only
    changes where they come from. `timestamp` is milliseconds since the epoch,
    as Date.now() gave before.
    """

    id: str
    kind: str
    message: str
    type: str
    read: bool
    timestamp: int
    link: Optional[str] = None
    refType: Optional[str] = None
    refId: Optional[int] = None

    @classmethod
    def from_orm_row(cls, row) -> "NotificationOut":
        return cls(
            id=str(row.id),
            kind=row.kind,
            message=row.message,
            type=row.tone,
            read=row.read_at is not None,
            timestamp=int(row.created_at.timestamp() * 1000) if row.created_at else 0,
            link=row.link or None,
            refType=row.ref_type,
            refId=row.ref_id,
        )
