"""Sending e-mail over SMTP, when it is configured.

Moved out of main.py for #134 so the reminder job can use it too, and reading
the settings module rather than os.getenv. Delivery is optional: with the SMTP
settings empty, send_email() logs a warning and returns False instead of
failing whatever asked for it.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

log = logging.getLogger("dixpertia")


def email_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not email_configured():
        log.warning("SMTP credentials missing. Email not sent.")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        log.info("Email sent to %s", to_email)
        return True
    except Exception as e:  # noqa: BLE001 - delivery must never fail the caller
        log.error("Email error: %s", e)
        return False
