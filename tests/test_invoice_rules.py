"""The accountant's mandatory rules, as tests rather than manual scripts (#57).

Each of these was agreed with the accountant and enforced in the database so
that a direct SQL write cannot bypass it. They are tested through the API where
the API is the way in, and through SQL where the point is that SQL cannot get
round them.

Several assert that something is **accepted**. Those matter as much as the
refusals: they are what shows a rule is targeted rather than a blanket freeze.
A rule that refuses everything passes every refusal test and is still wrong.
"""

import pytest
from sqlalchemy import text

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


@pytest.fixture
def a_supplier(client, admin):
    return client.post("/api/suppliers", headers=admin, json={
        "nom": "Tunisie Telecom", "email": "f@tt.tn",
        "telephone": "+216 71 000 000", "adresse": "Tunis",
    }).json()["id"]


def issue(client, admin, client_id, amount=1000):
    return client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1,
                   "prix_unitaire": amount, "taux_tva": 19}],
    })


# --- #38: the series is gapless -------------------------------------------

def test_numbers_start_at_one_and_increment(client, admin, a_client):
    numbers = [issue(client, admin, a_client).json()["numero"] for _ in range(3)]
    year = numbers[0][3:7]
    assert numbers == [f"FA-{year}-0001", f"FA-{year}-0002", f"FA-{year}-0003"]


def test_an_invoice_cannot_be_deleted(client, admin, a_client, database):
    """Deleting one would leave a hole in the series, so it is refused outright.

    An invoice issued in error is cancelled - the row and its number stay, with
    statut ANNULEE - and corrected by a credit note.
    """
    numero = issue(client, admin, a_client).json()["numero"]
    with database.connect() as c:
        with pytest.raises(Exception, match="gapless series"):
            c.execute(text("DELETE FROM invoices WHERE numero = :n"), {"n": numero})


def test_a_hand_written_number_cannot_skip_ahead(client, admin, a_client, database,
                                                 identities):
    issue(client, admin, a_client)
    year = __import__("datetime").date.today().year
    with database.connect() as c:
        with pytest.raises(Exception, match="breaks the FA series"):
            c.execute(text(
                "INSERT INTO invoices (numero, direction, client_id, date_emission,"
                " date_echeance, montant_ht, montant_ttc, statut, cree_par_id)"
                " VALUES (:n, 'OUTGOING', :c, CURRENT_DATE, CURRENT_DATE, 10, 12,"
                " 'BROUILLON', :u)"),
                {"n": f"FA-{year}-0099", "c": a_client,
                 "u": identities["admin"]["user_id"]})


def test_concurrent_creates_take_distinct_numbers(client, admin, a_client):
    """The old COUNT(*) + 1 gave two concurrent creates the same number.

    Not true concurrency - TestClient is serial - but it does prove the counter
    advances per create rather than being derived from a row count, which is
    the property that made the old code collide.
    """
    numbers = [issue(client, admin, a_client).json()["numero"] for _ in range(8)]
    assert len(set(numbers)) == 8


# --- #39: numbers follow issue dates --------------------------------------

def test_two_invoices_may_share_a_date(client, admin, a_client):
    """Several invoices a day is routine, so the rule is 'not earlier than'."""
    first = issue(client, admin, a_client)
    second = issue(client, admin, a_client)
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["dateIssued"] == second.json()["dateIssued"]


def test_an_issue_date_cannot_move_before_a_lower_number(client, admin, a_client,
                                                         database):
    issue(client, admin, a_client)
    second = issue(client, admin, a_client).json()["numero"]
    with database.connect() as c:
        with pytest.raises(Exception, match="must follow issue dates"):
            c.execute(text(
                "UPDATE invoices SET date_emission = '2020-01-01' WHERE numero = :n"),
                {"n": second})


# --- #40: income and expense are separate ----------------------------------

def test_sales_and_purchases_use_separate_series(client, admin, a_client, a_supplier):
    sale = issue(client, admin, a_client).json()["numero"]
    bill = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": a_supplier, "supplier_reference": "TT-001",
        "date_emission": "2026-10-05", "date_echeance": "2026-11-05",
        "montant_ht": 100, "montant_ttc": 119, "items": [],
    }).json()["numero"]
    assert sale.startswith("FA-") and bill.startswith("FF-")
    assert sale[7:] == bill[7:] == "-0001", "each series starts at 1 independently"


