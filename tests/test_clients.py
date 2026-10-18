"""Clients: created and corrected from the app, with the language their invoices print in (#192)."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.identity("admin")

ACME = {"nom": "Acme Corporation", "email": "billing@acme.tn", "telephone": "+216 70 000 000",
        "adresse": "1 rue de Tunis\n1000 Tunis"}


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


def create(client, headers, **changes):
    return client.post("/api/clients", headers=headers, json={**ACME, **changes})


# --- Creating ---------------------------------------------------------------

def test_a_client_is_created_trimmed_and_french_by_default(client, admin):
    response = create(client, admin, nom="  Acme Corporation  ", email=" billing@acme.tn ")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["nom"], body["email"], body["locale"]) == ("Acme Corporation", "billing@acme.tn", "fr")


def test_the_accountant_creates_clients_too(client, accountant):
    assert create(client, accountant, locale="en").json()["locale"] == "en"


@pytest.mark.parametrize("changes", [
    {"nom": ""},
    {"nom": "   "},
    {"nom": "x" * 151},
    {"email": "not-an-address"},
    {"telephone": "1" * 31},
    {"adresse": "x" * 501},
    {"locale": "de"},
])
def test_invalid_input_is_refused(client, admin, changes):
    assert create(client, admin, **changes).status_code == 422


def test_an_empty_email_is_allowed(client, admin):
    assert create(client, admin, email="").status_code == 200


def test_a_duplicate_name_is_409_not_500(client, admin):
    """ux_clients_nom_ci is case-insensitive; it used to surface as a 500."""
    create(client, admin)
    again = create(client, admin, nom="ACME CORPORATION")
    assert again.status_code == 409
    assert again.json()["code"] == "client.name_taken"


# --- Correcting -------------------------------------------------------------

def test_only_the_fields_sent_change(client, admin):
    client_id = create(client, admin).json()["id"]
    updated = client.patch(f"/api/clients/{client_id}", headers=admin,
                           json={"locale": "en", "telephone": " +216 71 111 111 "})
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert (body["locale"], body["telephone"], body["nom"], body["email"]) == (
        "en", "+216 71 111 111", ACME["nom"], ACME["email"])


def test_renaming_onto_another_client_is_409(client, admin):
    create(client, admin)
    other = create(client, admin, nom="Beta SARL").json()["id"]
    refused = client.patch(f"/api/clients/{other}", headers=admin, json={"nom": "acme corporation"})
    assert refused.status_code == 409 and refused.json()["code"] == "client.name_taken"


def test_an_unknown_client_is_404(client, admin):
    assert client.patch("/api/clients/999999", headers=admin, json={"locale": "en"}).status_code == 404


def test_the_employee_cannot_create_or_edit(client, admin, identities):
    client_id = create(client, admin).json()["id"]
    employee = identities["employee"]["headers"]
    assert create(client, employee, nom="Gamma").status_code == 403
    assert client.patch(f"/api/clients/{client_id}", headers=employee, json={"locale": "en"}).status_code == 403


# --- The language reaches the invoice ----------------------------------------

def test_switching_a_client_to_english_prints_its_invoice_in_english(client, admin):
    from invoice_flow import draft, pdf_text

    client_id = create(client, admin).json()["id"]
    invoice_id = draft(client, admin, client_id).json()["id"]
    before = pdf_text(client.get(f"/api/invoices/{invoice_id}/download", headers=admin).content)
    client.patch(f"/api/clients/{client_id}", headers=admin, json={"locale": "en"})
    after = pdf_text(client.get(f"/api/invoices/{invoice_id}/download", headers=admin).content)
    assert b"FACTURE" in before and b"FACTURE" not in after
    assert b"INVOICE" in after


# --- The audit trail --------------------------------------------------------

def test_creation_and_changes_are_audited(client, admin, database):
    client_id = create(client, admin).json()["id"]
    client.patch(f"/api/clients/{client_id}", headers=admin, json={"locale": "en"})
    client.patch(f"/api/clients/{client_id}", headers=admin, json={"locale": "en"})  # no change: no event
    with database.connect() as c:
        rows = c.execute(text(
            "SELECT action, before, after FROM audit_events WHERE entity = 'client' AND entity_id = :i ORDER BY id"),
            {"i": str(client_id)}).all()
    assert [r.action for r in rows] == ["client.created", "client.updated"]
    assert rows[1].before == {"locale": "fr"} and rows[1].after == {"locale": "en"}
