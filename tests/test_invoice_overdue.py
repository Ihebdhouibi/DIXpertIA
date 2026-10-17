"""Overdue is derived from the due date, never stored (#117).

A sent invoice whose due date has passed reads as Overdue, with no write;
due today is not yet overdue. The list filter applies the same rule, and the
database refuses storing EN_RETARD.

Supplier bills carry their own dates, so they make overdue cases without
waiting: an outgoing invoice is dated on approval and cannot be due before it.
The rule is the same for both directions.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from invoice_flow import pdf_text

pytestmark = pytest.mark.identity("admin")

TODAY = date.today()


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


@pytest.fixture
def bill(client, admin, accountant):
    supplier = client.post("/api/suppliers", headers=admin, json={"nom": "Fournisseur SA"}).json()["id"]
    counter = iter(range(1, 100))

    def make(due: date):
        response = client.post("/api/supplier-invoices", headers=accountant, json={
            "supplier_id": supplier, "supplier_reference": f"S-{next(counter):03d}",
            "date_emission": (TODAY - timedelta(days=40)).isoformat(), "date_echeance": due.isoformat(),
            "montant_ht": 100, "montant_ttc": 119, "items": []})
        assert response.status_code == 201, response.text
        return response.json()
    return make


def stored_status(database, invoice_id):
    with database.connect() as c:
        return c.execute(text("SELECT statut FROM invoices WHERE id = :i"), {"i": int(invoice_id)}).scalar_one()


def test_past_due_reads_as_overdue_without_any_write(bill, database):
    late = bill(TODAY - timedelta(days=1))
    assert late["status"] == "Overdue"
    assert stored_status(database, late["id"]) == "ENVOYEE", "derived, not stored"


def test_due_today_is_not_yet_overdue(bill):
    assert bill(TODAY)["status"] == "Sent"


def test_a_paid_invoice_is_never_overdue(client, accountant, bill):
    late = bill(TODAY - timedelta(days=5))
    paid = client.post(f"/api/invoices/{late['id']}/pay", headers=accountant,
                       json={"paid_on": TODAY.isoformat()})
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "Paid", "an overdue invoice is paid like a sent one"


def test_the_filter_follows_the_derived_status(client, accountant, bill):
    late = bill(TODAY - timedelta(days=1))
    on_time = bill(TODAY)
    paid_late = bill(TODAY - timedelta(days=3))
    client.post(f"/api/invoices/{paid_late['id']}/pay", headers=accountant, json={"paid_on": TODAY.isoformat()})

    def ids(statut):
        response = client.get("/api/invoices", headers=accountant, params={"statut": statut})
        assert response.status_code == 200, response.text
        return {i["id"] for i in response.json()}

    assert ids("en_retard") == {late["id"]}
    assert ids("envoyee") == {on_time["id"]}, "sent excludes overdue: one status per invoice"
    assert ids("payee") == {paid_late["id"]}


def test_the_pdf_says_overdue(client, accountant, bill):
    late = bill(TODAY - timedelta(days=1))
    pdf = client.get(f"/api/invoices/{late['id']}/download", headers=accountant)
    assert pdf.status_code == 200
    assert b"Overdue" in pdf_text(pdf.content)


def test_the_database_refuses_storing_overdue(bill, database):
    invoice_id = bill(TODAY - timedelta(days=1))["id"]
    with pytest.raises(DBAPIError, match="ck_invoices_overdue_is_derived"):
        with database.connect() as c:
            c.execute(text("UPDATE invoices SET statut = 'EN_RETARD' WHERE id = :i"), {"i": int(invoice_id)})