def test_the_same_bill_cannot_be_entered_twice(client, admin, a_supplier):
    """Entering it twice is how an invoice gets paid twice."""
    body = {"supplier_id": a_supplier, "supplier_reference": "DUP-1",
            "date_emission": "2026-10-05", "date_echeance": "2026-11-05",
            "montant_ht": 100, "montant_ttc": 119, "items": []}
    assert client.post("/api/supplier-invoices", headers=admin, json=body).status_code == 201
    again = client.post("/api/supplier-invoices", headers=admin, json=body)
    assert again.status_code == 409
    assert "already been recorded" in again.json()["detail"]


def test_two_suppliers_may_use_the_same_reference(client, admin, a_supplier):
    """"2026-001" is an ordinary house number. Uniqueness is per supplier."""
    other = client.post("/api/suppliers", headers=admin,
                        json={"nom": "STEG"}).json()["id"]
    body = {"supplier_reference": "2026-001", "date_emission": "2026-10-05",
            "date_echeance": "2026-11-05", "montant_ht": 100,
            "montant_ttc": 119, "items": []}
    first = client.post("/api/supplier-invoices", headers=admin,
                        json={**body, "supplier_id": a_supplier})
    second = client.post("/api/supplier-invoices", headers=admin,
                         json={**body, "supplier_id": other})
    assert first.status_code == 201 and second.status_code == 201


def test_a_supplier_bill_may_be_booked_out_of_date_order(client, admin, a_supplier):
    """Bills arrive out of order by nature; #39 applies to the sales series only."""
    late = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": a_supplier, "supplier_reference": "LATE",
        "date_emission": "2026-10-20", "date_echeance": "2026-11-20",
        "montant_ht": 100, "montant_ttc": 119, "items": []})
    earlier = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": a_supplier, "supplier_reference": "EARLIER",
        "date_emission": "2026-10-03", "date_echeance": "2026-11-03",
        "montant_ht": 100, "montant_ttc": 119, "items": []})
    assert late.status_code == 201
    assert earlier.status_code == 201, "a bill dated earlier must still be bookable"


# --- #41 and #42: the monthly close ----------------------------------------

def test_closing_is_refused_while_an_invoice_is_unfinished(client, admin, a_client):
    issue(client, admin, a_client)
    month = __import__("datetime").date.today().strftime("%Y-%m")
    response = client.post(f"/api/periods/{month}/close", headers=admin)
    assert response.status_code == 409
    assert response.json()["blocking"], "the refusal must name what is blocking it"


def test_closing_archives_the_month_and_is_final(client, admin, a_client, database):
    numero = issue(client, admin, a_client).json()["numero"]
    invoice_id = client.get("/api/invoices", headers=admin).json()[0]["id"]
    for state in ("processed", "completed"):
        client.patch(f"/api/invoices/{invoice_id}/processing-status",
                     headers=admin, json={"processing_status": state})

    month = __import__("datetime").date.today().strftime("%Y-%m")
    closed = client.post(f"/api/periods/{month}/close", headers=admin)
    assert closed.status_code == 200
    assert closed.json()["state"] == "closed"

    again = client.post(f"/api/periods/{month}/close", headers=admin)
    assert again.status_code == 409, "a closed month must not reopen"

    moved_back = client.patch(f"/api/invoices/{invoice_id}/processing-status",
                              headers=admin, json={"processing_status": "pending"})
    assert moved_back.status_code == 409, "archived is terminal"

    with database.connect() as c:
        with pytest.raises(Exception, match="is closed"):
            c.execute(text(
                "INSERT INTO invoices (numero, direction, client_id, date_emission,"
                " date_echeance, montant_ht, montant_ttc, statut, cree_par_id)"
                " SELECT 'FA-9999-0001', 'OUTGOING', client_id, date_emission,"
                " date_echeance, 10, 12, 'BROUILLON', cree_par_id"
                " FROM invoices WHERE numero = :n"), {"n": numero})


def test_a_client_may_still_pay_an_archived_invoice(client, admin, a_client, database):
    """The two status axes are independent: the commercial state keeps moving."""
    issue(client, admin, a_client)
    invoice_id = client.get("/api/invoices", headers=admin).json()[0]["id"]
    for state in ("processed", "completed"):
        client.patch(f"/api/invoices/{invoice_id}/processing-status",
                     headers=admin, json={"processing_status": state})
    month = __import__("datetime").date.today().strftime("%Y-%m")
    client.post(f"/api/periods/{month}/close", headers=admin)

    with database.connect() as c:
        c.execute(text("UPDATE invoices SET statut = 'PAYEE' WHERE id = :i"),
                  {"i": invoice_id})
        row = c.execute(text(
            "SELECT statut, processing_status FROM invoices WHERE id = :i"),
            {"i": invoice_id}).first()
    assert (row[0], row[1]) == ("PAYEE", "ARCHIVED")
