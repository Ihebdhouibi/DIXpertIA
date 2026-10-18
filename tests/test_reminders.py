"""Reminders for invoices stuck in the verification flow (#134).

The job is called directly with a chosen `now`, through run_reminders_once():
the same path as the periodic task, under its own "reminders" identity, so
these tests also prove the policies that let it read the flow.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import text

from invoice_flow import draft, submit

pytestmark = pytest.mark.identity("admin")

SECOND = timedelta(seconds=1)


@pytest.fixture
def run():
    from app.services.reminders import run_reminders_once

    def _run(at):
        return [(r.kind, r.user_id) for r in run_reminders_once(at)]
    return _run


@pytest.fixture
def new_draft(client, identities):
    admin = identities["admin"]["headers"]
    client_id = client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "", "telephone": "", "adresse": ""}).json()["id"]

    def _new():
        response = draft(client, admin, client_id)
        assert response.status_code == 200, response.text
        return response.json()["id"]
    return _new


def started(database, invoice_id, action):
    """When the review step `action` happened, as stored."""
    with database.connect() as c:
        return c.execute(text(
            "SELECT max(created_at) FROM invoice_reviews WHERE invoice_id = :i AND action = :a"),
            {"i": invoice_id, "a": action.upper()}).scalar()


def draft_since():
    # A draft counts from the start of its creation day, in UTC.
    return datetime.combine(date.today(), time.min, tzinfo=timezone.utc)


# --- Each step reminds the right person, after its delay ----------------------

def test_a_draft_reminds_its_creator_after_three_days(run, new_draft, identities):
    new_draft()
    admin = identities["admin"]["user_id"]
    assert run(draft_since() + timedelta(days=3) - SECOND) == []
    assert run(draft_since() + timedelta(days=3)) == [("reminder_draft", admin)]


def test_a_submitted_invoice_reminds_the_accountants_not_the_admin(
        run, new_draft, client, identities, database):
    invoice_id = new_draft()
    submit(client, identities, invoice_id)
    since = started(database, invoice_id, "submitted")
    assert run(since + timedelta(days=2) - SECOND) == []
    assert run(since + timedelta(days=2)) == [("reminder_review", identities["accountant"]["user_id"])]


def test_a_rejected_invoice_reminds_its_creator(run, new_draft, client, identities, database):
    invoice_id = new_draft()
    submit(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/reject", headers=identities["accountant"]["headers"],
                json={"comment": "Wrong VAT rate"})
    since = started(database, invoice_id, "rejected")
    assert run(since + timedelta(days=2)) == [("reminder_rejected", identities["admin"]["user_id"])]


def test_an_approved_unsent_invoice_reminds_its_creator_after_one_day(
        run, new_draft, client, identities, database):
    invoice_id = new_draft()
    submit(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/approve", headers=identities["accountant"]["headers"])
    since = started(database, invoice_id, "approved")
    assert run(since + timedelta(days=1) - SECOND) == []
    assert run(since + timedelta(days=1)) == [("reminder_approved", identities["admin"]["user_id"])]


# --- Once per period, and never once it has moved on ---------------------------

def test_one_reminder_per_period_then_again_the_next(run, new_draft, identities):
    new_draft()
    reminded = [("reminder_draft", identities["admin"]["user_id"])]
    assert run(draft_since() + timedelta(days=3)) == reminded
    assert run(draft_since() + timedelta(days=3, hours=1)) == [], "the job runs hourly; once per period"
    assert run(draft_since() + timedelta(days=6) - SECOND) == []
    assert run(draft_since() + timedelta(days=6)) == reminded


def test_a_job_that_was_down_catches_up_with_one_reminder(run, new_draft):
    new_draft()
    assert len(run(draft_since() + timedelta(days=30))) == 1


def test_an_invoice_that_moved_on_is_not_reminded_for_its_old_step(
        run, new_draft, client, identities, database):
    invoice_id = new_draft()
    submit(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/approve", headers=identities["accountant"]["headers"])
    client.post(f"/api/invoices/{invoice_id}/send", headers=identities["admin"]["headers"])
    assert run(draft_since() + timedelta(days=60)) == [], "a sent invoice is never reminded"


def test_a_resubmitted_invoice_is_no_longer_reminded_as_rejected(
        run, new_draft, client, identities, database):
    invoice_id = new_draft()
    submit(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/reject", headers=identities["accountant"]["headers"],
                json={"comment": "Wrong VAT rate"})
    submit(client, identities, invoice_id)
    kinds = {kind for kind, _ in run(started(database, invoice_id, "submitted") + timedelta(days=2))}
    assert kinds == {"reminder_review"}


# --- Settings, e-mail, and the job's own guarantees ---------------------------

def test_the_delays_come_from_settings(run, new_draft, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "REMINDER_DRAFT_DAYS", 1)
    new_draft()
    assert len(run(draft_since() + timedelta(days=1))) == 1


def test_the_reminder_is_shown_in_the_app(run, new_draft, client, identities):
    new_draft()
    run(draft_since() + timedelta(days=3))
    [n] = client.get("/api/notifications", headers=identities["admin"]["headers"]).json()
    assert n["kind"] == "reminder_draft" and n["type"] == "warning" and n["link"] == "invoices"
    assert "has been a draft for 3 days" in n["message"] and "Acme Corporation" in n["message"]


def test_reminders_are_emailed_when_smtp_is_configured(run, new_draft, identities, monkeypatch):
    from app.core.config import settings
    from app.services import reminders

    sent = []
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(settings, "SMTP_USER", "user")
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "secret")
    monkeypatch.setattr(reminders, "send_email", lambda to, subject, body: sent.append((to, body)) or True)
    new_draft()
    run(draft_since() + timedelta(days=3))
    assert [to for to, _ in sent] == [identities["admin"]["email"]]
    # In the recipient's language (#135): the test accounts are French, the default.
    assert "est un brouillon depuis" in sent[0][1]


def test_without_smtp_reminders_are_in_app_only(run, new_draft, monkeypatch):
    from app.core.config import settings
    from app.services import reminders

    sent = []
    monkeypatch.setattr(settings, "SMTP_HOST", "")
    monkeypatch.setattr(reminders, "send_email", lambda *a: sent.append(a) or True)
    new_draft()
    assert len(run(draft_since() + timedelta(days=3))) == 1
    assert sent == []


def test_a_second_pass_waits_for_the_running_one(run, new_draft, database):
    """Several API workers each run the job: only the one holding the lock writes."""
    from app.services.reminders import ADVISORY_LOCK_KEY

    new_draft()
    with database.connect() as c:
        c.execute(text("SELECT pg_advisory_lock(:k)"), {"k": ADVISORY_LOCK_KEY})
        try:
            assert run(draft_since() + timedelta(days=3)) == []
        finally:
            c.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": ADVISORY_LOCK_KEY})
    assert len(run(draft_since() + timedelta(days=3))) == 1


def test_the_job_identity_can_read_but_not_change_invoices(new_draft):
    from app.core.database import SessionLocal
    from app.core.identity import get_identity, set_identity

    invoice_id = new_draft()
    previous = get_identity()
    set_identity(None, "reminders")
    try:
        with SessionLocal() as db:
            assert db.execute(text("SELECT count(*) FROM invoices WHERE id = :i"), {"i": invoice_id}).scalar() == 1
            changed = db.execute(text("UPDATE invoices SET date_echeance = date_echeance WHERE id = :i"),
                                 {"i": invoice_id}).rowcount
            db.rollback()
    finally:
        set_identity(*previous)
    assert changed == 0
