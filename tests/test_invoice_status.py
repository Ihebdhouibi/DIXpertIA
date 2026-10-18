"""Paid and cancelled (#126): the commercial transitions after #118's send.

Mark paid: admin or accountant, a sent invoice or bill, in full on a date that
is neither in the future nor before the issue date. Cancel: admin, with a
reason, a draft not under verification or a sent invoice, never once its month
is closed. Paid and cancelled are final. The database holds the same rules
(trg_invoice_commercial_transitions and the CHECKs), tested directly at the end.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from invoice_flow import draft, numbered, sent, submit

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


def pay(client, headers, invoice_id, on=None):
    return client.post(f"/api/invoices/{invoice_id}/pay", headers=headers,
                       json={"paid_on": (on or date.today()).isoformat()})


def cancel(client, headers, invoice_id, reason="Duplicate of another invoice"):
    return client.post(f"/api/invoices/{invoice_id}/cancel", headers=headers, json={"reason": reason})


def actions(database, invoice_id):
    with database.connect() as c:
        return [r[0] for r in c.execute(text(
            "SELECT action FROM audit_events WHERE entity = 'invoice' AND entity_id = :i ORDER BY id"),
            {"i": str(invoice_id)})]


# --- Paid -------------------------------------------------------------------------

def test_the_accountant_marks_a_sent_invoice_paid(client, accountant, identities, database, a_client):
    invoice = sent(client, identities, a_client)
    paid = pay(client, accountant, invoice["id"])
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "Paid"
    assert paid.json()["paidOn"] == date.today().strftime("%b %d, %Y")
    assert actions(database, invoice["id"])[-1] == "invoice.paid"


def test_the_admin_may_mark_paid_too(client, admin, identities, a_client):
    invoice = sent(client, identities, a_client)
    assert pay(client, admin, invoice["id"]).status_code == 200


def test_paid_is_final(client, admin, accountant, identities, a_client):
    invoice = sent(client, identities, a_client)
    pay(client, accountant, invoice["id"])
    assert pay(client, accountant, invoice["id"]).status_code == 409
    refused = cancel(client, admin, invoice["id"])
    assert refused.status_code == 409 and "paid" in refused.json()["detail"]


def test_a_draft_cannot_be_marked_paid(client, admin, accountant, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    assert pay(client, accountant, invoice_id).status_code == 409


@pytest.mark.parametrize("days", [1, -1])
def test_the_payment_date_is_neither_future_nor_before_issue(client, accountant, identities, a_client, days):
    invoice = sent(client, identities, a_client)  # issued today, on approval
    response = pay(client, accountant, invoice["id"], on=date.today() + timedelta(days=days))
    assert response.status_code == 422


def test_a_supplier_bill_can_be_marked_paid(client, admin, accountant):
    supplier = client.post("/api/suppliers", headers=admin, json={"nom": "Fournisseur SA"}).json()["id"]
    bill = client.post("/api/supplier-invoices", headers=accountant, json={
        "supplier_id": supplier, "supplier_reference": "S-001",
        "date_emission": date.today().isoformat(), "date_echeance": date.today().isoformat(),
        "montant_ht": 100, "montant_ttc": 119, "items": []}).json()
    assert pay(client, accountant, bill["id"]).json()["status"] == "Paid"


# --- Cancelled ----------------------------------------------------------------------

def test_the_admin_cancels_a_draft_with_a_reason(client, admin, database, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    cancelled = cancel(client, admin, invoice_id, "Client withdrew the order")
    assert cancelled.status_code == 200, cancelled.text
    body = cancelled.json()
    assert body["status"] == "Cancelled" and body["numero"] is None, "a draft takes no number"
    assert body["cancellationReason"] == "Client withdrew the order" and body["cancelledAt"]
    assert actions(database, invoice_id)[-1] == "invoice.cancelled"


@pytest.mark.parametrize("reason", ["", "   "])
def test_a_reason_is_required(client, admin, a_client, reason):
    invoice_id = draft(client, admin, a_client).json()["id"]
    assert cancel(client, admin, invoice_id, reason).status_code == 422


def test_only_the_admin_cancels(client, admin, accountant, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    assert cancel(client, accountant, invoice_id).status_code == 403


def test_an_invoice_under_verification_cannot_be_cancelled(client, admin, identities, a_client):
    invoice_id = draft(client, admin, a_client).json()["id"]
    submit(client, identities, invoice_id)
    refused = cancel(client, admin, invoice_id)
    assert refused.status_code == 409 and "verification" in refused.json()["detail"]


def test_a_numbered_invoice_keeps_its_number_and_the_accountant_is_told(
        client, admin, identities, database, a_client):
    approved = numbered(client, identities, a_client)
    cancelled = cancel(client, admin, approved["id"]).json()
    assert cancelled["status"] == "Cancelled"
    assert cancelled["numero"] == approved["numero"], "the number stays in the series"
    with database.connect() as c:
        told = c.execute(text("SELECT user_id FROM notifications WHERE kind = 'invoice_cancelled'"
                              " AND ref_id = :i"), {"i": int(approved["id"])}).scalars().all()
    assert told == [identities["accountant"]["user_id"]]


def test_a_sent_invoice_can_be_cancelled_and_cancelled_is_final(client, admin, accountant, identities, a_client):
    invoice = sent(client, identities, a_client)
    assert cancel(client, admin, invoice["id"]).json()["status"] == "Cancelled"
    assert pay(client, accountant, invoice["id"]).status_code == 409
    assert cancel(client, admin, invoice["id"]).status_code == 409


# --- After the month is closed ------------------------------------------------------

def _closed_month_invoice(client, admin, identities, a_client):
    invoice = sent(client, identities, a_client)
    for state in ("processed", "completed"):
        client.patch(f"/api/invoices/{invoice['id']}/processing-status", headers=admin,
                     json={"processing_status": state})
    closed = client.post(f"/api/periods/{date.today().strftime('%Y-%m')}/close", headers=admin)
    assert closed.status_code == 200, closed.text
    return invoice


def test_late_payment_is_recorded_after_the_close(client, admin, accountant, identities, a_client):
    invoice = _closed_month_invoice(client, admin, identities, a_client)
    assert pay(client, accountant, invoice["id"]).json()["status"] == "Paid"


def test_an_invoice_of_a_closed_month_cannot_be_cancelled(client, admin, identities, a_client):
    invoice = _closed_month_invoice(client, admin, identities, a_client)
    refused = cancel(client, admin, invoice["id"])
    assert refused.status_code == 409 and "closed month" in refused.json()["detail"]


# --- The database holds the same rules ----------------------------------------------

def test_sql_cannot_reopen_a_paid_invoice(client, accountant, identities, database, a_client):
    invoice = sent(client, identities, a_client)
    pay(client, accountant, invoice["id"])
    with pytest.raises(DBAPIError, match="final"):
        with database.connect() as c:
            c.execute(text("UPDATE invoices SET statut = 'ENVOYEE', paid_on = NULL WHERE id = :i"),
                      {"i": int(invoice["id"])})


def test_sql_cannot_cancel_without_a_reason_or_pay_without_a_date(client, admin, identities, database, a_client):
    draft_id = int(draft(client, admin, a_client).json()["id"])
    invoice_id = int(sent(client, identities, a_client)["id"])
    with pytest.raises(DBAPIError, match="ck_invoices_cancelled_has_reason"):
        with database.connect() as c:
            c.execute(text("UPDATE invoices SET statut = 'ANNULEE' WHERE id = :i"), {"i": draft_id})
    with pytest.raises(DBAPIError, match="ck_invoices_paid_has_date"):
        with database.connect() as c:
            c.execute(text("UPDATE invoices SET statut = 'PAYEE' WHERE id = :i"), {"i": invoice_id})


def test_sql_cannot_skip_from_draft_to_paid(client, admin, database, a_client):
    draft_id = int(draft(client, admin, a_client).json()["id"])
    with pytest.raises(DBAPIError, match="cannot go from brouillon to payee"):
        with database.connect() as c:
            c.execute(text("UPDATE invoices SET statut = 'PAYEE', paid_on = current_date WHERE id = :i"),
                      {"i": draft_id})
