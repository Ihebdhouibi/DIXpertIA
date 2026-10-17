"""Correcting a draft invoice (#125), and the seal on invoice lines.

Only a draft of an invoice we issue can change, and the database holds the
rule: the API is tested where it is the way in, SQL where the point is that
SQL cannot get round it. As in test_invoice_rules, the acceptances matter as
much as the refusals - they show the rule is targeted, not a blanket freeze.
"""

from datetime import date

import pytest
from sqlalchemy import text

from invoice_flow import sent, submit

pytestmark = pytest.mark.identity("admin")

LINES = [
    {"designation": "Consulting", "quantite": 2, "prix_unitaire": 500, "taux_tva": 19},
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


@pytest.fixture
def draft(client, admin, a_client):
    return client.post("/api/invoices", headers=admin, json={
        "client_id": a_client, "date_echeance": "2027-12-31",
        "items": [{"designation": "Consulting", "quantite": 1,
                   "prix_unitaire": 1000, "taux_tva": 19}],
    }).json()


@pytest.fixture
def sent_invoice(client, identities, a_client):
    """Approved and sent through the real flow (#118): no longer a draft."""
    return sent(client, identities, a_client)


def edit(client, headers, invoice_id, items=LINES, due="2028-01-31"):
    return client.patch(f"/api/invoices/{invoice_id}", headers=headers,
                        json={"date_echeance": due, "items": items})


def test_a_draft_is_corrected_and_its_totals_recomputed(client, admin, draft):
    response = edit(client, admin, draft["id"])
    assert response.status_code == 200, response.text
    body = response.json()
    # 2 x 500 at 19% + 1 x 100 at 0%: HT 1100, TTC 1190 + 100.
    assert body["amountHT"] == pytest.approx(1100)
    assert body["amountTTC"] == pytest.approx(1290)
    assert [i["description"] for i in body["items"]] == ["Consulting", "Travel"]
    assert body["reference"] == draft["reference"], "the reference never changes"
    # What the edit form needs to prefill itself without losing anything.
    assert [i["vatRate"] for i in body["items"]] == [19, 0]
    assert body["dueDateIso"] == "2028-01-31"


def test_the_lines_are_replaced_not_appended(client, admin, draft, database):
    edit(client, admin, draft["id"])
    edit(client, admin, draft["id"], items=[LINES[1]])
    with database.connect() as c:
        count = c.execute(text("SELECT count(*) FROM invoice_items WHERE invoice_id = :i"),
                          {"i": int(draft["id"])}).scalar()
    assert count == 1


def test_only_the_admin_may_edit(client, identities, draft):
    for role in ("accountant", "employee"):
        assert edit(client, identities[role]["headers"], draft["id"]).status_code == 403


def test_a_correction_needs_at_least_one_line(client, admin, draft):
    assert edit(client, admin, draft["id"], items=[]).status_code == 422


def test_the_due_date_cannot_precede_the_issue_date(client, admin, draft):
    assert edit(client, admin, draft["id"], due="2000-01-01").status_code == 422


def test_an_unknown_invoice_is_404(client, admin):
    assert edit(client, admin, 999999).status_code == 404


def test_a_sent_invoice_is_refused_through_the_api(client, admin, sent_invoice):
    response = edit(client, admin, sent_invoice["id"])
    assert response.status_code == 409
    assert "no longer a draft" in response.json()["detail"]


def test_a_sent_invoice_is_refused_through_sql(sent_invoice, database):
    """The trigger, not the endpoint, is what holds the rule."""
    draft = sent_invoice
    with database.connect() as c:
        with pytest.raises(Exception, match="no longer a draft"):
            c.execute(text("UPDATE invoices SET montant_ttc = montant_ttc + 1 WHERE id = :i"),
                      {"i": int(draft["id"])})
    with database.connect() as c:
        with pytest.raises(Exception, match="lines cannot be changed"):
            c.execute(text("UPDATE invoice_items SET prix_unitaire = 1 WHERE invoice_id = :i"),
                      {"i": int(draft["id"])})
    with database.connect() as c:
        with pytest.raises(Exception, match="lines cannot be changed"):
            c.execute(text("INSERT INTO invoice_items (invoice_id, designation, quantite,"
                           " prix_unitaire, taux_tva) VALUES (:i, 'Extra', 1, 1, 19)"),
                      {"i": int(draft["id"])})


def test_a_sent_invoice_can_still_be_paid(sent_invoice, database):
    """Leaving draft freezes the content, not the commercial state."""
    draft = sent_invoice
    with database.begin() as c:
        # paid_on since #126: a paid invoice carries its payment date.
        c.execute(text("UPDATE invoices SET statut = 'PAYEE', paid_on = current_date WHERE id = :i"),
                  {"i": int(draft["id"])})
        statut = c.execute(text("SELECT statut FROM invoices WHERE id = :i"),
                           {"i": int(draft["id"])}).scalar()
    assert statut == "PAYEE"


def test_the_lines_of_an_archived_invoice_are_sealed(client, admin, sent_invoice, database):
    """The gap this issue closes: the archived seal used to stop at the invoice row."""
    draft = sent_invoice
    for state in ("processed", "completed"):
        client.patch(f"/api/invoices/{draft['id']}/processing-status",
                     headers=admin, json={"processing_status": state})
    month = date.today().strftime("%Y-%m")
    assert client.post(f"/api/periods/{month}/close", headers=admin).status_code == 200

    with database.connect() as c:
        with pytest.raises(Exception, match="archived and its lines are read-only"):
            c.execute(text("DELETE FROM invoice_items WHERE invoice_id = :i"), {"i": int(draft["id"])})
    # Archived and sent: the API refuses it as well.
    assert edit(client, admin, draft["id"]).status_code == 409


# --- #118: frozen while the accountant verifies it ---------------------------

def test_a_submitted_draft_cannot_be_edited(client, admin, identities, draft, database):
    assert submit(client, identities, draft["id"]).status_code == 200
    response = edit(client, admin, draft["id"])
    assert response.status_code == 409
    assert "under review" in response.json()["detail"]
    with database.connect() as c:
        with pytest.raises(Exception, match="under review"):
            c.execute(text("UPDATE invoices SET montant_ttc = montant_ttc + 1 WHERE id = :i"),
                      {"i": int(draft["id"])})


def test_a_rejected_draft_can_be_corrected_and_resubmitted(client, admin, identities, draft):
    accountant = identities["accountant"]["headers"]
    assert submit(client, identities, draft["id"]).status_code == 200
    rejected = client.post(f"/api/invoices/{draft['id']}/reject", headers=accountant,
                           json={"comment": "Travel is billed at cost, 0% VAT"})
    assert rejected.status_code == 200
    assert edit(client, admin, draft["id"]).status_code == 200, "a rejection reopens the draft"
    again = submit(client, identities, draft["id"])
    assert again.status_code == 200 and again.json()["reviewStatus"] == "Submitted"


def test_a_supplier_bill_is_still_recorded_with_its_lines(client, admin):
    """Bills are created already sent; the draft rule must not refuse their lines."""
    supplier = client.post("/api/suppliers", headers=admin, json={
        "nom": "Tunisie Telecom", "email": "f@tt.tn",
        "telephone": "+216 71 000 000", "adresse": "Tunis",
    }).json()["id"]
    today = date.today().isoformat()
    response = client.post("/api/supplier-invoices", headers=admin, json={
        "supplier_id": supplier, "supplier_reference": "TT-001",
        "date_emission": today, "date_echeance": today,
        "montant_ht": 100, "montant_ttc": 119,
        "items": [{"designation": "Line", "quantite": 1, "prix_unitaire": 100, "taux_tva": 19}],
    })
    assert response.status_code == 201, response.text
    # ...but it is not editable through this endpoint.
    assert edit(client, admin, response.json()["id"]).status_code == 409
