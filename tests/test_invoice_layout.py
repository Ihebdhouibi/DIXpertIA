"""The invoice PDF in the #194 layout (design/invoice-v2/README.md).

The generator and the amount in words need no database; the last tests go
through the API, so that a line's detail and unit reach the printed page.
"""

from decimal import Decimal

import pytest

from invoice_flow import pdf_text

SELLER = {"name": "DI Xpertia SUARL", "address": "Rue de Pasteur, Dar Chaabane El Fehri", "city": "8011 Nabeul",
          "phone": "+216 28 814 729", "email": "contact@dixpertia.com"}


def line(description="Development", qty=1, price=100, rate=19, detail=None, unit=None):
    return {"description": description, "detail": detail, "unit": unit, "qty": Decimal(qty),
            "price": Decimal(price), "total": Decimal(qty) * Decimal(price), "vat_rate": Decimal(rate)}


def render(locale="fr", items=None, subtotal=None, total=None, **extra):
    from app.services.invoice_generator import generate_invoice_pdf

    items = items if items is not None else [line()]
    subtotal = subtotal if subtotal is not None else sum(i["total"] for i in items)
    if total is None:
        total = sum(i["total"] * (1 + i["vat_rate"] / 100) for i in items).quantize(Decimal("0.01"))
    return pdf_text(generate_invoice_pdf({
        "locale": locale, "invoice_id": "FA-2026-0042", "client": "Acme", "client_address": "Tunis",
        "date_issued": "17 oct. 2026", "due_date": "16 nov. 2026", "status": "envoyee",
        "items": items, "subtotal": subtotal, "total": total, "seller": {**SELLER, **extra.pop("seller", {})},
        **extra,
    }))


# --- The amount in words --------------------------------------------------------------

@pytest.mark.parametrize("value,currency,locale,words", [
    (4927, "TND", "fr", "quatre mille neuf cent vingt-sept dinars"),
    (4927, "TND", "en", "four thousand nine hundred twenty-seven dinars"),
    (Decimal("1234.5"), "TND", "fr", "mille deux cent trente-quatre dinars et cinq cents millimes"),
    (Decimal("1234.5"), "TND", "en", "one thousand two hundred thirty-four dinars and five hundred millimes"),
    (1, "TND", "fr", "un dinar"),
    (Decimal("0.5"), "TND", "fr", "cinq cents millimes"),
    (0, "TND", "fr", "zéro dinar"),
    (80, "TND", "fr", "quatre-vingts dinars"),
    (81, "TND", "fr", "quatre-vingt-un dinars"),
    (71, "TND", "fr", "soixante et onze dinars"),
    (21, "TND", "fr", "vingt et un dinars"),
    (200, "TND", "fr", "deux cents dinars"),
    (201, "TND", "fr", "deux cent un dinars"),
    (80000, "TND", "fr", "quatre-vingt mille dinars"),
    (200000, "TND", "fr", "deux cent mille dinars"),
    (2_000_000, "TND", "fr", "deux millions de dinars"),
    (1_000_000, "EUR", "fr", "un million d'euros"),
    (2_000_000, "TND", "en", "two million dinars"),
    (Decimal("4000.25"), "EUR", "fr", "quatre mille euros et vingt-cinq centimes"),
    (Decimal("4000.25"), "EUR", "en", "four thousand euros and twenty-five cents"),
    (Decimal("1.01"), "USD", "en", "one dollar and one cent"),
])
def test_the_amount_in_words(value, currency, locale, words):
    from app.services.amount_in_words import amount_in_words

    assert amount_in_words(value, currency, locale) == words


def test_the_pdf_states_the_amount_in_words():
    pdf = render("fr", [line(qty=10, price=420, rate=0)], total=Decimal(4200))
    assert "à la somme de quatre mille deux cents dinars.".encode() in pdf
    pdf = render("en", [line(qty=10, price=420, rate=0)], total=Decimal(4200))
    assert b"Amount due: four thousand two hundred dinars." in pdf


# --- Totals -----------------------------------------------------------------------------

def test_one_vat_row_per_rate_highest_first():
    pdf = render("fr", [line(price=3600, rate=19), line(price=600, rate=7)])
    assert b"TVA 19" in pdf and b"TVA 7" in pdf
    assert pdf.index(b"TVA 19") < pdf.index(b"TVA 7")
    assert b"684,000" in pdf and b"42,000" in pdf
    assert b"4 926,000" in pdf


def test_the_vat_rows_add_up_to_the_stored_total():
    """The books hold amounts rounded to 2 decimals: the PDF never contradicts them."""
    from app.services.invoice_generator import _vat_rows

    items = [line(qty=1, price=Decimal("0.05"), rate=19), line(qty=1, price=Decimal("0.05"), rate=7)]
    subtotal, total = Decimal("0.10"), Decimal("0.11")
    rows = _vat_rows(items, subtotal, total, 3)
    assert sum(vat for _, _, vat in rows) == total - subtotal


