"""Reminders for invoices stuck in the verification flow (#134).

An invoice must never sit at a step of the flow (#118) without the person who
has to act being told. Past a delay at a step, that person gets a reminder,
and again every such period while the invoice stays there:

    a draft, never submitted     since its creation      -> its creator
    submitted, not reviewed      since the submission    -> every accountant
    rejected, not corrected      since the rejection     -> its creator
    approved, not sent           since the approval      -> its creator

Reminders are notifications (#116), and also e-mails when SMTP is configured.
One per period at most: a run that finds a reminder already written for the
current period writes nothing, so the job may run as often as it likes, and a
job that was down catches up with one reminder, not a backlog.

IDENTITY. The job acts for nobody, so it does not borrow a user's identity: it
runs as the role "reminders", which the policies of migration 7c1e5a9d2b40
allow to READ invoices, their reviews, clients and notifications, and nothing
else. It writes notifications like any server event. No account can hold that
role: ck_users_role limits users to admin, employee and accountant.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
import html
from app.services.email_template import render_html_email

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.identity import get_identity, set_identity
from app.i18n import render_notification, t
from app.models.invoicing import (
    Invoice,
    InvoiceDirection,
    InvoiceReviewAction,
    InvoiceReviewStatus,
    InvoiceStatus,
)
from app.models.notifications import Notification
from app.models.user import User
from app.services.email import email_configured, send_email
from app.services.notifications import notify, users_with_role

log = logging.getLogger("dixpertia")

JOB_ROLE = "reminders"
# Any constant: it only has to be the same for every process of this app.
ADVISORY_LOCK_KEY = 134_134


@dataclass(frozen=True)
class Step:
    kind: str
    delay_days: int
    # The review action that started the step; None for a draft, which starts
    # when it is created.
    started_by: InvoiceReviewAction | None
    to_accountants: bool


def _steps() -> dict[InvoiceReviewStatus, Step]:
    # Read at call time, so tests and a changed .env see the current values.
    return {
        InvoiceReviewStatus.NOT_SUBMITTED: Step(
            "reminder_draft", settings.REMINDER_DRAFT_DAYS, None, False),
        InvoiceReviewStatus.SUBMITTED: Step(
            "reminder_review", settings.REMINDER_REVIEW_DAYS, InvoiceReviewAction.SUBMITTED, True),
        InvoiceReviewStatus.REJECTED: Step(
            "reminder_rejected", settings.REMINDER_REJECTED_DAYS, InvoiceReviewAction.REJECTED, False),
        InvoiceReviewStatus.APPROVED: Step(
            "reminder_approved", settings.REMINDER_APPROVED_DAYS, InvoiceReviewAction.APPROVED, False),
    }


@dataclass(frozen=True)
class Reminder:
    invoice_id: int
    kind: str
    user_id: str
    # The facts of the reminder (#135): rendered in each reader's language.
    params: dict


def _since(invoice: Invoice, step: Step) -> datetime | None:
    """When the invoice entered its current step."""
    if step.started_by is None:
        # A draft has no creation time, only its creation date (date_emission
        # until approval, #118): it counts from the start of that day, in UTC.
        return datetime.combine(invoice.date_emission, time.min, tzinfo=timezone.utc)
    times = [r.created_at for r in invoice.reviews if r.action == step.started_by]
    return max(times) if times else None


def _params(invoice: Invoice, days: int) -> dict:
    """What a reminder says, as facts; the text is in app.i18n (#135)."""
    return {"ref": invoice.reference, "party": invoice.client.nom if invoice.client else None, "days": days}


def send_due_reminders(db: Session, now: datetime) -> list[Reminder]:
    """Write the reminders due at `now`, in the caller's transaction.

    Returns what was written, so the caller can e-mail it once committed.
    """
    steps = _steps()
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.client), selectinload(Invoice.reviews))
        .filter(
            Invoice.direction == InvoiceDirection.OUTGOING,
            # All four steps happen before the invoice is sent; a sent or
            # cancelled invoice has moved on and is never reminded.
            Invoice.statut == InvoiceStatus.BROUILLON,
        )
        .all()
    )
    accountants = users_with_role(db, "accountant")
    active = {u for (u,) in db.query(User.id).filter(User.isActive.is_(True))}

    written: list[Reminder] = []
    for invoice in invoices:
        step = steps.get(invoice.review_status)
        since = _since(invoice, step) if step else None
        if since is None:
            continue
        delay = timedelta(days=step.delay_days)
        elapsed = now - since
        if elapsed < delay:
            continue
        # The start of the current period: a reminder written since then means
        # this period is already covered.
        period_start = since + delay * (elapsed // delay)
        recipients = accountants if step.to_accountants else [invoice.cree_par_id]
        params = _params(invoice, elapsed.days)
        for user_id in recipients:
            if user_id not in active:
                continue
            already = db.query(Notification.id).filter(
                Notification.user_id == user_id,
                Notification.kind == step.kind,
                Notification.ref_type == "invoice",
                Notification.ref_id == invoice.id,
                Notification.created_at >= period_start,
            ).first()
            if already:
                continue
            notify(db, [user_id], kind=step.kind, tone="warning", params=params,
                   link="invoices", ref_type="invoice", ref_id=invoice.id, at=now)
            written.append(Reminder(invoice.id, step.kind, user_id, params))
    return written


def _email(db: Session, reminders: list[Reminder]) -> int:
    if not reminders or not email_configured():
        return 0
    # Each e-mail in its recipient's language (#135).
    recipients = {
        user_id: (email, locale)
        for user_id, email, locale in db.query(User.id, User.email, User.locale)
        .filter(User.id.in_({r.user_id for r in reminders}))
    }
    sent = 0
    for r in reminders:
        to, locale = recipients.get(r.user_id, (None, None))
        if not to:
            continue

        # 1. Generate the notification message
        message_text = render_notification(r.kind, r.params, locale)
        if not message_text:
            continue

        # 2. Plain text version (fallback)
        plain_body = t("email.reminder.body", locale, message=message_text, url=settings.FRONTEND_URL)

        # 3. HTML version (with escaping for security)
        safe_message = html.escape(message_text)
        safe_url = html.escape(settings.FRONTEND_URL)

        html_msg = t("email.reminder.html_message", locale, message=safe_message)
        html_body = render_html_email(
            lang=locale,
            title=t("email.reminder.html_title", locale),
            message_html=html_msg,
            action_url=safe_url,
            action_text=t("email.reminder.html_action", locale),
            footer_text=t("email.reminder.html_footer", locale)
        )

        # 4. Send both versions
        if send_email(
            to_email=to,
            subject=t("email.reminder.subject", locale),
            plain_text=plain_body,
            html_text=html_body
        ):
            sent += 1
    return sent


def run_reminders_once(now: datetime | None = None) -> list[Reminder]:
    """One pass of the job: write what is due, commit, then e-mail it.

    A transaction-level advisory lock keeps it to one pass at a time across
    workers; a pass that does not get the lock does nothing. E-mail goes out
    only after the commit, so a failed pass sends nothing.
    """
    now = now or datetime.now(timezone.utc)
    previous = get_identity()
    set_identity(None, JOB_ROLE)
    try:
        with SessionLocal() as db:
            if not db.execute(text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": ADVISORY_LOCK_KEY}).scalar():
                return []
            reminders = send_due_reminders(db, now)
            db.commit()
            emailed = _email(db, reminders)
        if reminders:
            log.info("Reminders: %d written, %d e-mailed", len(reminders), emailed)
        return reminders
    finally:
        set_identity(*previous)


async def reminder_loop() -> None:
    """Run the job now, then every REMINDER_INTERVAL_MINUTES, until cancelled."""
    while True:
        try:
            await asyncio.to_thread(run_reminders_once)
        except Exception:  # noqa: BLE001 - one failed pass must not stop the next
            log.exception("Reminder job failed")
        await asyncio.sleep(settings.REMINDER_INTERVAL_MINUTES * 60)
