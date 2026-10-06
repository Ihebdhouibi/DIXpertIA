"""Row-level security, through the API (#57).

db/verify_rls.py already proves the policies hold against direct SQL. This
proves the API does not hand the data over anyway - which is a separate
question, because an endpoint that queried as the owner role, or that forgot to
propagate the caller's identity, would bypass every policy while the SQL-level
check still passed.

The failure these prevent is the worst one in the system: one employee reading
another's payroll.
"""

import pytest
from sqlalchemy import text


@pytest.fixture
def payroll_for_everyone(database):
    """A payslip and a leave request for each fixture employee."""
    with database.connect() as c:
        rows = c.execute(text(
            "SELECT e.id, u.role FROM employees e JOIN users u ON u.id = e.user_id"
        )).all()
        for employee_id, _ in rows:
            c.execute(text(
                "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
                " VALUES (:e, '2026-03-01', 3000, 2400)"), {"e": employee_id})
            c.execute(text(
                "INSERT INTO leave_requests (employee_id, date_debut, date_fin,"
                " type_conge, statut) VALUES (:e, '2026-03-10', '2026-03-12',"
                " 'PAYE', 'EN_ATTENTE')"), {"e": employee_id})
    return {role: employee_id for employee_id, role in rows}


@pytest.mark.identity("employee")
def test_an_employee_sees_only_their_own_payslips(client, identities,
                                                  payroll_for_everyone):
    me = identities["employee"]
    response = client.get("/api/payslips", headers=me["headers"])
    assert response.status_code == 200

    returned = {row["employeeId"] for row in response.json()}
    assert returned == {me["employee_id"]}, (
        f"an employee must see only their own payslips, got {returned}"
    )


@pytest.mark.identity("employee")
def test_an_employee_sees_only_their_own_leave(client, identities,
                                               payroll_for_everyone):
    me = identities["employee"]
    response = client.get("/api/leave-requests", headers=me["headers"])
    assert response.status_code == 200
    returned = {row["employeeId"] for row in response.json()}
    assert returned == {me["employee_id"]}


@pytest.mark.identity("admin")
def test_an_admin_sees_everyone(client, identities, payroll_for_everyone):
    response = client.get("/api/payslips", headers=identities["admin"]["headers"])
    assert response.status_code == 200
    assert len(response.json()) == len(payroll_for_everyone)


@pytest.mark.identity("accountant")
def test_an_accountant_sees_all_payroll_but_only_their_own_leave(
        client, identities, payroll_for_everyone):
    """The split decided on #10.

    Payroll is the accountant's job. Leave is not, so they see their own
    request like any other employee and nobody else's.
    """
    me = identities["accountant"]
    payslips = client.get("/api/payslips", headers=me["headers"])
    assert len(payslips.json()) == len(payroll_for_everyone)

    leave = client.get("/api/leave-requests", headers=me["headers"])
    returned = {row["employeeId"] for row in leave.json()}
    assert returned == {me["employee_id"]}


@pytest.mark.identity("employee")
def test_no_response_ever_carries_a_password_hash(client, identities):
    """An explicit output schema is what stops this; here is the check.

    The removed GET /api/data returned whole user rows, hashes included, to any
    authenticated caller. Nothing structural prevents that returning except
    schemas - and a test.
    """
    for path in ("/api/me", "/api/payslips", "/api/leave-requests", "/api/employees"):
        body = client.get(path, headers=identities["employee"]["headers"]).text
        for secret in ("hashedPassword", "resetToken", "resetTokenExpiry"):
            assert secret not in body, f"{path} leaked {secret}"


def test_without_an_identity_the_tables_read_as_empty(database):
    """The policies fail closed.

    current_setting(..., true) gives NULL when never set and '' once a
    transaction-local value has gone out of scope. Both must mean "no
    identity"; if either leaked through as a match, every row would be visible
    to an unauthenticated connection.
    """
    from app.core.database import SessionLocal
    from app.core.identity import clear_identity, set_identity

    with database.connect() as c:
        employee_id = c.execute(text("SELECT id FROM employees LIMIT 1")).scalar()
        c.execute(text(
            "INSERT INTO payslips (employee_id, periode, montant_brut, montant_net)"
            " VALUES (:e, '2026-04-01', 1000, 800)"), {"e": employee_id})

    set_identity(None, None)
    session = SessionLocal()
    try:
        visible = session.execute(text("SELECT count(*) FROM payslips")).scalar()
    finally:
        session.close()
        clear_identity()

    assert visible == 0, "payroll was readable with no identity set"
