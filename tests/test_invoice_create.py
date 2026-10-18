"""Creating an invoice with real lines, and only once (#128).

The UI now sends every line as typed and an Idempotency-Key per opening of the
form. These pin the two server behaviours it relies on.
"""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.identity("admin")

LINES = [
    {"designation": "Consulting", "quantite": 2, "prix_unitaire": 500, "taux_tva": 19},
    {"designation": "Training", "quantite": 1, "prix_unitaire": 300, "taux_tva": 7},
    {"designation": "Travel", "quantite": 1, "prix_unitaire": 100, "taux_tva": 0},
]


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def a_client(client, admin):
    return client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "a@acme.tn",
        "telephone": "+216 70 000 000", "adresse": "1 rue de Tunis",
    }).json()["id"]


def create(client, admin, client_id, key=None, items=LINES):
    headers = {**admin, **({"Idempotency-Key": key} if key else {})}
    return client.post("/api/invoices", headers=headers, json={
        "client_id": client_id, "date_echeance": "2027-12-31", "items": items,
    })


def count_invoices(database):
    with database.connect() as c:
        return c.execute(text("SELECT count(*) FROM invoices")).scalar()


def test_every_line_is_kept_with_its_own_vat(client, admin, a_client):
    body = create(client, admin, a_client).json()
    assert [(i["description"], i["vatRate"]) for i in body["items"]] == [
        ("Consulting", 19), ("Training", 7), ("Travel", 0)]
    # HT 1000 + 300 + 100; TTC 1190 + 321 + 100.
    assert body["amountHT"] == pytest.approx(1400)
    assert body["amountTTC"] == pytest.approx(1611)


def test_the_same_key_creates_one_invoice(client, admin, a_client, database):
    """A double click or a retry must not take a second legal number."""
    first = create(client, admin, a_client, key="form-opening-1")
    again = create(client, admin, a_client, key="form-opening-1")
    assert first.status_code == again.status_code == 200
    assert again.json()["id"] == first.json()["id"]
    assert count_invoices(database) == 1


def test_different_keys_create_different_invoices(client, admin, a_client, database):
    a = create(client, admin, a_client, key="form-opening-1").json()["id"]
    b = create(client, admin, a_client, key="form-opening-2").json()["id"]
    assert a != b
    assert count_invoices(database) == 2


def test_a_new_invoice_is_a_draft_without_a_legal_number(client, admin, a_client):
    """Since #118 the number comes at approval; the draft shows BR- and its id."""
    body = create(client, admin, a_client).json()
    assert body["numero"] is None
    assert body["reference"] == f"BR-{int(body['id']):04d}"
    assert (body["status"], body["reviewStatus"]) == ("Draft", "Not submitted")


def test_a_due_date_in_the_past_is_refused(client, admin, a_client):
    response = client.post("/api/invoices", headers=admin, json={
        "client_id": a_client, "date_echeance": "2000-01-01", "items": LINES,
    })
    assert response.status_code == 422


# --- Line detail and unit (#194) ---------------------------------------------

DETAILED = [
    {"designation": "Development", "quantite": 12, "prix_unitaire": 350, "taux_tva": 19,
     "detail": "  Payroll module: leave balances and payslip PDF.\nTwo review rounds.  ", "unite": " days "},
    {"designation": "Hosting", "quantite": 1, "prix_unitaire": 90, "taux_tva": 19, "detail": "   ", "unite": ""},
]


def test_a_line_keeps_its_detail_and_unit(client, admin, a_client):
    items = create(client, admin, a_client, items=DETAILED).json()["items"]
    assert items[0]["detail"] == "Payroll module: leave balances and payslip PDF.\nTwo review rounds."
    assert items[0]["unit"] == "days"
    # Blank is nothing, not an empty line on the PDF.
    assert (items[1]["detail"], items[1]["unit"]) == (None, None)


def test_a_line_without_detail_or_unit_is_still_valid(client, admin, a_client):
    items = create(client, admin, a_client).json()["items"]
    assert all(i["detail"] is None and i["unit"] is None for i in items)


def test_correcting_a_draft_changes_its_detail_and_unit(client, admin, a_client):
    invoice_id = create(client, admin, a_client).json()["id"]
    response = client.patch(f"/api/invoices/{invoice_id}", headers=admin, json={
        "date_echeance": "2027-12-31",
        "items": [{**LINES[0], "detail": "Architecture review", "unite": "flat fee"}],
    })
    assert response.status_code == 200, response.text
    assert [(i["detail"], i["unit"]) for i in response.json()["items"]] == [("Architecture review", "flat fee")]


@pytest.mark.parametrize("field,size", [("detail", 1001), ("unite", 31)])
def test_a_detail_or_unit_too_long_is_refused_by_name(client, admin, a_client, field, size):
    response = create(client, admin, a_client, items=[{**LINES[0], field: "x" * size}])
    assert response.status_code == 422
    assert field in response.text


@pytest.mark.parametrize("field,size", [("detail", 1000), ("unite", 30)])
def test_a_detail_or_unit_at_the_limit_is_accepted(client, admin, a_client, field, size):
    assert create(client, admin, a_client, items=[{**LINES[0], field: "x" * size}]).status_code == 200


def test_the_database_caps_the_detail_too(database, client, admin, a_client):
    """The CHECK holds even for a write that skips the API."""
    invoice_id = create(client, admin, a_client).json()["id"]
    with pytest.raises(Exception, match="ck_invoice_items_detail"):
        with database.begin() as c:
            c.execute(text("UPDATE invoice_items SET detail = repeat('x', 1001) WHERE invoice_id = :i"),
                      {"i": invoice_id})
