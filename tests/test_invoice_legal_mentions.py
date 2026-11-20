"""The legal mentions on an invoice we issue (#189).

Tunisian law requires them for the invoice to be valid in the client's books:
the seller's matricule fiscal and RNE, a business client's matricule fiscal,
and the stamp duty (droit de timbre) on an invoice to a client in Tunisia.

The stamp duty is stored on the invoice when a draft is created or edited,
then fixed with its totals: a new rate never changes an issued invoice. An
invoice missing a mandatory mention cannot be approved, and the error says
what to complete.
"""

from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from invoice_flow import approve, draft, pdf_text, submit

pytestmark = pytest.mark.identity("admin")

TUNIS = {"nom": "Acme Tunisie", "adresse": "1 rue de Tunis"}
BUSINESS = {**TUNIS, "entreprise": True, "identifiant_fiscal": "1234567A/A/M/000"}
ABROAD = {"nom": "Example Retail Ltd", "adresse": "10 Market Street\nLondon", "locale": "en",
          "export": True, "devise": "USD", "entreprise": True}


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


def make_client(client, admin, **body):
    response = client.post("/api/clients", headers=admin, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def new_draft(client, admin, client_id, rate=19):
    response = client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1, "prix_unitaire": 1000, "taux_tva": rate}],
    })
    assert response.status_code == 200, response.text
    return response.json()


def approval(client, identities, invoice_id):
    """Submit as the admin, then ask the accountant to approve; returns the answer."""
    assert submit(client, identities, invoice_id).status_code == 200
    return client.post(f"/api/invoices/{invoice_id}/approve", headers=identities["accountant"]["headers"])


# --- The stamp duty ---------------------------------------------------------------------

def test_an_invoice_to_a_client_in_tunisia_carries_the_stamp_duty(client, admin):
    invoice = new_draft(client, admin, make_client(client, admin, **BUSINESS)["id"])
    assert invoice["amountTTC"] == pytest.approx(1190)
    assert invoice["stampDuty"] == pytest.approx(1)
    assert invoice["amountDue"] == pytest.approx(1191)


def test_an_export_invoice_carries_none(client, admin):
    invoice = new_draft(client, admin, make_client(client, admin, **ABROAD)["id"], rate=0)
    assert invoice["stampDuty"] == 0
    assert invoice["amountDue"] == invoice["amountTTC"] == pytest.approx(1000)


def test_a_new_rate_applies_to_drafts_and_never_to_an_issued_invoice(client, admin, identities, monkeypatch):
    from app.core.config import settings

    customer = make_client(client, admin, **BUSINESS)["id"]
    issued = approve(client, identities, new_draft(client, admin, customer)["id"])
    pending = new_draft(client, admin, customer)

    monkeypatch.setattr(settings, "STAMP_DUTY_AMOUNT", Decimal("2.500"))
    assert new_draft(client, admin, customer)["stampDuty"] == pytest.approx(2.5)
    # A draft takes the rate in force when it is edited.
    edited = client.patch(f"/api/invoices/{pending['id']}", headers=admin, json={
        "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1, "prix_unitaire": 1000, "taux_tva": 19}],
    })
    assert edited.status_code == 200, edited.text
    assert edited.json()["stampDuty"] == pytest.approx(2.5)
    again = client.get(f"/api/invoices/{issued['id']}", headers=admin).json()
    assert again["stampDuty"] == pytest.approx(1) and again["amountDue"] == pytest.approx(1191)


def test_the_database_fixes_the_stamp_duty_once_submitted(client, admin, identities, database):
    invoice = new_draft(client, admin, make_client(client, admin, **BUSINESS)["id"])
    assert submit(client, identities, invoice["id"]).status_code == 200
    with pytest.raises(DBAPIError, match="cannot be edited"):
        with database.begin() as c:
            c.execute(text("UPDATE invoices SET droit_timbre = 0 WHERE id = :i"), {"i": int(invoice["id"])})


def test_the_database_refuses_a_stamp_duty_on_an_export_invoice(client, admin, database):
    invoice = new_draft(client, admin, make_client(client, admin, **ABROAD)["id"], rate=0)
    with pytest.raises(DBAPIError, match="ck_invoices_stamp_duty"):
        with database.begin() as c:
            c.execute(text("UPDATE invoices SET droit_timbre = 1 WHERE id = :i"), {"i": int(invoice["id"])})


def test_the_pdf_prints_the_stamp_duty_and_adds_it_to_the_amount_due(client, admin):
    invoice = new_draft(client, admin, make_client(client, admin, **BUSINESS, locale="en")["id"])
    pdf = pdf_text(client.get(f"/api/invoices/{invoice['id']}/download", headers=admin).content)
    assert b"Stamp duty" in pdf and b"1.000" in pdf
    assert pdf.index(b"VAT 19") < pdf.index(b"Stamp duty") < pdf.index(b"TOTAL DUE")
    assert b"TOTAL DUE 1,191.000 TND" in pdf
    assert b"one thousand one hundred ninety-one dinars" in pdf


def test_the_french_pdf_reads_droit_de_timbre(client, admin):
    invoice = new_draft(client, admin, make_client(client, admin, **BUSINESS)["id"])
    pdf = pdf_text(client.get(f"/api/invoices/{invoice['id']}/download", headers=admin).content)
    assert b"Droit de timbre" in pdf
    assert "NET À PAYER 1 191,000 TND".encode() in pdf


def test_an_export_pdf_has_no_stamp_duty_row(client, admin):
    invoice = new_draft(client, admin, make_client(client, admin, **ABROAD)["id"], rate=0)
    pdf = pdf_text(client.get(f"/api/invoices/{invoice['id']}/download", headers=admin).content)
    assert b"Stamp duty" not in pdf
    assert b"TOTAL DUE 1,000.00 USD" in pdf


