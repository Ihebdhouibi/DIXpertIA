"""An invoice's history (#115), read from the audit trail of #63.

The trail already records every step. These tests cover what #115 adds: the
history endpoint, its wording, and the policy that lets the accountant read
invoice events - and only those.
"""

import os

import pytest
from sqlalchemy import create_engine, text

from invoice_flow import approve, draft, submit

pytestmark = pytest.mark.identity("admin")


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


@pytest.fixture
def a_client(client, admin):
    return client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "", "telephone": "", "adresse": ""}).json()["id"]


def history(client, headers, invoice_id):
    response = client.get(f"/api/invoices/{invoice_id}/history", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_the_whole_life_of_an_invoice_newest_first(client, admin, accountant, identities, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    submit(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/reject", headers=accountant, json={"comment": "Wrong VAT rate"})
    client.patch(f"/api/invoices/{invoice_id}", headers=admin, json={
        "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1, "prix_unitaire": 900, "taux_tva": 19}]})
    approved = approve(client, identities, invoice_id)
    client.post(f"/api/invoices/{invoice_id}/send", headers=admin)
    client.patch(f"/api/invoices/{invoice_id}/processing-status", headers=accountant,
                 json={"processing_status": "processed"})

    labels = [e["label"] for e in history(client, accountant, invoice_id)]
    assert labels == [
        "Books: Pending to Processed",
        "Sent to the client",
        f"Approved, numbered {approved['numero']}",
        "Submitted for verification",
        "Draft corrected",
        "Rejected: Wrong VAT rate",
        "Submitted for verification",
        "Draft created",
    ]


def test_paid_and_cancelled_read_in_words(client, admin, accountant, identities, a_client):
    """The commercial steps of #126 join the history."""
    from datetime import date

    from invoice_flow import sent

    paid = sent(client, identities, a_client)
    client.post(f"/api/invoices/{paid['id']}/pay", headers=accountant, json={"paid_on": date.today().isoformat()})
    assert history(client, accountant, paid["id"])[0]["label"] == f"Paid on {date.today().isoformat()}"

    dropped = draft(client, admin, a_client).json()["id"]
    client.post(f"/api/invoices/{dropped}/cancel", headers=admin, json={"reason": "Client withdrew the order"})
    assert history(client, admin, dropped)[0]["label"] == "Cancelled: Client withdrew the order"


def test_each_step_names_who_did_it(client, admin, accountant, identities, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    approve(client, identities, invoice_id)
    steps = {e["action"]: (e["actorName"], e["actorRole"]) for e in history(client, admin, invoice_id)}
    assert steps["invoice.created"] == ("Test admin", "admin")
    assert steps["invoice.approved"] == ("Test accountant", "accountant")


def test_only_this_invoices_events(client, admin, a_client):
    first = draft(client, admin, a_client).json()["id"]
    draft(client, admin, a_client)
    assert len(history(client, admin, first)) == 1


def test_a_supplier_bill_reads_as_recorded(client, admin):
    supplier = client.post("/api/suppliers", headers=admin, json={
        "nom": "Tunisie Telecom", "email": "", "telephone": "", "adresse": ""}).json()["id"]
    bill = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": supplier, "supplier_reference": "TT-001",
        "date_emission": "2026-10-05", "date_echeance": "2026-11-05",
        "montant_ht": 100, "montant_ttc": 119, "items": []}).json()
    [step] = history(client, admin, bill["id"])
    assert step["label"] == f"Supplier bill recorded as {bill['numero']}"


def test_an_unknown_invoice_is_404(client, admin):
    assert client.get("/api/invoices/999999/history", headers=admin).status_code == 404


def test_the_employee_is_refused(client, identities, admin, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    assert client.get(f"/api/invoices/{invoice_id}/history",
                      headers=identities["employee"]["headers"]).status_code == 403


# --- The policy: the accountant reads invoice events, nothing else ----------

def _as_app_role(user_id, role):
    engine = create_engine(os.environ["DATABASE_URL"])
    conn = engine.connect()
    conn.execute(text("SELECT set_config('app.user_id', :u, false), set_config('app.user_role', :r, false)"),
                 {"u": user_id or "", "r": role or ""})
    conn.commit()
    return engine, conn


def test_the_accountant_reads_invoice_events_and_nothing_else(database, identities):
    with database.connect() as c:
        for entity in ("invoice", "user", "leave_request", "accounting_period"):
            c.execute(text(
                "INSERT INTO audit_events (actor_id, actor_role, action, entity, entity_id)"
                " VALUES (:a, 'admin', 'test.event', :e, '1')"),
                {"a": identities["admin"]["user_id"], "e": entity})
    for role, visible in (("accountant", {"invoice"}), ("employee", set()),
                          ("admin", {"invoice", "user", "leave_request", "accounting_period"})):
        engine, conn = _as_app_role(identities[role]["user_id"], role)
        try:
            seen = set(conn.execute(text("SELECT entity FROM audit_events")).scalars())
        finally:
            conn.close()
            engine.dispose()
        assert seen == visible, role


def test_the_trail_listing_stays_admin_only(client, accountant):
    """Reading invoice history does not open GET /api/audit-events to the accountant."""
    assert client.get("/api/audit-events", headers=accountant).status_code == 403
