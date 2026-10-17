"""The public contact form and the admin's inbox of enquiries (#98).

POST /api/contact is public: it is listed in main.PUBLIC_PATHS, and it reaches
the database only through submit_contact_request() (a SECURITY DEFINER
function), never through a table. The admin routes read and mark enquiries
under row-level security that only lets the admin in.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.i18n import ApiError, t
from app.models.contact import ContactRequest
from app.models.user import User
from app.schemas.api import MessageOut
from app.schemas.contact import ContactIn, ContactRequestOut
from app.services import contact
from app.services.audit import record_event

public = APIRouter()
admin = APIRouter(dependencies=[Depends(require_roles("admin"))])

MAX_PAGE_SIZE = 200
# A refused sender may try again in an hour, when its oldest message ages out.
RETRY_AFTER_SECONDS = 3600


@public.post("/contact", response_model=MessageOut)
def send_enquiry(payload: ContactIn, request: Request, background: BackgroundTasks, db: Session = Depends(get_db)):
    """Receive an enquiry: store it, notify the admins, e-mail the inbox.

    A filled-in honeypot gets the same answer as a real enquiry and is not
    kept, so a bot learns nothing. Past a limit the answer is 429, with
    Retry-After, and a message that offers the phone instead.
    """
    answer = MessageOut(message=t("contact.received"))
    if payload.website:
        return answer

    ip = request.client.host if request.client else None
    result = contact.submit(db, name=payload.name, email=str(payload.email), topic=payload.topic,
                            message=payload.message, ip=ip)
    if result in (contact.SENDER_LIMITED, contact.EVERYONE_LIMITED):
        raise ApiError(429, "contact.too_many", headers={"Retry-After": str(RETRY_AFTER_SECONDS)})

    # After the commit, and off the request: the enquiry is safe already, and
    # a slow mail server should not keep the visitor waiting.
    background.add_task(contact.email_inbox, request_id=result, name=payload.name, email=str(payload.email),
                        topic=payload.topic, message=payload.message)
    return answer


@admin.get("/contact-requests", response_model=list[ContactRequestOut])
def list_enquiries(
    response: Response,
    db: Session = Depends(get_db),
    handled: bool | None = Query(None, description="true: handled only, false: open only"),
    limit: int = Query(50, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
):
    """Newest first. X-Total-Count is the number matching the filter."""
    query = db.query(ContactRequest)
    if handled is True:
        query = query.filter(ContactRequest.handled_at.isnot(None))
    elif handled is False:
        query = query.filter(ContactRequest.handled_at.is_(None))
    response.headers["X-Total-Count"] = str(query.count())
    rows = (
        db.query(ContactRequest, User.firstName, User.lastName)
        .outerjoin(User, User.id == ContactRequest.handled_by_id)
        .filter(ContactRequest.id.in_(query.with_entities(ContactRequest.id)))
        .order_by(ContactRequest.created_at.desc(), ContactRequest.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return [ContactRequestOut.from_row(r, f"{first or ''} {last or ''}".strip() or None) for r, first, last in rows]


@admin.post("/contact-requests/{request_id}/handle", response_model=ContactRequestOut)
def mark_handled(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))):
    """Mark an enquiry as answered. Once handled, it stays handled."""
    row = db.get(ContactRequest, request_id)
    if row is None:
        raise ApiError(404, "contact.not_found")
    if row.handled_at is None:
        record_event(db, "contact_request.handled", "contact_request", row.id)
        row.handled_at = datetime.now(timezone.utc)
        row.handled_by_id = user.id
        db.commit()
        db.refresh(row)
    return ContactRequestOut.from_row(row, f"{user.firstName} {user.lastName}".strip())