def test_the_list_sorts_on_the_amount_due(client, admin):
    """An export invoice of 1000 and a domestic one of 1000 at 0% VAT: the stamp duty decides."""
    abroad = new_draft(client, admin, make_client(client, admin, **ABROAD)["id"], rate=0)
    domestic = new_draft(client, admin, make_client(client, admin, **BUSINESS)["id"], rate=0)
    listed = [row["id"] for row in client.get("/api/invoices", headers=admin, params={"sort": "-amount"}).json()]
    assert listed.index(domestic["id"]) < listed.index(abroad["id"])


# --- The client's matricule fiscal ------------------------------------------------------

def test_a_business_in_tunisia_needs_its_tax_id(client, admin):
    response = client.post("/api/clients", headers=admin, json={**TUNIS, "entreprise": True})
    assert response.status_code == 422
    assert response.json()["code"] == "client.tax_id_required"
    blank = client.post("/api/clients", headers=admin, json={**TUNIS, "entreprise": True, "identifiant_fiscal": "  "})
    assert blank.status_code == 422


def test_a_private_person_or_a_business_abroad_does_not(client, admin):
    person = make_client(client, admin, **TUNIS)
    assert (person["entreprise"], person["identifiant_fiscal"]) == (False, None)
    assert make_client(client, admin, **ABROAD)["identifiant_fiscal"] is None


def test_a_business_with_its_tax_id_is_saved(client, admin):
    body = make_client(client, admin, **BUSINESS)
    assert (body["entreprise"], body["identifiant_fiscal"]) == (True, "1234567A/A/M/000")


@pytest.mark.parametrize("start,changes", [
    # A private person becomes a business.
    ({}, {"entreprise": True}),
    # A business loses its tax ID.
    ({"entreprise": True, "identifiant_fiscal": "1234567A/A/M/000"}, {"identifiant_fiscal": ""}),
    # A business abroad moves to Tunisia.
    ({"entreprise": True, "export": True, "devise": "USD"}, {"export": False, "devise": "TND"}),
])
def test_an_update_cannot_leave_a_business_in_tunisia_without_its_tax_id(client, admin, start, changes):
    """The rule holds on the client as it would be, not only on the fields sent."""
    customer = make_client(client, admin, **TUNIS, **start)
    response = client.patch(f"/api/clients/{customer['id']}", headers=admin, json=changes)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "client.tax_id_required"


# --- Approval -----------------------------------------------------------------------------

@pytest.mark.parametrize("setting,words", [("SELLER_TAX_ID", "our tax ID"), ("SELLER_RNE", "our trade register")])
def test_an_invoice_is_not_approved_without_our_identification(client, admin, identities, monkeypatch,
                                                              setting, words):
    from app.core.config import settings

    invoice = new_draft(client, admin, make_client(client, admin, **BUSINESS)["id"])
    monkeypatch.setattr(settings, setting, "")
    response = approval(client, identities, invoice["id"])
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "invoice.missing_legal_mentions"
    assert words in response.json()["detail"]
    # Not numbered: the series has no gap to explain.
    again = client.get(f"/api/invoices/{invoice['id']}", headers=admin).json()
    assert again["numero"] is None and again["reviewStatus"] == "Submitted"


def test_an_invoice_to_a_business_without_its_tax_id_is_not_approved(client, admin, identities, database):
    customer = make_client(client, admin, **TUNIS)
    invoice = new_draft(client, admin, customer["id"])
    # A client recorded before the rule: the database lets it be, approval does not.
    with database.begin() as c:
        c.execute(text("UPDATE clients SET entreprise = true WHERE id = :i"), {"i": customer["id"]})
    response = approval(client, identities, invoice["id"])
    assert response.status_code == 409
    assert "the client's tax ID" in response.json()["detail"]

    fixed = client.patch(f"/api/clients/{customer['id']}", headers=admin,
                         json={"identifiant_fiscal": "1234567A/A/M/000"})
    assert fixed.status_code == 200, fixed.text
    approved = client.post(f"/api/invoices/{invoice['id']}/approve", headers=identities["accountant"]["headers"])
    assert approved.status_code == 200, approved.text
    assert approved.json()["numero"]


def test_the_message_names_every_missing_mention_in_french(client, admin, identities, monkeypatch, database):
    from app.core.config import settings

    customer = make_client(client, admin, **TUNIS)
    invoice = new_draft(client, admin, customer["id"])
    with database.begin() as c:
        c.execute(text("UPDATE clients SET entreprise = true WHERE id = :i"), {"i": customer["id"]})
    monkeypatch.setattr(settings, "SELLER_TAX_ID", "")
    monkeypatch.setattr(settings, "SELLER_RNE", "")
    assert submit(client, identities, invoice["id"]).status_code == 200
    response = client.post(f"/api/invoices/{invoice['id']}/approve",
                           headers={**identities["accountant"]["headers"], "Accept-Language": "fr"})
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "notre matricule fiscal" in detail and "notre numéro RNE" in detail
    assert "le matricule fiscal du client" in detail


def test_a_private_person_and_an_export_client_are_approved(client, admin, identities):
    for body, rate in ((TUNIS, 19), (ABROAD, 0)):
        invoice = new_draft(client, admin, make_client(client, admin, **body)["id"], rate=rate)
        assert approval(client, identities, invoice["id"]).status_code == 200


def test_the_flow_helpers_still_approve(client, admin, identities):
    """invoice_flow's draft() uses a plain client: approval passes with our details set."""
    customer = make_client(client, admin, **TUNIS)["id"]
    created = draft(client, admin, customer)
    assert created.status_code == 200
    assert approve(client, identities, created.json()["id"])["numero"]
