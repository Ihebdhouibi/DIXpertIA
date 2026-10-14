"""Verification before sending (#118): submit, approve, reject, send.

The flow, the roles, and the rules the endpoints answer for. The database
rules behind them are exercised in test_invoice_rules (series), test_invoice_edit
(frozen content) and directly in SQL below where the point is that SQL cannot
get round them.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from invoice_flow import approve, draft, sent, submit

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
        "nom": "Acme Corporation", "email": "a@acme.tn",
        "telephone": "+216 70 000 000", "adresse": "1 rue de Tunis",
    }).json()["id"]


@pytest.fixture
def a_draft(client, admin, a_client):
    return draft(client, admin, a_client).json()


def act(client, headers, invoice_id, action, **body):
    return client.post(f"/api/invoices/{invoice_id}/{action}", headers=headers, json=body or None)


# --- The flow ---------------------------------------------------------------

def test_the_whole_flow_with_its_history(client, admin, accountant, identities, a_draft):
    submitted = submit(client, identities, a_draft["id"])
    assert submitted.json()["reviewStatus"] == "Submitted"

    rejected = act(client, accountant, a_draft["id"], "reject", comment="Wrong VAT rate")
    assert rejected.json()["reviewStatus"] == "Rejected"
    assert rejected.json()["numero"] is None, "a rejected draft takes no number"

    assert submit(client, identities, a_draft["id"]).status_code == 200
    approved = act(client, accountant, a_draft["id"], "approve").json()
    assert approved["reviewStatus"] == "Approved"
    assert approved["numero"] and approved["reference"] == approved["numero"]
    assert approved["dateIssued"] == date.today().strftime("%b %d, %Y"), "dated on approval"

    sent_invoice = act(client, admin, a_draft["id"], "send").json()
    assert sent_invoice["status"] == "Sent"

    history = client.get(f"/api/invoices/{a_draft['id']}", headers=admin).json()["reviews"]
    assert [h["action"] for h in history] == ["submitted", "rejected", "submitted", "approved"]
    assert history[1]["comment"] == "Wrong VAT rate", "the admin corrects from this"


def test_the_list_filters_on_the_review_state(client, admin, accountant, identities, a_client):
    waiting = draft(client, admin, a_client).json()
    draft(client, admin, a_client)
    submit(client, identities, waiting["id"])
    queue = client.get("/api/invoices?review_status=submitted", headers=accountant).json()
    assert [i["id"] for i in queue] == [waiting["id"]], "the accountant's 'to verify' queue"


# --- Who does what -----------------------------------------------------------

def test_the_accountant_cannot_submit_or_send(client, accountant, a_draft):
    assert act(client, accountant, a_draft["id"], "submit").status_code == 403
    assert act(client, accountant, a_draft["id"], "send").status_code == 403


def test_the_admin_cannot_approve_or_reject(client, admin, identities, a_draft):
    submit(client, identities, a_draft["id"])
    assert act(client, admin, a_draft["id"], "approve").status_code == 403
    assert act(client, admin, a_draft["id"], "reject", comment="x").status_code == 403


def test_the_creator_never_decides(client, accountant, identities, a_draft, database):
    """Only admins create today, so make the accountant the creator to prove it."""
    submit(client, identities, a_draft["id"])
    with database.begin() as c:
        c.execute(text("UPDATE invoices SET cree_par_id = :u WHERE id = :i"),
                  {"u": identities["accountant"]["user_id"], "i": int(a_draft["id"])})
    assert act(client, accountant, a_draft["id"], "approve").status_code == 403
    # And the database refuses it too, whatever the path.
    with database.connect() as c:
        with pytest.raises(Exception, match="person who created it"):
            c.execute(text("INSERT INTO invoice_reviews (invoice_id, actor_id, action)"
                           " VALUES (:i, :u, 'APPROVED')"),
                      {"i": int(a_draft["id"]), "u": identities["accountant"]["user_id"]})


# --- The rules ---------------------------------------------------------------

def test_a_rejection_needs_a_comment(client, accountant, identities, a_draft):
    submit(client, identities, a_draft["id"])
    assert act(client, accountant, a_draft["id"], "reject", comment="   ").status_code == 422
    assert act(client, accountant, a_draft["id"], "reject").status_code == 422


def test_only_a_submitted_invoice_is_decided(client, accountant, a_draft):
    assert act(client, accountant, a_draft["id"], "approve").status_code == 409
    assert act(client, accountant, a_draft["id"], "reject", comment="x").status_code == 409


def test_an_unapproved_invoice_cannot_be_sent(client, admin, identities, a_draft, database):
    assert act(client, admin, a_draft["id"], "send").status_code == 409
    submit(client, identities, a_draft["id"])
    assert act(client, admin, a_draft["id"], "send").status_code == 409
    with database.connect() as c:
        with pytest.raises(Exception, match="before the accountant approves it"):
            c.execute(text("UPDATE invoices SET statut = 'ENVOYEE' WHERE id = :i"), {"i": int(a_draft["id"])})


def test_bookkeeping_starts_when_the_invoice_is_sent(client, admin, identities, a_client):
    waiting = draft(client, admin, a_client).json()
    moved = client.patch(f"/api/invoices/{waiting['id']}/processing-status",
                         headers=admin, json={"processing_status": "processed"})
    assert moved.status_code == 409
    assert "bookkeeping starts when it is sent" in moved.json()["detail"]

    out = sent(client, identities, a_client)
    booked = client.patch(f"/api/invoices/{out['id']}/processing-status",
                          headers=admin, json={"processing_status": "processed"})
    assert booked.status_code == 200


def test_an_approved_invoice_is_final(client, accountant, identities, a_draft):
    approve(client, identities, a_draft["id"])
    assert submit(client, identities, a_draft["id"]).status_code == 409
    assert act(client, accountant, a_draft["id"], "reject", comment="too late").status_code == 409


def test_an_overdue_draft_is_not_approved(client, admin, accountant, identities, a_draft, database):
    """Approval dates the invoice today; a due date already past would break ck_invoices_dates."""
    submit(client, identities, a_draft["id"])
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    with database.begin() as c:
        c.execute(text("ALTER TABLE invoices DISABLE TRIGGER invoice_draft_is_editable"))
        c.execute(text("UPDATE invoices SET date_emission = :d, date_echeance = :d WHERE id = :i"),
                  {"d": yesterday, "i": int(a_draft["id"])})
        c.execute(text("ALTER TABLE invoices ENABLE TRIGGER invoice_draft_is_editable"))
    response = act(client, accountant, a_draft["id"], "approve")
    assert response.status_code == 409
    assert "reject it so the due date can be corrected" in response.json()["detail"]


def test_a_supplier_bill_is_not_reviewed(client, admin, identities):
    supplier = client.post("/api/suppliers", headers=admin, json={"nom": "Tunisie Telecom"}).json()["id"]
    today = date.today().isoformat()
    bill = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": supplier, "supplier_reference": "TT-001",
        "date_emission": today, "date_echeance": today,
        "montant_ht": 100, "montant_ttc": 119, "items": [],
    }).json()
    assert submit(client, identities, bill["id"]).status_code == 409
