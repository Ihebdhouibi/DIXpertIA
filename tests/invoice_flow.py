"""Helpers that walk an invoice through the verification flow (#118).

Since #118 a new outgoing invoice is a draft without a legal number: it gets
one when the accountant approves it, and the books can take it once it is sent.
Tests that need a numbered or a sent invoice go through the real endpoints,
so they exercise the same path as the app.
"""

import base64
import re
import zlib

DUE = "2027-12-31"


def draft(client, admin, client_id, amount=1000, due=DUE):
    """Create a draft as the admin. Returns the response."""
    return client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": due,
        "items": [{"designation": "Consulting", "quantite": 1,
                   "prix_unitaire": amount, "taux_tva": 19}],
    })


def submit(client, identities, invoice_id):
    return client.post(f"/api/invoices/{invoice_id}/submit", headers=identities["admin"]["headers"])


def approve(client, identities, invoice_id):
    """Submit as the admin, approve as the accountant. Returns the approved invoice."""
    submitted = submit(client, identities, invoice_id)
    assert submitted.status_code == 200, submitted.text
    approved = client.post(f"/api/invoices/{invoice_id}/approve",
                           headers=identities["accountant"]["headers"])
    assert approved.status_code == 200, approved.text
    return approved.json()


def numbered(client, identities, client_id, amount=1000):
    """A draft created, submitted and approved: it has its legal number."""
    created = draft(client, identities["admin"]["headers"], client_id, amount)
    assert created.status_code == 200, created.text
    return approve(client, identities, created.json()["id"])


def sent(client, identities, client_id, amount=1000):
    """An approved invoice marked as sent: the books can take it."""
    invoice = numbered(client, identities, client_id, amount)
    response = client.post(f"/api/invoices/{invoice['id']}/send", headers=identities["admin"]["headers"])
    assert response.status_code == 200, response.text
    return response.json()


def pdf_text(pdf: bytes) -> bytes:
    """The content streams of a ReportLab PDF, decoded, to search its text."""
    out = b""
    for match in re.finditer(rb"/ASCII85Decode /FlateDecode \].*?stream\r?\n(.*?)endstream", pdf, re.S):
        data = match.group(1).strip()
        if data.endswith(b"~>"):
            data = data[:-2]
        out += zlib.decompress(base64.a85decode(data))
    return out
