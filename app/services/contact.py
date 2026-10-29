"""Receiving an enquiry from the public contact .

The order matters: limits and storage first, in one database call, then the
commit, then the e-mail. An enquiry is never lost, because it is a row before
anything can fail on the mail side, and nothing is e-mailed for an enquiry
that was not stored.

"""

import hashlib
import hmac
import html
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.i18n import DEFAULT_LOCALE, t
from app.services.email import email_configured, send_email
from app.services.email_template import render_html_email

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

    # 1. Prepare the translated topic label
    topic_label = t(f"contact.topic.{topic}", DEFAULT_LOCALE)

    # 2. Generate the plain text version (fallback)
    subject = t("email.contact.subject", DEFAULT_LOCALE, name=name, topic=topic_label)
    body = t("email.contact.body", DEFAULT_LOCALE, id=request_id, name=name, email=email,
             topic=topic_label, message=message, link=settings.FRONTEND_URL)

    # 3. Generate the HTML version securely (Escaping is mandatory here!)
    safe_name = html.escape(name)
    safe_email = html.escape(email)
    # Replace newlines with <br> to keep the message formatting in HTML
    safe_message = html.escape(message).replace('\n', '<br>')
    safe_topic = html.escape(topic_label)

    html_msg = t("email.contact.html_message", DEFAULT_LOCALE,
                 name=safe_name, email=safe_email, topic=safe_topic,
                 message=safe_message, link=settings.FRONTEND_URL)

    html_body = render_html_email(
        lang=DEFAULT_LOCALE,
        title=t("email.contact.html_title", DEFAULT_LOCALE),
        message_html=html_msg,
        footer_text=t("email.contact.html_footer", DEFAULT_LOCALE)
    )

    # 4. Send both parts (plain text + HTML)
    sent = send_email(
        to_email=settings.CONTACT_INBOX,
        subject=subject,
        plain_text=body,
        html_text=html_body,
        reply_to=email
    )

    if not sent:
        log.warning("Contact request %s stored but not e-mailed", request_id)
    return sent
