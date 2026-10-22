"""The dashboard's figures, computed by the server (#120).

The dashboard used to add up the lists it had loaded: at most 200 invoices,
50 leave requests and 50 employees. Past those caps every figure was partial.
These tests pin the replacement: exact past the old cap, a count and its amount
taken from the same rows, Overdue derived as in the list (#117), each block
present only for the roles that see it, and the month filter.

Supplier bills make the invoices: they carry their own dates and need no
approval round, so a few hundred cost one request each.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import text

from invoice_flow import draft

pytestmark = pytest.mark.identity("admin")

TODAY = date.today()
URL = "/api/dashboard/summary"


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


@pytest.fixture
def bill(client, admin, accountant):
    supplier = client.post("/api/suppliers", headers=admin, json={"nom": "Fournisseur SA"}).json()["id"]
    counter = iter(range(1, 10_000))

    def make(ttc=119, issued=TODAY - timedelta(days=40), due=TODAY + timedelta(days=30)):
        response = client.post("/api/supplier-invoices", headers=accountant, json={
            "supplier_id": supplier, "supplier_reference": f"S-{next(counter):05d}",
            "date_emission": issued.isoformat(), "date_echeance": due.isoformat(),
            "montant_ht": round(ttc / 1.19, 3), "montant_ttc": ttc, "items": []})
        assert response.status_code == 201, response.text
        return response.json()
    return make


def summary(client, headers, **params):
    response = client.get(URL, headers=headers, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def by_status(figures):
    return {s["status"]: s for s in figures["byStatus"]}


def test_exact_past_the_old_200_invoice_cap(client, admin, bill):
    """205 invoices: the old dashboard summed 200 of them and said so."""
    for _ in range(205):
        bill(ttc=10)
    invoices = summary(client, admin)["invoices"]
    assert invoices["count"] == 205
    # Since #195 each total also comes per currency, in `amounts`.
    assert invoices["suppliers"] == {"count": 205, "amount": pytest.approx(2050),
                                     "amounts": [{"currency": "TND", "amount": pytest.approx(2050)}]}


def test_counts_and_amounts_come_from_the_same_rows(client, admin, bill):
    for ttc in (100, 250.5, 1000):
        bill(ttc=ttc)
    invoices = summary(client, admin)["invoices"]
    assert invoices["count"] == sum(s["count"] for s in invoices["byStatus"])
    assert invoices["suppliers"]["amount"] == pytest.approx(sum(s["amount"] for s in invoices["byStatus"]))
    assert invoices["count"] == sum(p["count"] for p in invoices["byProcessing"])
    assert invoices["suppliers"]["amount"] == pytest.approx(1350.5)


def test_every_status_is_listed_in_order_zeros_included(client, admin):
    invoices = summary(client, admin)["invoices"]
    assert [s["status"] for s in invoices["byStatus"]] == ["Draft", "Sent", "Paid", "Overdue", "Cancelled"]
    assert [p["status"] for p in invoices["byProcessing"]] == ["Pending", "Processed", "Completed", "Archived"]
    assert invoices["count"] == 0
    assert invoices["clients"] == invoices["suppliers"] == {"count": 0, "amount": 0, "amounts": []}


def test_overdue_is_derived_as_in_the_invoice_list(client, admin, bill, database):
    bill(ttc=100, due=TODAY - timedelta(days=1))
    bill(ttc=200, due=TODAY)
    statuses = by_status(summary(client, admin)["invoices"])
    assert (statuses["Overdue"]["count"], statuses["Overdue"]["amount"]) == (1, pytest.approx(100))
    assert (statuses["Sent"]["count"], statuses["Sent"]["amount"]) == (1, pytest.approx(200))

    listed = client.get("/api/invoices", headers=admin, params={"statut": "en_retard"}).json()
    assert len(listed) == statuses["Overdue"]["count"], "the dashboard and the list agree"


def test_month_filter_counts_that_month_only(client, admin, bill):
    bill(ttc=100, issued=date(2026, 3, 1))
    bill(ttc=200, issued=date(2026, 3, 31))
    bill(ttc=400, issued=date(2026, 4, 1))
    march = summary(client, admin, month="2026-03")
    assert march["month"] == "2026-03"
    assert march["invoices"]["count"] == 2
    assert march["invoices"]["suppliers"]["amount"] == pytest.approx(300)
    assert summary(client, admin, month="2026-12")["invoices"]["count"] == 0
    assert summary(client, admin)["invoices"]["count"] == 3


def test_client_and_supplier_totals_are_kept_apart(client, admin, bill):
    """Income and expenses: two totals, never one sum (#40)."""
    customer = client.post("/api/clients", headers=admin, json={
        "nom": "Acme Corporation", "email": "a@acme.tn",
        "telephone": "+216 70 000 000", "adresse": "1 rue de Tunis",
    }).json()["id"]
    for amount in (1000, 500):
        assert draft(client, admin, customer, amount).status_code == 200
    bill(ttc=119)
    invoices = summary(client, admin)["invoices"]
    tnd = [{"currency": "TND", "amount": pytest.approx(1785)}]
    assert invoices["clients"] == {"count": 2, "amount": pytest.approx(1785), "amounts": tnd}, "1500 HT at 19% VAT"
    assert invoices["suppliers"] == {"count": 1, "amount": pytest.approx(119),
                                     "amounts": [{"currency": "TND", "amount": pytest.approx(119)}]}
    assert invoices["count"] == 3


@pytest.mark.parametrize("month", ["2026-13", "2026-1", "march", "2026-00"])
def test_a_malformed_month_is_refused(client, admin, month):
    assert client.get(URL, headers=admin, params={"month": month}).status_code == 422


@pytest.mark.identity("accountant")
def test_the_accountant_sees_invoices_but_not_the_team(client, accountant, bill):
    bill(ttc=100)
    body = summary(client, accountant)
    assert body["invoices"]["count"] == 1
    assert body["team"] is None


@pytest.mark.identity("employee")
def test_an_employee_gets_no_invoice_or_team_block(client, identities):
    body = summary(client, identities["employee"]["headers"])
    assert body["invoices"] is None, "null, not zeros: invoices are not theirs to see (#55)"
    assert body["team"] is None


def test_the_admin_sees_the_whole_team(client, admin, database):
    with database.connect() as c:
        total, active = c.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE employment_status = 'ACTIVE') FROM employees")).one()
    assert summary(client, admin)["team"] == {"active": active, "total": total}


