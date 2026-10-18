"""French and English (#135).

The API answers in the request's language (Accept-Language), French without
one. E-mails and notification texts follow the reader's account language,
the invoice PDF its client's. The catalog is complete in both languages, and
every message a database trigger can raise is recognised and translated.
"""

import re
import string

import pytest
from sqlalchemy import text

from account_flow import bearer, link_token, make_account, sign_in
from invoice_flow import draft, pdf_text, sent, submit

pytestmark = pytest.mark.identity("admin")

DOMAIN = "i18n-test.tn"
FR = {"Accept-Language": "fr"}
EN = {"Accept-Language": "en"}


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def accountant(identities):
    return identities["accountant"]["headers"]


def make_client(client, admin, locale="fr", nom="Acme Corporation"):
    return client.post("/api/clients", headers=admin, json={
        "nom": nom, "email": "a@acme.tn", "telephone": "+216 70 000 000",
        "adresse": "1 rue de Tunis", "locale": locale}).json()["id"]


# --- The catalog ----------------------------------------------------------------------

def _placeholders(value: str) -> set:
    return {name for _, name, _, _ in string.Formatter().parse(value) if name is not None}


def test_every_message_exists_in_both_languages_with_the_same_placeholders():
    from app.i18n import CATALOG, LOCALES

    for key, texts in CATALOG.items():
        assert set(texts) == set(LOCALES), f"{key} is missing a language"
        assert all(texts[loc].strip() for loc in LOCALES), f"{key} has an empty text"
        assert _placeholders(texts["fr"]) == _placeholders(texts["en"]), f"{key}: placeholders differ"


def test_every_trigger_message_is_recognised(database):
    """A trigger raising a message the catalog cannot translate would reach a
    French user in English. Read from the live functions, not the migrations."""
    from app.i18n import translate_db_message

    with database.connect() as c:
        sources = c.execute(text(
            "SELECT p.proname, p.prosrc FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
            "WHERE n.nspname = 'public' AND p.prosrc LIKE '%RAISE EXCEPTION%'")).all()
    assert sources, "the scan must see the trigger functions"
    unrecognised = []
    for name, source in sources:
        for raise_ in re.finditer(r"RAISE EXCEPTION\s+((?:'(?:[^']|'')*'\s*)+)", source):
            fmt = "".join(re.findall(r"'((?:[^']|'')*)'", raise_.group(1))).replace("''", "'")
            sample = fmt.replace("%", "X-1")
            if translate_db_message(sample, "fr") is None:
                unrecognised.append((name, fmt))
    assert unrecognised == [], f"trigger messages with no translation: {unrecognised}"


# --- API errors: the request's language -------------------------------------------------

@pytest.mark.parametrize("headers,expected", [
    (FR, "Facture introuvable"),
    (EN, "Invoice not found"),
    ({"Accept-Language": "en-US,en;q=0.9"}, "Invoice not found"),
    ({"Accept-Language": ""}, "Facture introuvable"),
    ({"Accept-Language": "de-DE"}, "Facture introuvable"),
])
def test_an_error_answers_in_the_request_language(client, identities, headers, expected):
    response = client.get("/api/invoices/999999", headers={**identities["admin"]["headers"], **headers})
    assert response.status_code == 404
    assert response.json() == {"detail": expected, "code": "invoice.not_found"}


def test_an_unauthenticated_request_is_refused_in_french_by_default(client):
    response = client.get("/api/me", headers={"Accept-Language": ""})
    assert response.status_code == 401 and response.json()["detail"] == "Non authentifié"


def test_a_database_rule_answers_in_the_request_language(client, admin):
    client_id = make_client(client, admin)
    invoice_id = draft(client, admin, client_id).json()["id"]
    path = f"/api/invoices/{invoice_id}/processing-status"
    body = {"processing_status": "processed"}
    fr = client.patch(path, headers={**admin, **FR}, json=body)
    en = client.patch(path, headers={**admin, **EN}, json=body)
    assert fr.status_code == en.status_code == 409
    assert "est encore un brouillon" in fr.json()["detail"]
    assert "is still a draft" in en.json()["detail"]


def test_a_status_inside_a_sentence_is_translated(client, admin, accountant, identities):
    client_id = make_client(client, admin)
    invoice = sent(client, identities, client_id)
    client.post(f"/api/invoices/{invoice['id']}/cancel", headers=admin, json={"reason": "Doublon"})
    refused = client.post(f"/api/invoices/{invoice['id']}/pay", headers={**accountant, **FR},
                          json={"paid_on": invoice["dateIssuedIso"]})
    assert refused.status_code == 409
    assert "est annulée et ne peut pas être marquée payée" in refused.json()["detail"]


