"""Leave balances (#121): entitlement minus approved days, pending days apart.

The rules of this first version are in app/services/leave_balance.py: working
days Monday to Friday, only paid leave capped, the year's entitlement recorded
from annual_entitlement_days on first read and fixed afterwards.

The seeded accounts (conftest.ACCOUNTS) each have an employee record, hired on
2024-01-01 with 21 days a year. Requests are inserted directly, as the owner:
these tests are about the balance, not about requesting leave.
"""

import os
from datetime import date

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

URL = "/api/leaves/balances"
YEAR = 2026
ENTITLEMENT = 21  # conftest._seed_accounts
# insufficient_privilege: what a row-level security refusal raises. The code,
# not the message, which PostgreSQL translates (a French server says otherwise).
RLS_REFUSED = "42501"


def leave(database, employee_id, start, end, kind="PAYE", status="APPROUVE", validator="TEST-ADMIN"):
    with database.begin() as c:
        c.execute(text(
            "INSERT INTO leave_requests (employee_id, date_debut, date_fin, type_conge, statut, valide_par_id)"
            " VALUES (:e, :s, :f, :k, :st, :v)"),
            {"e": employee_id, "s": start, "f": end, "k": kind, "st": status,
             "v": None if status == "EN_ATTENTE" else validator})


def balance(client, who, year=YEAR, kind="paye", **params):
    response = client.get(URL, headers=who["headers"], params={"year": year, **params})
    assert response.status_code == 200, response.text
    return next(b for b in response.json()["balances"] if b["type"] == kind)


def recorded(database, employee_id, year=YEAR):
    with database.connect() as c:
        return c.execute(text(
            "SELECT days FROM leave_entitlements WHERE employee_id = :e AND year = :y"),
            {"e": employee_id, "y": year}).scalar()


@pytest.fixture
def employee(identities):
    return identities["employee"]


# --- Counting -------------------------------------------------------------------------

@pytest.mark.identity("employee")
def test_entitlement_minus_approved_days_with_pending_apart(client, database, employee):
    leave(database, employee["employee_id"], "2026-02-02", "2026-02-06")                  # Mon-Fri: 5
    leave(database, employee["employee_id"], "2026-03-02", "2026-03-03", status="EN_ATTENTE")  # 2
    paid = balance(client, employee)
    assert paid == {"type": "paye", "entitlement": 21, "approvedDays": 5, "pendingDays": 2, "availableDays": 16}


@pytest.mark.identity("employee")
def test_weekends_are_not_counted(client, database, employee):
    leave(database, employee["employee_id"], "2026-02-06", "2026-02-09")   # Fri-Mon: 2
    leave(database, employee["employee_id"], "2026-02-14", "2026-02-15")   # Sat-Sun: 0
    assert balance(client, employee)["approvedDays"] == 2


@pytest.mark.identity("employee")
def test_a_request_spanning_two_years_counts_in_each(client, database, employee):
    leave(database, employee["employee_id"], "2025-12-29", "2026-01-09")
    assert balance(client, employee, year=2025)["approvedDays"] == 3   # Mon 29 - Wed 31
    assert balance(client, employee, year=2026)["approvedDays"] == 7   # Thu 1 - Fri 9


@pytest.mark.identity("employee")
def test_refused_requests_do_not_count(client, database, employee):
    leave(database, employee["employee_id"], "2026-02-02", "2026-02-06", status="REFUSE")
    paid = balance(client, employee)
    assert (paid["approvedDays"], paid["pendingDays"]) == (0, 0)


@pytest.mark.identity("employee")
def test_sick_and_unpaid_leave_are_counted_not_capped(client, database, employee):
    leave(database, employee["employee_id"], "2026-02-02", "2026-02-03", kind="MALADIE")
    leave(database, employee["employee_id"], "2026-02-04", "2026-02-04", kind="SANS_SOLDE")
    sick = balance(client, employee, kind="maladie")
    assert (sick["approvedDays"], sick["entitlement"], sick["availableDays"]) == (2, 0, 0)
    assert balance(client, employee, kind="sans_solde")["approvedDays"] == 1
    # Neither touches paid leave.
    assert balance(client, employee)["availableDays"] == ENTITLEMENT


# --- The entitlement of a year ----------------------------------------------------------

@pytest.mark.identity("employee")
def test_the_year_is_recorded_on_first_read_then_fixed(client, database, employee):
    assert recorded(database, employee["employee_id"]) is None
    assert balance(client, employee)["entitlement"] == ENTITLEMENT
    assert recorded(database, employee["employee_id"]) == ENTITLEMENT

    with database.begin() as c:
        c.execute(text("UPDATE employees SET annual_entitlement_days = 30 WHERE id = :e"),
                  {"e": employee["employee_id"]})
    try:
        # A recorded year keeps its figure; a future one shows the new figure, unrecorded.
        assert balance(client, employee)["entitlement"] == ENTITLEMENT
        future = date.today().year + 1
        assert balance(client, employee, year=future)["entitlement"] == 30
        assert recorded(database, employee["employee_id"], future) is None
    finally:
        with database.begin() as c:
            c.execute(text("UPDATE employees SET annual_entitlement_days = :d WHERE id = :e"),
                      {"d": ENTITLEMENT, "e": employee["employee_id"]})


