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

from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.identity import get_identity, set_identity
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
    message: str


def _since(invoice: Invoice, step: Step) -> datetime | None:
    """When the invoice entered its current step."""
    if step.started_by is None:
        # A draft has no creation time, only its creation date (date_emission
        # until approval, #118): it counts from the start of that day, in UTC.
        return datetime.combine(invoice.date_emission, time.min, tzinfo=timezone.utc)
    times = [r.created_at for r in invoice.reviews if r.action == step.started_by]
    return max(times) if times else None


def _message(invoice: Invoice, step: Step, days: int) -> str:
    who = invoice.client.nom if invoice.client else "an unknown client"
    ref = invoice.reference
    span = f"{days} day{'s' if days != 1 else ''}"
    if step.kind == "reminder_draft":
        return f"Invoice {ref} for {who} has been a draft for {span}. Submit it to the accountant when it is ready."
    if step.kind == "reminder_review":
        return f"Invoice {ref} for {who} has been waiting for your verification for {span}."
    if step.kind == "reminder_rejected":
        return f"Invoice {ref} for {who} was rejected {span} ago and has not been corrected. Correct and resubmit it."
    return f"Invoice {ref} for {who} was approved {span} ago and has not been sent to the client."


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
        message = _message(invoice, step, elapsed.days)
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
            notify(db, [user_id], kind=step.kind, tone="warning", message=message,
                   link="invoices", ref_type="invoice", ref_id=invoice.id, at=now)
            written.append(Reminder(invoice.id, step.kind, user_id, message))
    return written


def _email(db: Session, reminders: list[Reminder]) -> int:
    if not reminders or not email_configured():
        return 0
    emails = dict(db.query(User.id, User.email).filter(User.id.in_({r.user_id for r in reminders})))
    sent = 0
    for r in reminders:
        to = emails.get(r.user_id)
        body = f"{r.message}\n\nOpen DI Xpertia: {settings.FRONTEND_URL}\n"
        if to and send_email(to, "DI Xpertia - invoice reminder", body):
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
