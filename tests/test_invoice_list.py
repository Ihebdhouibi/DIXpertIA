"""Sorting the invoice list on the server (#113).

The list is paginated, so the order has to be decided by the query: sorting one
page in the browser would rank 50 rows out of thousands and show a wrong
"largest invoice". These tests pin the accepted orders, their direction, the
stable tie-break across pages, and the refusal of anything else.
"""

import pytest

pytestmark = pytest.mark.identity("admin")


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def a_client(client, admin):
    return client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "a@acme.tn",
        "telephone": "+216 70 000 000", "adresse": "1 rue de Tunis",
    }).json()["id"]


def issue(client, admin, client_id, amount):
    response = client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1,
                   "prix_unitaire": amount, "taux_tva": 19}],
    })
    assert response.status_code in (200, 201), response.text
    return response.json()


def amounts(client, admin, **params):
    response = client.get("/api/invoices", headers=admin, params=params)
    assert response.status_code == 200, response.text
    return [row["amountTTC"] for row in response.json()]


def test_sort_by_amount_both_directions(client, admin, a_client):
    for amount in (500, 3000, 1200):
        issue(client, admin, a_client, amount)
    ascending = amounts(client, admin, sort="amount")
    descending = amounts(client, admin, sort="-amount")
    assert ascending == sorted(ascending) and len(ascending) == 3
    assert descending == sorted(descending, reverse=True)
    assert ascending == list(reversed(descending))


def test_sort_applies_before_pagination(client, admin, a_client):
    """The largest invoice is on page one, wherever it was created."""
    for amount in (100, 200, 9000, 300):
        issue(client, admin, a_client, amount)
    first_page = amounts(client, admin, sort="-amount", limit=2, offset=0)
    second_page = amounts(client, admin, sort="-amount", limit=2, offset=2)
    assert first_page[0] == max(first_page + second_page)
    assert first_page + second_page == sorted(first_page + second_page, reverse=True)


def test_default_order_is_newest_first(client, admin, a_client):
    """Invoices issued the same day fall back on id: the latest one first."""
    created = [issue(client, admin, a_client, amount)["id"] for amount in (100, 200, 300)]
    response = client.get("/api/invoices", headers=admin)
    listed = [row["id"] for row in response.json()]
    assert listed == list(reversed(created))


def test_ties_are_stable_across_pages(client, admin, a_client):
    """Equal amounts tie-break on id, so paging neither repeats nor skips a row."""
    for _ in range(5):
        issue(client, admin, a_client, 1000)
    pages = [
        [row["id"] for row in client.get(
            "/api/invoices", headers=admin, params={"sort": "amount", "limit": 2, "offset": offset},
        ).json()]
        for offset in (0, 2, 4)
    ]
    seen = [i for page in pages for i in page]
    assert len(seen) == len(set(seen)) == 5


@pytest.mark.parametrize("bad", ["montant_ttc", "id", "amount;drop", "DATE"])
def test_unknown_sort_is_refused(client, admin, bad):
    """Only the closed list is accepted: no sorting on arbitrary columns."""
    response = client.get("/api/invoices", headers=admin, params={"sort": bad})
    assert response.status_code == 422