def test_dates_follow_the_request_language(client, admin):
    invoice_id = draft(client, admin, make_client(client, admin)).json()["id"]
    fr = client.get(f"/api/invoices/{invoice_id}", headers={**admin, **FR}).json()["dateIssued"]
    en = client.get(f"/api/invoices/{invoice_id}", headers={**admin, **EN}).json()["dateIssued"]
    assert re.fullmatch(r"\d{1,2} \S+ \d{4}", fr), fr
    assert re.fullmatch(r"[A-Z][a-z]{2} \d{2}, \d{4}", en), en


# --- Notifications: rendered in the reader's language -----------------------------------

def test_a_notification_is_read_in_the_readers_language(client, admin, accountant, identities, database):
    invoice_id = draft(client, admin, make_client(client, admin, nom="Société Générale")).json()["id"]
    submit(client, identities, invoice_id)
    [fr] = client.get("/api/notifications", headers={**accountant, **FR}).json()
    [en] = client.get("/api/notifications", headers={**accountant, **EN}).json()
    assert fr["message"].startswith("La facture") and "attend votre vérification" in fr["message"]
    assert en["message"].startswith("Invoice") and "waiting for your verification" in en["message"]
    with database.connect() as c:
        stored = c.execute(text("SELECT message, params FROM notifications")).one()
    assert stored.message == en["message"], "an English copy is kept for SQL readers"
    assert stored.params["party"] == "Société Générale"


# --- E-mails: the recipient's account language ------------------------------------------

def test_the_activation_email_is_in_the_language_chosen_for_the_account(client, admin, mailbox):
    client.post("/api/users", headers=admin, json={
        "email": f"fr@{DOMAIN}", "firstName": "Amel", "lastName": "B", "role": "employee"})
    client.post("/api/users", headers=admin, json={
        "email": f"en@{DOMAIN}", "firstName": "John", "lastName": "D", "role": "employee", "locale": "en"})
    by_to = {m["to"]: m for m in mailbox}
    assert by_to[f"fr@{DOMAIN}"]["subject"] == "Activez votre compte DIXpertIA"
    assert by_to[f"fr@{DOMAIN}"]["body"].startswith("Bonjour Amel")
    assert by_to[f"en@{DOMAIN}"]["subject"] == "Activate your DIXpertIA account"
    assert link_token(mailbox, f"fr@{DOMAIN}"), "the link is still there"


def test_the_reset_email_follows_the_account_not_the_page(client, database, mailbox):
    make_account(database, f"reader@{DOMAIN}")  # French, the default
    client.post("/api/forgot-password", headers=EN, json={"email": f"reader@{DOMAIN}"})
    assert mailbox[-1]["subject"] == "Réinitialisation de votre mot de passe"


# --- The account's own language -----------------------------------------------------------

def test_an_account_saves_its_own_language(client, database):
    make_account(database, f"self@{DOMAIN}")
    signed_in = sign_in(client, f"self@{DOMAIN}").json()
    assert signed_in["user"]["locale"] == "fr"
    token = signed_in["access_token"]
    saved = client.put("/api/me/locale", headers=bearer(token), json={"locale": "en"})
    assert saved.status_code == 200 and saved.json()["locale"] == "en"
    assert client.get("/api/me", headers=bearer(token)).json()["locale"] == "en"
    assert client.put("/api/me/locale", headers=bearer(token), json={"locale": "de"}).status_code == 422


def test_the_language_endpoint_changes_only_the_callers_row(client, identities, database):
    employee = identities["employee"]
    client.put("/api/me/locale", headers=employee["headers"], json={"locale": "en"})
    with database.connect() as c:
        rows = dict(c.execute(text("SELECT id, locale FROM users WHERE id = ANY(:i)"),
                              {"i": [identities[r]["user_id"] for r in ("admin", "accountant", "employee")]}).all())
        c.execute(text("UPDATE users SET locale = 'fr' WHERE id = :u"), {"u": employee["user_id"]})
    assert rows[employee["user_id"]] == "en"
    assert rows[identities["admin"]["user_id"]] == rows[identities["accountant"]["user_id"]] == "fr"


# --- The invoice PDF: the client's language -----------------------------------------------

@pytest.mark.parametrize("locale,words,absent", [
    ("fr", (b"FACTURE", b"Total TTC", b"TND"), b"INVOICE"),
    ("en", (b"INVOICE", b"Total due", b"TND"), b"FACTURE"),
])
def test_the_pdf_is_printed_in_the_clients_language_whoever_downloads_it(
        client, admin, identities, locale, words, absent):
    invoice = sent(client, identities, make_client(client, admin, locale=locale, nom=f"Client {locale}"))
    for request_language in (FR, EN):
        pdf = pdf_text(client.get(f"/api/invoices/{invoice['id']}/download",
                                  headers={**admin, **request_language}).content)
        for word in words:
            assert word in pdf, (locale, request_language, word)
        assert absent not in pdf and b"$" not in pdf
