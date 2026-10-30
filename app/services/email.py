"""Sending e-mail over SMTP, when it is configured.

Moved out of main.py for #134 so the reminder job can use it too, and reading
the settings module rather than os.getenv. Delivery is optional: with the SMTP
settings empty, send_email() logs a warning and returns False instead of
failing whatever asked for it.

"""

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

log = logging.getLogger("dixpertia")

# Port 465 speaks TLS from the first byte (SMTPS); any other port starts in
# clear and must upgrade with STARTTLS before the password is sent.
SMTPS_PORT = 465
TIMEOUT_SECONDS = 20


def email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html_text: str | None = None,
    reply_to: str | None = None
) -> bool:
    """Send an e-mail, optionally with an HTML alternative.
    `plain_text` is always required as a fallback (and to keep spam filters happy).
    `html_text` is optional; when provided, the e-mail is sent as multipart/alternative.
    `reply_to` lets the recipient answer someone else, such as a contact form's sender (#98).
    """
    if not email_configured():
        log.warning("SMTP credentials missing. Email not sent.")
        return False
    try:
        # Use multipart/alternative if an HTML part is provided (#211)
        if html_text:
            msg = MIMEMultipart("alternative")
            # Attach text first, HTML second (clients pick the best one they can render)
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(html_text, "html", "utf-8"))
        else:
            msg = MIMEMultipart()
            msg.attach(MIMEText(body, "plain", "utf-8"))

        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        if reply_to:
            msg["Reply-To"] = reply_to

        # A verified TLS connection, always: the mail server's certificate must
        # match SMTP_HOST, or the password could be handed to an impostor.
        # starttls() with no context checks nothing.
        context = ssl.create_default_context()
        if settings.SMTP_PORT == SMTPS_PORT:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT,
                                      context=context, timeout=TIMEOUT_SECONDS)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=TIMEOUT_SECONDS)
            server.starttls(context=context)
        with server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        log.info("Email sent to %s", to_email)
        return True
    except Exception as e:  # noqa: BLE001 - delivery must never fail the caller
        log.error("Email error: %s", e)
        return False
