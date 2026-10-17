"""The audit trail (#63): every sensitive action leaves exactly one event.

Events are written in the action's own transaction, by the signed-in identity,
and nobody can change or delete them afterwards. Only the admin reads them.
"""

import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from account_flow import link_token
from invoice_flow import draft, sent, submit

pytestmark = pytest.mark.identity("admin")

# Accounts made here are not truncated between tests (users holds the fixture
# accounts), so they are removed by this domain afterwards.
DOMAIN = "audit-test.tn"


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("DELETE FROM employees WHERE user_id IN "
                       "(SELECT id FROM users WHERE email LIKE :d)"), {"d": f"%@{DOMAIN}"})
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


@pytest.fixture
def a_client(client, admin):
    return client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "a@acme.tn",
        "telephone": "+216 70 000 000", "adresse": "1 rue de Tunis",
    }).json()["id"]


def events(database, entity=None, entity_id=None):
    """(action, actor_id, actor_role) in the order they were recorded."""
    sql = "SELECT action, actor_id, actor_role FROM audit_events"
    params = {}
    if entity:
        sql += " WHERE entity = :e AND entity_id = :i"
        params = {"e": entity, "i": str(entity_id)}
    with database.connect() as c:
        return [tuple(r) for r in c.execute(text(sql + " ORDER BY id"), params)]


def as_app_role(user_id, role):
    """A connection as dixpertia_app carrying an identity, like a request's."""
    engine = create_engine(os.environ["DATABASE_URL"])
    conn = engine.connect()
    conn.execute(text("SELECT set_config('app.user_id', :u, false), set_config('app.user_role', :r, false)"),
                 {"u": user_id or "", "r": role or ""})
    # Session-level settings survive the commit; committing ends the implicit
    # transaction SQLAlchemy began, so a test can open its own with begin().
    conn.commit()
    return engine, conn


# --- Each action, once, by whoever did it -------------------------------------

