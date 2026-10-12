"""The invoice PDF download (#86): reachable from the UI, and robust to its data.

Three defects shared one endpoint: the route matched `numero` while the UI
sent the internal id (404 for every invoice), a NULL client address crashed
the generator, and a supplier bill printed its counterparty as "Unknown".
An unclosed tag such as "<b>" in a name or a line made ReportLab fail too.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

# The app is imported inside the tests, not here: conftest points the
# environment at the test database first, and importing app modules at
# collection time would bind them before that.

pytestmark = pytest.mark.identity("admin")


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


def make_client(client, admin, nom="Acme Corporation", adresse="1 rue de Tunis"):
    return client.post("/api/clients", headers=admin, json={
        "nom": nom, "email": "a@acme.tn", "telephone": "+216 70 000 000", "adresse": adresse,
    }).json()["id"]


def issue(client, admin, client_id, designation="Consulting"):
    return client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": designation, "quantite": 1,
                   "prix_unitaire": 1000, "taux_tva": 19}],
    }).json()


# --- The route -------------------------------------------------------------

def test_the_pdf_downloads_by_internal_id(client, admin):
    invoice = issue(client, admin, make_client(client, admin))
    response = client.get(f"/api/invoices/{invoice['id']}/download", headers=admin)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    # The file is still named after the legal number.
    assert invoice["numero"] in response.headers["content-disposition"]


def test_an_unknown_id_is_404(client, admin):
    assert client.get("/api/invoices/999999/download", headers=admin).status_code == 404


def test_the_number_is_no_longer_the_path(client, admin):
    """The old URL shape is refused rather than silently matching something."""
    invoice = issue(client, admin, make_client(client, admin))
    assert client.get(f"/api/invoices/{invoice['numero']}/download", headers=admin).status_code == 422


# --- The data --------------------------------------------------------------

def test_a_null_contact_field_can_no_longer_be_stored(database):
    """The root cause: the default of '' existed in Python only."""
    with database.connect() as c:
        # Matched loosely: the wording follows the server's locale.
        with pytest.raises(Exception, match="(?i)null"):
            c.execute(text("INSERT INTO clients (nom, adresse) VALUES ('Raw SQL client', NULL)"))


def test_a_row_inserted_outside_the_orm_gets_empty_contact_fields(database):
    with database.begin() as c:
        c.execute(text("INSERT INTO clients (nom) VALUES ('Raw SQL client')"))
        row = c.execute(text(
            "SELECT email, telephone, adresse FROM clients WHERE nom = 'Raw SQL client'")).first()
    assert tuple(row) == ("", "", "")


def test_markup_in_names_and_lines_does_not_break_the_pdf(client, admin):
    # "<b>" left open made the old generator raise ValueError; it is now
    # escaped and printed as text.
    client_id = make_client(client, admin, nom="R&D <b>Consulting", adresse="12 rue A & B\n<i>Tunis")
    invoice = issue(client, admin, client_id, designation="<i>Audit phase 1")
    response = client.get(f"/api/invoices/{invoice['id']}/download", headers=admin)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_the_generator_tolerates_missing_values():
    from app.services.invoice_generator import generate_invoice_pdf

    pdf = generate_invoice_pdf({
        "invoice_id": None, "client": None, "client_address": None,
        "date_issued": None, "due_date": None, "status": None,
        "items": [{"description": None, "qty": 1, "price": 1, "total": 1}],
        "subtotal": 1, "total": 1.19,
    })
    assert pdf.startswith(b"%PDF")


def test_a_supplier_bill_prints_the_supplier():
    """No database needed: the mapping alone decided the counterparty."""
    from app.models.invoicing import Invoice, InvoiceDirection, InvoiceStatus, Supplier
    from app.routers.invoicing import _pdf_data

    bill = Invoice(
        numero="FF-2026-0001", direction=InvoiceDirection.INCOMING, statut=InvoiceStatus.ENVOYEE,
        supplier=Supplier(nom="Tunisie Telecom", adresse="Tunis"), client=None,
        date_emission=date(2026, 10, 5), date_echeance=date(2026, 11, 5),
        montant_ht=Decimal(100), montant_ttc=Decimal(119), items=[],
    )
    data = _pdf_data(bill)
    assert (data["client"], data["client_address"]) == ("Tunisie Telecom", "Tunis")


def test_an_issued_invoice_prints_the_client():
    from app.models.invoicing import Client, Invoice, InvoiceDirection, InvoiceStatus
    from app.routers.invoicing import _pdf_data

    sale = Invoice(
        numero="FA-2026-0001", direction=InvoiceDirection.OUTGOING, statut=InvoiceStatus.BROUILLON,
        client=Client(nom="Acme Corporation", adresse="1 rue de Tunis"),
        date_emission=date(2026, 10, 5), date_echeance=date(2026, 11, 5),
        montant_ht=Decimal(100), montant_ttc=Decimal(119), items=[],
    )
    assert _pdf_data(sale)["client"] == "Acme Corporation"
