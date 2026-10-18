"""Receiving an enquiry from the public contact form (#98).

The order matters: limits and storage first, in one database call, then the
commit, then the e-mail. An enquiry is never lost, because it is a row before
anything can fail on the mail side, and nothing is e-mailed for an enquiry
that was not stored.
"""

import hashlib
import hmac
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.i18n import DEFAULT_LOCALE, t
from app.services.email import email_configured, send_email

log = logging.getLogger("dixpertia")

SENDER_LIMITED = -1
EVERYONE_LIMITED = -2


def sender_hash(ip: str | None) -> str:
    """An HMAC of the sender's IP with the server secret: stable for counting,
    useless for recovering the address. The IP itself is never stored."""
    return hmac.new(settings.SECRET_KEY.encode(), (ip or "unknown").encode(), hashlib.sha256).hexdigest()


def submit(db: Session, *, name: str, email: str, topic: str, message: str, ip: str | None) -> int:
    """Store the enquiry and notify the admins, unless a limit is reached.

    Returns the new id, or SENDER_LIMITED / EVERYONE_LIMITED. Commits.
    """
    result = db.execute(
        text("SELECT submit_contact_request(:name, :email, :topic, :message, :sender, :per_sender, :total)"),
        {"name": name, "email": email, "topic": topic, "message": message, "sender": sender_hash(ip),
         "per_sender": settings.CONTACT_LIMIT_PER_SENDER, "total": settings.CONTACT_LIMIT_TOTAL},
    ).scalar_one()
    db.commit()
    return result


def email_inbox(*, request_id: int, name: str, email: str, topic: str, message: str) -> bool:
    """E-mail a stored enquiry to CONTACT_INBOX, if it and SMTP are configured.

    Only ever to our own inbox: the sender's address goes in Reply-To, so a
    reply reaches them, and nothing is sent to it automatically. Otherwise the
    form would mail whatever address a spammer typed.
    """
    if not settings.CONTACT_INBOX or not email_configured():
        return False
    subject = t("email.contact.subject", DEFAULT_LOCALE, name=name, topic=t(f"contact.topic.{topic}", DEFAULT_LOCALE))
    body = t("email.contact.body", DEFAULT_LOCALE, id=request_id, name=name, email=email,
             topic=t(f"contact.topic.{topic}", DEFAULT_LOCALE), message=message, link=settings.FRONTEND_URL)
    sent = send_email(settings.CONTACT_INBOX, subject, body, reply_to=email)
    if not sent:
        log.warning("Contact request %s stored but not e-mailed", request_id)
    return sent
