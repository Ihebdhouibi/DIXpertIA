
import uuid

import pytest
from sqlalchemy import text

from tests.account_flow import make_account



@pytest.fixture
def setup_employee_with_entitlement(database):
    """Creates an employee with 20 days of PAID leave entitlement for 2026."""
    # Génère un e-mail unique pour éviter le UniqueViolation entre les tests
    unique_email = f"emp-leave-{uuid.uuid4().hex[:8]}@test.tn"
    emp_id = make_account(database, unique_email)

    with database.connect() as c:
        e_id = c.execute(
            text("SELECT id FROM employees WHERE user_id = :u"),
            {"u": emp_id},
        ).scalar_one()

        c.execute(
            text(
                "INSERT INTO leave_entitlements (employee_id, year, type_conge, days) "
                "VALUES (:e, 2026, 'PAYE', 20)"
            ),
            {"e": e_id},
        )

        c.execute(
            text(
                "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut) "
                "VALUES (:e, '2026-02-01', '2026-02-05', 'PAYE', 'APPROUVE')"
            ),
            {"e": e_id},
        )

        c.execute(
            text(
                "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut) "
                "VALUES (:e, '2026-03-01', '2026-03-02', 'PAYE', 'EN_ATTENTE')"
            ),
            {"e": e_id},
        )

    return e_id


def test_balance_calculation(client, identities, setup_employee_with_entitlement):
    emp_headers = identities["employee"]["headers"]

    res = client.get("/api/leaves/balances?year=2026", headers=emp_headers)
    assert res.status_code == 200
    data = res.json()

    paye_bal = next(b for b in data["balances"] if b["type"] == "paye")
    assert paye_bal["entitlement"] == 20.0
    assert paye_bal["approvedDays"] == 5.0
    assert paye_bal["pendingDays"] == 2.0
    assert paye_bal["availableDays"] == 15.0


def test_request_spanning_two_years(client, database, identities, setup_employee_with_entitlement):
    e_id = setup_employee_with_entitlement
    emp_headers = identities["employee"]["headers"]

    with database.connect() as c:
        c.execute(
            text(
                "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut) "
                "VALUES (:e, '2025-12-28', '2026-01-03', 'PAYE', 'APPROUVE')"
            ),
            {"e": e_id},
        )

    res = client.get("/api/leaves/balances?year=2026", headers=emp_headers)
    paye_bal = next(b for b in res.json()["balances"] if b["type"] == "paye")
    assert paye_bal["approvedDays"] == 8.0


def test_admin_can_see_other_employee_balance(client, identities, setup_employee_with_entitlement):
    e_id = setup_employee_with_entitlement
    admin_headers = identities["admin"]["headers"]

    res = client.get(f"/api/leaves/balances?year=2026&employee_id={e_id}", headers=admin_headers)
    assert res.status_code == 200


def test_employee_cannot_see_other_employee_balance(client, identities, setup_employee_with_entitlement):
    e_id = setup_employee_with_entitlement
    other_emp_headers = identities["accountant"]["headers"]

    res = client.get(f"/api/leaves/balances?year=2026&employee_id={e_id}", headers=other_emp_headers)
    assert res.status_code == 403


def test_employee_without_entitlement(client, database, identities):
    make_account(database, "no-entitlement@test.tn")
    emp_headers = identities["employee"]["headers"]

    res = client.get("/api/leaves/balances?year=2026", headers=emp_headers)
    assert res.status_code == 200
    paye_bal = next(b for b in res.json()["balances"] if b["type"] == "paye")
    assert paye_bal["entitlement"] == 0.0
    assert paye_bal["availableDays"] == 0.0
