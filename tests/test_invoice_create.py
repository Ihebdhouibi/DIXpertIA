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
    assert again.json()["numero"] == first.json()["numero"]
    assert count_invoices(database) == 1


def test_different_keys_create_different_invoices(client, admin, a_client, database):
    a = create(client, admin, a_client, key="form-opening-1").json()["numero"]
    b = create(client, admin, a_client, key="form-opening-2").json()["numero"]
    assert a != b
    assert count_invoices(database) == 2


def test_a_due_date_in_the_past_is_refused(client, admin, a_client):
    response = client.post("/api/invoices", headers=admin, json={
        "client_id": a_client, "date_echeance": "2000-01-01", "items": LINES,
    })
    assert response.status_code == 422
