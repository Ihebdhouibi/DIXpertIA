import uuid

import pytest
from sqlalchemy import text

from tests.account_flow import make_account


# --- helpers -------------------------------------------------------------

def _make_employee(database, client, email: str) -> dict:
    """Create a user + employee row, commit, return {employee_id, user_id, email, headers}.

    make_account only inserts into `users`; the `employees` row has to be
    created here or `SELECT id FROM employees WHERE user_id = :u` finds nothing.
    """
    user_id = make_account(database, email)

    with database.begin() as c:                      # begin() commits on exit
        e_id = c.execute(
            text(
                "INSERT INTO employees (user_id, job_title, hired_on, annual_entitlement_days) "
                "VALUES (:u, 'Tester', '2024-01-01', 20) RETURNING id"
            ),
            {"u": user_id},
        ).scalar_one()

    headers = _auth_headers(user_id)
    return {"employee_id": e_id, "user_id": user_id, "email": email, "headers": headers}


def _auth_headers(user_id: str, role: str = "employee") -> dict:
    # Imported here, not at module level: app.core.config reads its
    # environment at import time, and the `database` fixture sets it.
    from app.core.security import create_access_token

    token = create_access_token({"sub": user_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


# --- fixture -------------------------------------------------------------

@pytest.fixture
def setup_employee_with_entitlement(database, client):
    """Creates an employee with 20 days of PAID leave entitlement for 2026,
    one approved 5-day request (Feb 1-5) and one pending 2-day request (Mar 1-2).

    Approved requests need a validator (ck_leave_decision_has_validator), and
    the validator cannot be the employee themselves (trg_leave_no_self_validation),
    so a separate user is created for that role.
    """
    unique_email = f"emp-leave-{uuid.uuid4().hex[:8]}@test.tn"
    account = _make_employee(database, client, unique_email)
    e_id = account["employee_id"]

    validator_id = make_account(
        database, f"validator-{uuid.uuid4().hex[:8]}@test.tn"
    )
    account["validator_id"] = validator_id

    with database.begin() as c:
        c.execute(
            text(
                "INSERT INTO leave_entitlements (employee_id, year, type_conge, days) "
                "VALUES (:e, 2026, 'PAYE', 20)"
            ),
            {"e": e_id},
        )
        c.execute(
            text(
                "INSERT INTO leave_requests "
                "(employee_id, date_debut, date_fin, type_conge, statut, valide_par_id) "
                "VALUES (:e, '2026-02-01', '2026-02-05', 'PAYE', 'APPROUVE', :v)"
            ),
            {"e": e_id, "v": validator_id},
        )
        c.execute(
            text(
                "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut) "
                "VALUES (:e, '2026-03-01', '2026-03-02', 'PAYE', 'EN_ATTENTE')"
            ),
            {"e": e_id},
        )

    return account   # {employee_id, user_id, email, headers, validator_id}


# --- tests ---------------------------------------------------------------

def test_balance_calculation(client, setup_employee_with_entitlement):
    setup = setup_employee_with_entitlement
    res = client.get("/api/leaves/balances?year=2026", headers=setup["headers"])
    assert res.status_code == 200

    paye = next(b for b in res.json()["balances"] if b["type"] == "paye")
    assert paye["entitlement"] == 20.0
    assert paye["approvedDays"] == 5.0
    assert paye["pendingDays"] == 2.0
    assert paye["availableDays"] == 15.0


def test_request_spanning_two_years(client, database, setup_employee_with_entitlement):
    setup = setup_employee_with_entitlement
    e_id = setup["employee_id"]

    with database.begin() as c:
        c.execute(
            text(
                "INSERT INTO leave_requests "
                "(employee_id, date_debut, date_fin, type_conge, statut, valide_par_id) "
                "VALUES (:e, '2025-12-28', '2026-01-03', 'PAYE', 'APPROUVE', :v)"
            ),
            {"e": e_id, "v": setup["validator_id"]},
        )

    res = client.get("/api/leaves/balances?year=2026", headers=setup["headers"])
    paye = next(b for b in res.json()["balances"] if b["type"] == "paye")
    # 5 days in Feb + 3 days falling in 2026 (Jan 1-3) = 8
    assert paye["approvedDays"] == 8.0


def test_admin_can_see_other_employee_balance(
    client, identities, setup_employee_with_entitlement
):
    setup = setup_employee_with_entitlement
    res = client.get(
        f"/api/leaves/balances?year=2026&employee_id={setup['employee_id']}",
        headers=identities["admin"]["headers"],
    )
    assert res.status_code == 200
    paye = next(b for b in res.json()["balances"] if b["type"] == "paye")
    # The admin really sees the *other* employee's balance, not an empty list.
    assert paye["entitlement"] == 20.0
    assert paye["approvedDays"] == 5.0


def test_employee_cannot_see_other_employee_balance(
    client, identities, setup_employee_with_entitlement
):
    setup = setup_employee_with_entitlement
    # A non-admin signed-in user (accountant) tries to read someone else's balance.
    res = client.get(
        f"/api/leaves/balances?year=2026&employee_id={setup['employee_id']}",
        headers=identities["accountant"]["headers"],
    )
    assert res.status_code == 403


def test_employee_without_entitlement(client, database):
    unique_email = f"emp-no-entitlement-{uuid.uuid4().hex[:8]}@test.tn"
    account = _make_employee(database, client, unique_email)

    res = client.get("/api/leaves/balances?year=2026", headers=account["headers"])
    assert res.status_code == 200
    paye = next(b for b in res.json()["balances"] if b["type"] == "paye")
    assert paye["entitlement"] == 0.0
    assert paye["availableDays"] == 0.0