@pytest.mark.identity("employee")
def test_a_correction_by_the_admin_wins(client, database, employee):
    with database.begin() as c:
        c.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                       " VALUES (:e, :y, 'PAYE', 25.5)"), {"e": employee["employee_id"], "y": YEAR})
    assert balance(client, employee)["entitlement"] == 25.5


@pytest.mark.identity("employee")
def test_no_entitlement_before_the_year_of_hire(client, database, employee):
    assert balance(client, employee, year=2023)["entitlement"] == 0
    assert recorded(database, employee["employee_id"], 2023) is None


@pytest.mark.identity("employee")
@pytest.mark.parametrize("year", [0, 1999, 2101])
def test_the_year_is_bounded(client, employee, year):
    assert client.get(URL, headers=employee["headers"], params={"year": year}).status_code == 422


# --- Who sees whose ----------------------------------------------------------------------

@pytest.mark.identity("admin")
def test_the_admin_sees_an_employees_balance(client, database, identities):
    leave(database, identities["employee"]["employee_id"], "2026-02-02", "2026-02-06")
    paid = balance(client, identities["admin"], employee_id=identities["employee"]["employee_id"])
    assert (paid["entitlement"], paid["approvedDays"]) == (ENTITLEMENT, 5)


@pytest.mark.identity("employee")
def test_an_employee_may_name_their_own_record(client, employee):
    assert balance(client, employee, employee_id=employee["employee_id"])["entitlement"] == ENTITLEMENT


@pytest.mark.parametrize("role", ["employee", "accountant"])
def test_nobody_else_sees_someone_elses_balance(client, identities, role):
    from app.core.identity import set_identity

    set_identity(identities[role]["user_id"], role)
    other = identities["admin"]["employee_id"]
    response = client.get(URL, headers=identities[role]["headers"], params={"year": YEAR, "employee_id": other})
    assert response.status_code == 403


# --- The database holds the same line -----------------------------------------------------

def _as_app_role(user_id, role):
    engine = create_engine(os.environ["DATABASE_URL"])
    conn = engine.connect()
    conn.execute(text("SELECT set_config('app.user_id', :u, false), set_config('app.user_role', :r, false)"),
                 {"u": user_id or "", "r": role or ""})
    conn.commit()
    return engine, conn


def test_an_employee_cannot_give_themselves_more_days(database, identities):
    who = identities["employee"]
    engine, conn = _as_app_role(who["user_id"], "employee")
    try:
        with pytest.raises(DBAPIError) as refused:
            conn.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                              " VALUES (:e, :y, 'PAYE', 99)"), {"e": who["employee_id"], "y": YEAR})
        assert refused.value.orig.pgcode == RLS_REFUSED
        conn.rollback()
        # Their own year, with their own figure: allowed (that is what the first read does).
        conn.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                          " VALUES (:e, :y, 'PAYE', :d)"), {"e": who["employee_id"], "y": YEAR, "d": ENTITLEMENT})
        conn.rollback()
    finally:
        conn.close()
        engine.dispose()


def test_an_employee_cannot_read_or_record_someone_elses_year(database, identities):
    who, other = identities["employee"], identities["accountant"]["employee_id"]
    with database.begin() as c:
        c.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                       " VALUES (:e, :y, 'PAYE', 21)"), {"e": other, "y": YEAR})
    engine, conn = _as_app_role(who["user_id"], "employee")
    try:
        assert conn.execute(text("SELECT count(*) FROM leave_entitlements WHERE employee_id = :e"),
                            {"e": other}).scalar() == 0
        with pytest.raises(DBAPIError) as refused:
            conn.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                              " VALUES (:e, :y, 'PAYE', 21)"), {"e": other, "y": YEAR + 1})
        assert refused.value.orig.pgcode == RLS_REFUSED
        conn.rollback()
    finally:
        conn.close()
        engine.dispose()


def test_only_paid_leave_has_an_entitlement(database, identities):
    with pytest.raises(DBAPIError, match="ck_leave_entitlements_paid_only"):
        with database.begin() as c:
            c.execute(text("INSERT INTO leave_entitlements (employee_id, year, type_conge, days)"
                           " VALUES (:e, :y, 'MALADIE', 5)"), {"e": identities["employee"]["employee_id"], "y": YEAR})