def test_the_invoice_flow_is_recorded_step_by_step(client, admin, accountant, identities, database, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    assert submit(client, identities, invoice_id).status_code == 200
    assert client.post(f"/api/invoices/{invoice_id}/reject", headers=accountant,
                       json={"comment": "Wrong VAT rate"}).status_code == 200
    assert client.patch(f"/api/invoices/{invoice_id}", headers=admin, json={
        "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 2, "prix_unitaire": 500, "taux_tva": 19}],
    }).status_code == 200
    assert submit(client, identities, invoice_id).status_code == 200
    assert client.post(f"/api/invoices/{invoice_id}/approve", headers=accountant).status_code == 200
    assert client.post(f"/api/invoices/{invoice_id}/send", headers=admin).status_code == 200

    admin_id = identities["admin"]["user_id"]
    accountant_id = identities["accountant"]["user_id"]
    assert events(database, "invoice", invoice_id) == [
        ("invoice.created", admin_id, "admin"),
        ("invoice.submitted", admin_id, "admin"),
        ("invoice.rejected", accountant_id, "accountant"),
        ("invoice.updated", admin_id, "admin"),
        ("invoice.submitted", admin_id, "admin"),
        ("invoice.approved", accountant_id, "accountant"),
        ("invoice.sent", admin_id, "admin"),
    ]


def test_an_approval_records_the_number_it_allocated(client, admin, accountant, identities, database, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    submit(client, identities, invoice_id)
    numero = client.post(f"/api/invoices/{invoice_id}/approve", headers=accountant).json()["numero"]
    with database.connect() as c:
        before, after = c.execute(text(
            "SELECT before, after FROM audit_events WHERE action = 'invoice.approved' AND entity_id = :i"),
            {"i": str(invoice_id)}).one()
    assert before["numero"] is None and before["review_status"] == "submitted"
    assert after["numero"] == numero and after["review_status"] == "approved"


def test_a_refused_action_records_nothing(client, admin, identities, database, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    refused = client.post(f"/api/invoices/{invoice_id}/send", headers=admin)
    assert refused.status_code == 409
    assert [e[0] for e in events(database, "invoice", invoice_id)] == ["invoice.created"]


def test_an_idempotent_replay_records_one_creation(client, admin, database, a_client):
    body = {"client_id": a_client, "date_echeance": "2027-12-31",
            "items": [{"designation": "Consulting", "quantite": 1, "prix_unitaire": 100, "taux_tva": 19}]}
    headers = {**admin, "Idempotency-Key": "audit-replay-1"}
    first = client.post("/api/invoices", headers=headers, json=body).json()
    second = client.post("/api/invoices", headers=headers, json=body).json()
    assert first["id"] == second["id"]
    assert [e[0] for e in events(database, "invoice", first["id"])] == ["invoice.created"]


def test_a_processing_move_is_recorded(client, admin, identities, database, a_client):
    invoice_id = sent(client, identities, a_client)["id"]
    moved = client.patch(f"/api/invoices/{invoice_id}/processing-status", headers=admin,
                         json={"processing_status": "processed"})
    assert moved.status_code == 200, moved.text
    with database.connect() as c:
        before, after = c.execute(text(
            "SELECT before, after FROM audit_events"
            " WHERE action = 'invoice.processing_status_changed' AND entity_id = :i"),
            {"i": str(invoice_id)}).one()
    assert (before["processing_status"], after["processing_status"]) == ("pending", "processed")


def test_the_month_close_is_recorded(client, admin, identities, database, a_client):
    waiting = draft(client, admin, a_client).json()
    month = date.today().strftime("%Y-%m")
    assert client.post(f"/api/periods/{month}/close", headers=admin).status_code == 200
    assert events(database, "accounting_period", month) == [
        ("accounting_period.closed", identities["admin"]["user_id"], "admin")]
    # A draft is not part of the close, so it records nothing of its own.
    assert [e[0] for e in events(database, "invoice", waiting["id"])] == ["invoice.created"]


def test_leave_decisions_are_recorded(client, admin, identities, database):
    employee = identities["employee"]["headers"]
    ids = []
    for start, end in (("2027-03-01", "2027-03-02"), ("2027-04-05", "2027-04-06")):
        created = client.post("/api/leave-requests", headers=employee, json={
            "startDate": start, "endDate": end, "type": "Annual Leave"})
        assert created.status_code == 201, created.text
        ids.append(created.json()["id"])
    assert client.post(f"/api/leave-requests/{ids[0]}/approve", headers=admin).status_code == 200
    assert client.post(f"/api/leave-requests/{ids[1]}/reject", headers=admin,
                       json={"comment": "Team is short that week"}).status_code == 200

    admin_id = identities["admin"]["user_id"]
    assert events(database, "leave_request", ids[0]) == [("leave_request.approved", admin_id, "admin")]
    assert events(database, "leave_request", ids[1]) == [("leave_request.rejected", admin_id, "admin")]


def test_account_creation_activation_and_password_reset_are_recorded(client, admin, identities, database, mailbox):
    email = f"new@{DOMAIN}"
    created = client.post("/api/users", headers=admin, json={
        "email": email, "firstName": "New", "lastName": "Hire", "role": "employee"})
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    activation = link_token(mailbox, email)

    assert client.post("/api/employees", headers=admin, json={
        "userId": user_id, "jobTitle": "Analyst", "hiredOn": "2026-10-01",
        "annualEntitlementDays": 21}).status_code == 201

    assert client.post("/api/activate", json={
        "token": activation, "newPassword": "a-first-password-long-enough"}).status_code == 200
    assert client.post("/api/forgot-password", json={"email": email}).status_code == 200
    reset = link_token(mailbox, email)
    assert client.post("/api/reset-password", json={
        "token": reset, "newPassword": "a-new-password-long-enough"}).status_code == 200

    admin_id = identities["admin"]["user_id"]
    assert events(database, "user", user_id) == [
        ("user.created", admin_id, "admin"),
        # Anonymous steps: nobody is signed in, and the trail says so.
        ("user.activated", None, None),
        ("user.password_reset_requested", None, None),
        ("user.password_reset", None, None),
    ]
    assert [e[0] for e in events(database, "employee", _employee_id(database, user_id))] == [
        "employee.created"]

    # No secret reaches the trail: not the links' tokens, nor the password hash.
    with database.connect() as c:
        trail = c.execute(text("SELECT string_agg(coalesce(before::text, '') || coalesce(after::text, ''), '')"
                               " FROM audit_events")).scalar_one() or ""
        hashed = c.execute(text('SELECT "hashedPassword" FROM users WHERE id = :u'), {"u": user_id}).scalar_one()
    for secret in (activation, reset, hashed):
        assert secret not in trail


def _employee_id(database, user_id):
    with database.connect() as c:
        return c.execute(text("SELECT id FROM employees WHERE user_id = :u"), {"u": user_id}).scalar_one()


def test_an_unknown_email_records_nothing(client, database):
    assert client.post("/api/forgot-password", json={"email": f"nobody@{DOMAIN}"}).status_code == 200
    assert events(database) == []


# --- Append-only, and written only in one's own name ---------------------------

def _one_event(database, identities):
    with database.connect() as c:
        return c.execute(text(
            "INSERT INTO audit_events (actor_id, actor_role, action, entity, entity_id)"
            " VALUES (:a, 'admin', 'test.event', 'test', '1') RETURNING id"),
            {"a": identities["admin"]["user_id"]}).scalar_one()


def test_the_application_role_cannot_change_or_delete_an_event(database, identities):
    event_id = _one_event(database, identities)
    engine, conn = as_app_role(identities["admin"]["user_id"], "admin")
    try:
        for statement in ("UPDATE audit_events SET action = 'tampered' WHERE id = :i",
                          "DELETE FROM audit_events WHERE id = :i"):
            with pytest.raises(DBAPIError, match="permission denied"):
                with conn.begin():
                    conn.execute(text(statement), {"i": event_id})
    finally:
        conn.close()
        engine.dispose()


def test_not_even_the_owner_can_change_or_delete_an_event(database, identities):
    event_id = _one_event(database, identities)
    for statement in ("UPDATE audit_events SET action = 'tampered' WHERE id = :i",
                      "DELETE FROM audit_events WHERE id = :i"):
        with pytest.raises(DBAPIError, match="append-only"):
            with database.connect() as c:
                c.execute(text(statement), {"i": event_id})


def test_an_event_cannot_be_written_in_someone_elses_name(identities):
    engine, conn = as_app_role(identities["employee"]["user_id"], "employee")
    try:
        with pytest.raises(DBAPIError, match="row-level security"):
            with conn.begin():
                conn.execute(text(
                    "INSERT INTO audit_events (actor_id, actor_role, action, entity, entity_id)"
                    " VALUES (:a, 'admin', 'invoice.approved', 'invoice', '1')"),
                    {"a": identities["admin"]["user_id"]})
    finally:
        conn.close()
        engine.dispose()


# --- Reading: the admin only ----------------------------------------------------

def test_only_the_admin_reads_the_trail_even_in_sql(database, identities):
    _one_event(database, identities)
    for role, expected in (("admin", 1), ("accountant", 0), ("employee", 0)):
        engine, conn = as_app_role(identities[role]["user_id"], role)
        try:
            assert conn.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == expected, role
        finally:
            conn.close()
            engine.dispose()


def test_the_admin_endpoint_filters_and_counts(client, admin, accountant, identities, a_client):
    first = draft(client, admin, a_client).json()["id"]
    draft(client, admin, a_client)
    submit(client, identities, first)

    everything = client.get("/api/audit-events", headers=admin)
    assert everything.status_code == 200
    assert everything.headers["X-Total-Count"] == "3"
    assert everything.json()[0]["action"] == "invoice.submitted", "newest first"

    one_invoice = client.get("/api/audit-events", headers=admin,
                             params={"entity": "invoice", "entityId": first})
    assert [e["action"] for e in one_invoice.json()] == ["invoice.submitted", "invoice.created"]

    by_action = client.get("/api/audit-events", headers=admin, params={"action": "invoice.created"})
    assert by_action.headers["X-Total-Count"] == "2"

    by_actor = client.get("/api/audit-events", headers=admin,
                          params={"actorId": identities["accountant"]["user_id"]})
    assert by_actor.json() == []

    today = date.today().isoformat()
    in_range = client.get("/api/audit-events", headers=admin, params={"since": today, "until": today})
    assert in_range.headers["X-Total-Count"] == "3"
    future = client.get("/api/audit-events", headers=admin, params={"since": "2099-01-01"})
    assert future.json() == []

    assert client.get("/api/audit-events", headers=accountant).status_code == 403