def test_the_amount_due_is_the_stored_total():
    # A stored total the lines alone would not give: the PDF prints the stored one.
    pdf = render("en", [line(price=100, rate=19)], total=Decimal("119.00"))
    assert b"TOTAL DUE 119.000 TND" in pdf


# --- Lines ------------------------------------------------------------------------------

def test_a_line_prints_its_detail_and_unit():
    pdf = render("fr", [line("Développement", qty=12, price=350, detail="Module paie\nDeux revues", unit="jours")])
    assert "Développement".encode() in pdf
    assert b"Module paie" in pdf and b"Deux revues" in pdf
    assert b"jours" in pdf and b"12" in pdf


def test_french_and_english_number_formats():
    from app.services.invoice_generator import _number, _quantity, _rate

    # A no-break space in French, so an amount never breaks across two lines
    # (pypdf reads it back as a plain space, hence the direct checks).
    assert _number(Decimal("4200"), "fr", 3) == "4 200,000"
    assert _number(Decimal("4200"), "en", 3) == "4,200.000"
    assert _number(Decimal("4000"), "fr", 2) == "4 000,00"
    assert (_quantity(Decimal("2.50"), "fr"), _quantity(Decimal("12.00"), "en")) == ("2,5", "12")
    assert (_rate(Decimal("19.00"), "fr"), _rate(Decimal("7"), "en")) == ("19 %", "7%")
    fr = render("fr", [line(qty=Decimal("2.5"), price=1200, rate=19)])
    en = render("en", [line(qty=Decimal("2.5"), price=1200, rate=19)])
    assert b"2,5" in fr and b"1 200,000" in fr and b"19 %" in fr
    assert b"2.5" in en and b"1,200.000" in en and b"19%" in en


def test_a_long_invoice_runs_onto_numbered_pages():
    items = [line(f"Lot {n}", detail="Correctifs et évolutions.") for n in range(1, 41)]
    pdf = render("fr", items)
    assert b"Page 1 / 2" in pdf or b"Page 1 / 3" in pdf
    assert b"Suite page 2" in pdf
    assert "FA-2026-0042 · suite".encode() in pdf
    # The totals come once, after the last line.
    assert pdf.count("NET À PAYER".encode()) == 1
    assert pdf.index(b"Lot 40") < pdf.index("NET À PAYER".encode())


def test_a_short_invoice_is_one_page():
    pdf = render("en")
    assert b"Page 1 / 1" in pdf and b"Continued on page" not in pdf


# --- The seller -------------------------------------------------------------------------

def test_an_unset_seller_detail_is_not_printed():
    """No placeholder ever reaches a real invoice: #189 fills these."""
    pdf = render("fr", seller={"tax_id": "", "rne": "", "iban": ""})
    assert b"MF " not in pdf and b"RNE" not in pdf
    assert b"IBAN" not in pdf and "COORDONNÉES BANCAIRES".encode() not in pdf
    assert b"contact@dixpertia.com" in pdf


def test_a_set_seller_detail_is_printed():
    pdf = render("en", seller={"tax_id": "1234567A/A/M/000", "rne": "1234567A", "iban": "TN59 1000 0000"})
    assert b"Tax ID 1234567A/A/M/000" in pdf and b"RNE 1234567A" in pdf
    assert b"BANK DETAILS" in pdf and b"TN59 1000 0000" in pdf


def test_a_supplier_bill_puts_the_supplier_as_issuer():
    pdf = render("fr", incoming=True)
    # Émetteur, then the supplier (Acme), then Facturé à, then DI Xpertia.
    assert pdf.index("ÉMETTEUR".encode()) < pdf.index(b"Acme") < pdf.index("FACTURÉ À".encode())


# --- Through the API ------------------------------------------------------------------

@pytest.mark.identity("admin")
def test_the_downloaded_pdf_carries_the_lines_detail_and_unit(client, identities):
    admin = identities["admin"]["headers"]
    client_id = client.post("/api/clients", headers=admin, json={
        "nom": "Layout Client", "adresse": "1 rue de Tunis", "locale": "en"}).json()["id"]
    invoice = client.post("/api/invoices", headers=admin, json={
        "client_id": client_id, "date_echeance": "2027-12-31",
        "items": [{"designation": "Development", "quantite": 12, "prix_unitaire": 350, "taux_tva": 19,
                   "detail": "Payroll module", "unite": "days"}],
    }).json()
    pdf = pdf_text(client.get(f"/api/invoices/{invoice['id']}/download", headers=admin).content)
    assert b"Payroll module" in pdf and b"days" in pdf
    assert b"Page 1 / 1" in pdf and b"DRAFT" in pdf
