"""Export clients and the invoice currency (#195).

A client abroad is billed for an export of services: no Tunisian VAT (Code de
la TVA, art. 3-I and 11-I), in their own currency. For this release an export
client always pays in a foreign currency.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = pytest.mark.identity("admin")

ABROAD = {"nom": "Example Retail Ltd", "adresse": "10 Market Street\nLondon", "locale": "en",
          "export": True, "devise": "USD", "identifiant_fiscal": " GB 123456789 "}
LOCAL = {"nom": "Acme Tunisie", "adresse": "1 rue de Tunis"}


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


def make_client(client, admin, **body):
    response = client.post("/api/clients", headers=admin, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def invoice(client, admin, client_id, rate=0, **extra):
    return client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 2, "prix_unitaire": 1000, "taux_tva": rate}],
        **extra,
    })


# --- Clients ----------------------------------------------------------------------------

def test_a_client_is_domestic_in_dinars_by_default(client, admin):
    body = make_client(client, admin, **LOCAL)
    assert (body["export"], body["devise"], body["identifiant_fiscal"]) == (False, "TND", None)


def test_an_export_client_keeps_its_currency_and_tax_id(client, admin):
    body = make_client(client, admin, **ABROAD)
    assert (body["export"], body["devise"], body["identifiant_fiscal"]) == (True, "USD", "GB 123456789")


def test_an_export_client_in_dinars_is_refused(client, admin):
    response = client.post("/api/clients", headers=admin, json={**ABROAD, "devise": "TND"})
    assert response.status_code == 422
    assert "foreign currency" in response.text


@pytest.mark.parametrize("changes", [{"devise": "CHF"}, {"identifiant_fiscal": "x" * 51}])
def test_an_unknown_currency_or_a_long_tax_id_is_refused(client, admin, changes):
    assert client.post("/api/clients", headers=admin, json={**ABROAD, **changes}).status_code == 422


def test_the_rule_holds_on_the_client_as_it_will_be(client, admin):
    """Flagging a TND client as export, without changing its currency, is refused."""
    local = make_client(client, admin, **LOCAL)
    response = client.patch(f"/api/clients/{local['id']}", headers=admin, json={"export": True})
    assert response.status_code == 422
    moved = client.patch(f"/api/clients/{local['id']}", headers=admin, json={"export": True, "devise": "EUR"})
    assert moved.status_code == 200 and (moved.json()["export"], moved.json()["devise"]) == (True, "EUR")
    # Back to TND while still export: refused too.
    assert client.patch(f"/api/clients/{local['id']}", headers=admin, json={"devise": "TND"}).status_code == 422


def test_a_tax_id_can_be_cleared(client, admin):
    abroad = make_client(client, admin, **ABROAD)
    body = client.patch(f"/api/clients/{abroad['id']}", headers=admin, json={"identifiant_fiscal": "  "}).json()
    assert body["identifiant_fiscal"] is None


# --- Invoices ---------------------------------------------------------------------------

def test_an_export_invoice_takes_the_clients_currency(client, admin):
    abroad = make_client(client, admin, **ABROAD)
    body = invoice(client, admin, abroad["id"]).json()
    assert (body["currency"], body["export"]) == ("USD", True)
    assert body["amountHT"] == body["amountTTC"] == pytest.approx(2000)


def test_a_domestic_invoice_is_unchanged(client, admin):
    local = make_client(client, admin, **LOCAL)
    body = invoice(client, admin, local["id"], rate=19).json()
    assert (body["currency"], body["export"]) == ("TND", False)
    assert body["amountTTC"] == pytest.approx(2380)


def test_vat_on_an_export_invoice_is_refused_with_its_line(client, admin):
    abroad = make_client(client, admin, **ABROAD)
    response = invoice(client, admin, abroad["id"], rate=19)
    assert response.status_code == 422
    assert "Line 1" in response.text or "Ligne 1" in response.text


def test_correcting_an_export_draft_keeps_the_rule(client, admin):
    abroad = make_client(client, admin, **ABROAD)
    draft = invoice(client, admin, abroad["id"]).json()
    response = client.patch(f"/api/invoices/{draft['id']}", headers=admin, json={
        "date_echeance": "2027-12-31",
        "items": [{"designation": "Audit", "quantite": 1, "prix_unitaire": 500, "taux_tva": 0},
                  {"designation": "Travel", "quantite": 1, "prix_unitaire": 50, "taux_tva": 7}],
    })
    assert response.status_code == 422 and ("Line 2" in response.text or "Ligne 2" in response.text)


def test_an_invoice_keeps_its_currency_when_the_client_changes(client, admin):
    """An invoice reprints as issued: the client record moving on does not move it."""
    abroad = make_client(client, admin, **ABROAD)
    draft = invoice(client, admin, abroad["id"]).json()
    client.patch(f"/api/clients/{abroad['id']}", headers=admin, json={"devise": "EUR"})
    body = client.get(f"/api/invoices/{draft['id']}", headers=admin).json()
    assert (body["currency"], body["export"]) == ("USD", True)


def test_an_unknown_client_is_404(client, admin):
    assert invoice(client, admin, 999999).status_code == 404


def test_the_currency_and_export_flag_are_audited(client, admin, database):
    abroad = make_client(client, admin, **ABROAD)
    invoice_id = int(invoice(client, admin, abroad["id"]).json()["id"])
    with database.connect() as c:
        after = c.execute(text(
            "SELECT after FROM audit_events WHERE action = 'invoice.created' AND entity_id = :i"),
            {"i": str(invoice_id)}).scalar_one()
    assert (after["devise"], after["export"]) == ("USD", True)


# --- The database, for a write that skips the API --------------------------------------

def test_the_database_refuses_vat_on_an_export_line(client, admin, database):
    abroad = make_client(client, admin, **ABROAD)
    invoice_id = int(invoice(client, admin, abroad["id"]).json()["id"])
    with pytest.raises(DBAPIError, match="export of services"):
        with database.begin() as c:
            c.execute(text("UPDATE invoice_items SET taux_tva = 19 WHERE invoice_id = :i"), {"i": invoice_id})


def test_the_database_fixes_the_invoice_currency(client, admin, database):
    abroad = make_client(client, admin, **ABROAD)
    invoice_id = int(invoice(client, admin, abroad["id"]).json()["id"])
    with pytest.raises(DBAPIError, match="cannot change"):
        with database.begin() as c:
            c.execute(text("UPDATE invoices SET devise = 'EUR' WHERE id = :i"), {"i": invoice_id})


def test_the_database_refuses_an_export_client_in_dinars(database):
    with pytest.raises(DBAPIError, match="ck_clients_export_in_foreign_currency"):
        with database.begin() as c:
            c.execute(text("INSERT INTO clients (nom, export, devise) VALUES ('Raw export', true, 'TND')"))


# --- The PDF ----------------------------------------------------------------------------

def test_the_export_invoice_pdf_is_in_dollars_without_vat(client, admin):
    from invoice_flow import pdf_text

    abroad = make_client(client, admin, **ABROAD)
    draft = invoice(client, admin, abroad["id"]).json()
    pdf = pdf_text(client.get(f"/api/invoices/{draft['id']}/download", headers=admin).content)
    assert b"TOTAL DUE 2,000.00 USD" in pdf
    assert b"Export of services" in pdf and b"VAT No. GB 123456789" in pdf
    assert b"two thousand dollars" in pdf


# --- Totals are never summed across currencies -----------------------------------------

def sent_invoice(client, identities, client_id, rate):
    """Created, approved by the accountant and sent: in the books (#118)."""
    from invoice_flow import approve

    admin = identities["admin"]["headers"]
    created = invoice(client, admin, client_id, rate=rate)
    assert created.status_code == 200, created.text
    approve(client, identities, created.json()["id"])
    response = client.post(f"/api/invoices/{created.json()['id']}/send", headers=admin)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def one_of_each(client, admin, identities):
    """This month: one invoice in TND (2 380 TTC) and one in USD (2 000, no VAT)."""
    local = make_client(client, admin, **LOCAL)
    abroad = make_client(client, admin, **ABROAD)
    return sent_invoice(client, identities, local["id"], 19), sent_invoice(client, identities, abroad["id"], 0)


def test_the_dashboard_keeps_each_currency_apart(client, admin, one_of_each):
    figures = client.get("/api/dashboard/summary", headers=admin).json()["invoices"]
    clients = figures["clients"]
    assert clients["count"] == 2
    assert clients["amounts"] == [{"currency": "TND", "amount": pytest.approx(2380)},
                                  {"currency": "USD", "amount": pytest.approx(2000)}]
    # `amount` is the TND part only: never 4 380.
    assert clients["amount"] == pytest.approx(2380)
    sent = {s["status"]: s for s in figures["byStatus"]}["Sent"]
    assert {a["currency"] for a in sent["amounts"]} == {"TND", "USD"}


def test_the_month_preview_totals_each_currency(client, admin, one_of_each):
    from datetime import date

    month = date.today().strftime("%Y-%m")
    body = client.get(f"/api/periods/{month}", headers=admin).json()
    totals = {t["currency"]: t for t in body["totals_by_currency"]}
    assert float(totals["TND"]["total_ttc_outgoing"]) == pytest.approx(2380)
    assert float(totals["USD"]["total_ttc_outgoing"]) == pytest.approx(2000)
    assert float(totals["USD"]["total_ht_outgoing"]) == pytest.approx(2000)
    assert float(body["total_ttc_outgoing"]) == pytest.approx(2380), "the flat totals are the TND part"
    assert body["invoice_count"] == 2


def test_the_month_close_records_each_currency(client, admin, identities, one_of_each, database):
    from datetime import date

    for inv in one_of_each:
        for step in ("processed", "completed"):
            moved = client.patch(f"/api/invoices/{inv['id']}/processing-status", headers=admin,
                                 json={"processing_status": step})
            assert moved.status_code == 200, moved.text
    month = date.today().strftime("%Y-%m")
    closed = client.post(f"/api/periods/{month}/close", headers=admin)
    assert closed.status_code == 200, closed.text
    with database.connect() as c:
        stored = c.execute(text("SELECT totals_by_currency, total_ttc_outgoing FROM accounting_periods"
                                " WHERE periode = date_trunc('month', current_date)")).one()
    by_currency = {t["currency"]: t for t in stored[0]}
    assert by_currency["USD"]["total_ttc_outgoing"] == "2000.00"
    assert float(stored[1]) == pytest.approx(2380)
