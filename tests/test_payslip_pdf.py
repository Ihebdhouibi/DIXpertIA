"""The payslip PDF (#22): who may download it, and what it says."""

import uuid

import pytest
from sqlalchemy import text

from tests.account_flow import make_account


# --- helpers ---------------------------------------------------------------

def _auth(user_id: str) -> dict:
    # Imported here: app.core.config reads the environment at import time.
    from app.core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': user_id, 'role': 'employee'})}"}


def _employee(database, first="Amel", last="Trabelsi", locale="en") -> dict:
    """A user and an employee record, named and in the given language."""
    user_id = make_account(database, f"emp-{uuid.uuid4().hex[:8]}@test.tn")
    with database.begin() as c:
        c.execute(text('UPDATE users SET "firstName" = :f, "lastName" = :l, locale = :loc WHERE id = :u'),
                  {"f": first, "l": last, "loc": locale, "u": user_id})
        employee_id = c.execute(text(
            "INSERT INTO employees (user_id, job_title, hired_on, annual_entitlement_days) "
            "VALUES (:u, 'Developer', '2024-01-15', 20) RETURNING id"), {"u": user_id}).scalar_one()
    return {"user_id": user_id, "employee_id": employee_id, "headers": _auth(user_id)}


def _payslip(database, employee_id, period: str, gross, net) -> int:
    with database.begin() as c:
        return c.execute(text(
            "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) "
            "VALUES (:e, :p, :g, :n) RETURNING id"),
            {"e": employee_id, "p": period, "g": gross, "n": net}).scalar_one()


def _text(response) -> str:
    from invoice_flow import pdf_text

    return pdf_text(response.content).decode("utf-8")


def _get(client, payslip_id, headers=None):
    return client.get(f"/api/payslips/{payslip_id}/pdf", headers=headers or {})


# --- access ----------------------------------------------------------------

def test_the_owner_downloads_their_payslip(client, database):
    emp = _employee(database)
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    response = _get(client, pid, emp["headers"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;") and "Payslip_2026-03_Amel_Trabelsi.pdf" in disposition


@pytest.mark.parametrize("role", ["admin", "accountant"])
def test_admin_and_accountant_download_any_payslip(client, database, identities, role):
    emp = _employee(database)
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    response = _get(client, pid, identities[role]["headers"])
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_another_employee_gets_404_like_an_unknown_id(client, database):
    owner, other = _employee(database), _employee(database, "Sami", "Gharbi")
    pid = _payslip(database, owner["employee_id"], "2026-03-01", 3000, 2400)
    hidden = _get(client, pid, other["headers"])
    unknown = _get(client, 999999, other["headers"])
    assert hidden.status_code == 404
    assert (hidden.status_code, hidden.json()) == (unknown.status_code, unknown.json())
    assert hidden.json()["code"] == "payslip.not_found"


def test_no_token_is_401(client, database):
    emp = _employee(database)
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    assert _get(client, pid).status_code == 401


# --- content ---------------------------------------------------------------

def test_the_pdf_says_who_when_and_how_much(client, database):
    emp = _employee(database)
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    body = _text(_get(client, pid, emp["headers"]))
    assert "Amel Trabelsi" in body
    assert "March 2026" in body
    assert "3,000.000" in body and "2,400.000" in body
    assert "Gross pay" in body and "NET PAY" in body and "YEAR TO DATE" in body

def test_the_pdf_is_in_the_employees_language_not_the_callers(client, database, identities):
    emp = _employee(database, locale="fr")
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    # Downloaded by an admin whose own account is not French.
    body = _text(_get(client, pid, identities["admin"]["headers"]))
    assert "mars 2026" in body and "Salaire brut" in body
    assert "Gross pay" not in body


def test_year_to_date_ignores_last_year_and_later_months(client, database):
    emp = _employee(database)
    e = emp["employee_id"]
    _payslip(database, e, "2025-12-01", 1000, 800)     # previous year
    _payslip(database, e, "2026-01-01", 2000, 1600)
    feb = _payslip(database, e, "2026-02-01", 3000, 2400)
    _payslip(database, e, "2026-03-01", 4000, 3200)    # a later month
    body = _text(_get(client, feb, emp["headers"]))
    assert "5,000.000" in body and "4,000.000" in body      # Jan + Feb: gross, net
    assert "6,000.000" not in body                           # would include December
    assert "10,000.000" not in body                          # would include everything


def test_markup_in_the_name_does_not_break_the_pdf(client, database):
    emp = _employee(database, first="R&D <b>Team", last="A & B <i>")
    pid = _payslip(database, emp["employee_id"], "2026-03-01", 3000, 2400)
    response = _get(client, pid, emp["headers"])
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert "<b>" in _text(response)