@pytest.fixture
def pending_for_everyone(database, identities):
    """Two pending requests and one approved for each fixture employee.

    A decision names who made it, and nobody decides their own: the admin
    approves everyone's, the accountant the admin's.
    """
    admin, accountant = identities["admin"]["user_id"], identities["accountant"]["user_id"]
    with database.connect() as c:
        rows = c.execute(text("SELECT id, user_id FROM employees")).all()
        for employee_id, user_id in rows:
            decider = accountant if user_id == admin else admin
            for statut in ("EN_ATTENTE", "EN_ATTENTE", "APPROUVE"):
                c.execute(text(
                    "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut, valide_par_id)"
                    " VALUES (:e, '2026-03-10', '2026-03-12', 'PAYE', :s, :v)"),
                    {"e": employee_id, "s": statut, "v": None if statut == "EN_ATTENTE" else decider})
    return len(rows)


def test_the_admin_counts_everyone_s_pending_leave(client, admin, pending_for_everyone):
    assert summary(client, admin)["leave"]["pending"] == 2 * pending_for_everyone


@pytest.mark.identity("employee")
def test_an_employee_counts_only_their_own_pending_leave(client, identities, pending_for_everyone):
    assert summary(client, identities["employee"]["headers"])["leave"]["pending"] == 2


def test_signed_out_is_refused(client):
    assert client.get(URL).status_code in (401, 403)
