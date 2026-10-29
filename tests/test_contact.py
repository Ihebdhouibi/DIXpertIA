"""The public contact form (#98): enquiries are kept, the admins told, abuse refused.

Before, the form showed "Message received" while nothing left the browser.
"""

import pytest
from sqlalchemy import text

GOOD = {"name": "Amira Ben Salah", "email": "amira@example.tn", "topic": "security_audit",
        "message": "We would like a penetration test of our web portal."}


@pytest.fixture
def inbox(monkeypatch):
    """E-mails the contact service sends, captured; SMTP and CONTACT_INBOX set."""
    from app.core.config import settings
    from app.services import contact

    sent = []
    monkeypatch.setattr(settings, "CONTACT_INBOX", "inbox@dixpertia.test")
    monkeypatch.setattr(contact, "email_configured", lambda: True)
    def mock_send(to, subject, body, html_text=None, reply_to=None, **kwargs):
        sent.append((to, subject, body, reply_to))
        return True

    monkeypatch.setattr(contact, "send_email", mock_send)
    return sent


def stored(database):
    with database.connect() as c:
        return c.execute(text(
            "SELECT name, email, topic, message, sender_hash FROM contact_requests ORDER BY id")).all()


def send(client, **changes):
    return client.post("/api/contact", json={**GOOD, **changes})


# --- An enquiry is kept, and the admins are told ------------------------------

def test_an_enquiry_is_stored_without_signing_in(client, database):
    response = send(client)
    assert response.status_code == 200, response.text
    [row] = stored(database)
    assert row[:4] == ("Amira Ben Salah", "amira@example.tn", "security_audit", GOOD["message"])


def test_the_ip_is_never_stored_only_a_keyed_hash(client, database):
    send(client)
    [row] = stored(database)
    assert len(row.sender_hash) == 64 and "testclient" not in row.sender_hash


def test_every_admin_is_notified_and_nobody_else(client, identities, database):
    send(client)
    with database.connect() as c:
        rows = c.execute(text("SELECT user_id, link, params FROM notifications WHERE kind = 'contact_request'")).all()
    assert [r.user_id for r in rows] == [identities["admin"]["user_id"]]
    assert rows[0].link == "enquiries" and rows[0].params == {"name": "Amira Ben Salah", "topic": "security_audit"}
    [n] = client.get("/api/notifications", headers={**identities["admin"]["headers"], "Accept-Language": "en"}).json()
    assert n["message"] == "New enquiry from Amira Ben Salah about Security audit / penetration testing."


def test_it_is_emailed_to_our_inbox_only_with_the_sender_in_reply_to(client, inbox):
    send(client)
    [(to, subject, body, reply_to)] = inbox
    assert to == "inbox@dixpertia.test", "never to the address the visitor typed"
    assert reply_to == "amira@example.tn"
    assert "Amira Ben Salah" in subject and GOOD["message"] in body


def test_without_an_inbox_it_is_still_kept_and_nothing_is_emailed(client, database, monkeypatch):
    from app.core.config import settings
    from app.services import contact

    sent = []
    monkeypatch.setattr(settings, "CONTACT_INBOX", "")
    monkeypatch.setattr(contact, "send_email", lambda *a, **k: sent.append(a) or True)
    assert send(client).status_code == 200
    assert len(stored(database)) == 1 and sent == []


# --- Abuse is refused --------------------------------------------------------

def test_a_filled_honeypot_gets_the_same_answer_and_is_not_kept(client, database, inbox):
    real = send(client).json()
    bot = send(client, website="http://spam.example")
    assert bot.status_code == 200 and bot.json() == real, "the bot must not learn it was caught"
    assert len(stored(database)) == 1 and len(inbox) == 1


def test_one_sender_is_limited_per_hour(client, database, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CONTACT_LIMIT_PER_SENDER", 2)
    assert [send(client).status_code for _ in range(3)] == [200, 200, 429]
    refused = send(client)
    assert refused.headers["Retry-After"] == "3600" and "+216 28 814 729" in refused.json()["detail"]
    assert len(stored(database)) == 2


def test_everyone_together_is_limited_per_hour(client, database, monkeypatch):
    from app.core.config import settings
    from app.services import contact

    senders = iter(f"{n:064x}" for n in range(10))
    monkeypatch.setattr(contact, "sender_hash", lambda ip: next(senders))
    monkeypatch.setattr(settings, "CONTACT_LIMIT_TOTAL", 3)
    assert [send(client).status_code for _ in range(4)] == [200, 200, 200, 429]
    assert len(stored(database)) == 3


@pytest.mark.parametrize("changes", [
    {"name": ""},
    {"name": "Amira\r\nBcc: victim@example.com"},  # header injection
    {"name": "x" * 121},
    {"email": "not-an-address"},
    {"topic": "free_money"},
    {"message": "too short"},
    {"message": "x" * 5001},
])
def test_invalid_input_is_refused_and_not_kept(client, database, changes):
    assert send(client, **changes).status_code == 422
    assert stored(database) == []


def test_an_anonymous_caller_cannot_read_the_enquiries_even_in_sql(client, database):
    """The sender writes through the function only; the table stays closed."""
    import os

    from sqlalchemy import create_engine

    send(client)
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as c:
            assert c.execute(text("SELECT count(*) FROM contact_requests")).scalar() == 0
            with pytest.raises(Exception):
                c.execute(text("INSERT INTO contact_requests (name, email, topic, message, sender_hash)"
                               " VALUES ('x', 'x@x.tn', 'other', 'direct insert attempt', 'h')"))
    finally:
        engine.dispose()


# --- The admin reads and handles them ----------------------------------------

def test_the_admin_lists_them_newest_first_and_marks_one_handled(client, identities, database):
    admin = identities["admin"]["headers"]
    send(client)
    send(client, name="Karim Trabelsi")
    listed = client.get("/api/contact-requests", headers=admin)
    assert listed.status_code == 200 and listed.headers["X-Total-Count"] == "2"
    first, second = listed.json()
    assert first["name"] == "Karim Trabelsi" and first["handledAt"] is None

    handled = client.post(f"/api/contact-requests/{first['id']}/handle", headers=admin)
    assert handled.status_code == 200 and handled.json()["handledAt"] and handled.json()["handledBy"] == "Test admin"
    assert [e["id"] for e in client.get("/api/contact-requests?handled=false", headers=admin).json()] == [second["id"]]
    with database.connect() as c:
        actions = c.execute(text("SELECT action FROM audit_events WHERE entity = 'contact_request'")).scalars().all()
    assert actions == ["contact_request.handled"]


def test_an_unknown_enquiry_is_404(client, identities):
    assert client.post("/api/contact-requests/999999/handle", headers=identities["admin"]["headers"]).status_code == 404


@pytest.mark.parametrize("role", ["accountant", "employee"])
def test_only_the_admin_reads_them(client, identities, role):
    send(client)
    headers = identities[role]["headers"]
    assert client.get("/api/contact-requests", headers=headers).status_code == 403
