"""Verify the row-level security policies by direct query.

    python db/verify_rls.py

Creates two employees and one payslip each as the OWNER role, then reads the
table back under each identity as the APPLICATION role and checks what is
visible. Fixtures are removed again at the end.

Direct queries, not API calls, on purpose: the point of RLS is that it holds
even when the application's own role checks are wrong or bypassed. Testing
through the API would only re-test the API.

No pytest harness exists yet; this folds into the suite added by #57.
"""

import sys
from datetime import date

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.identity import clear_identity, set_identity

EMPLOYEES = ("RLS-EMP-A", "RLS-EMP-B")


def setup(owner):
    """Create a user, an employee record and a payslip for each fixture.

    Payslips hang off employees, not users, since #60 - so the fixture needs
    both, and the policy has to resolve users.id -> employees.id to decide what
    is visible.
    """
    ids = {}
    with owner.begin() as c:
        teardown_sql(c)
        for uid in EMPLOYEES:
            c.execute(
                text('INSERT INTO users (id, email, "firstName", "lastName", role, '
                     '"hashedPassword", "isActive", "isVerified", "createdAt") '
                     "VALUES (:id, :em, 'RLS', 'Fixture', 'employee', 'x', true, true, now())"),
                {"id": uid, "em": f"{uid.lower()}@rls.test"},
            )
            employee_id = c.execute(
                text("INSERT INTO employees (user_id, job_title, hired_on, "
                     "annual_entitlement_days) VALUES (:u, 'Fixture', :d, 21) RETURNING id"),
                {"u": uid, "d": date(2025, 1, 1)},
            ).scalar()
            ids[uid] = employee_id
            c.execute(
                text("INSERT INTO payslips (employee_id, periode, montant_brut, montant_net) "
                     "VALUES (:e, :p, 1000, 800)"),
                {"e": employee_id, "p": date(2026, 9, 1)},
            )
    return ids


def teardown_sql(c):
    c.execute(text("DELETE FROM payslips WHERE employee_id IN "
                   "(SELECT id FROM employees WHERE user_id = ANY(:ids))"),
              {"ids": list(EMPLOYEES)})
    c.execute(text("DELETE FROM leave_requests WHERE employee_id IN "
                   "(SELECT id FROM employees WHERE user_id = ANY(:ids))"),
              {"ids": list(EMPLOYEES)})
    c.execute(text("DELETE FROM employees WHERE user_id = ANY(:ids)"), {"ids": list(EMPLOYEES)})
    c.execute(text("DELETE FROM users WHERE id = ANY(:ids)"), {"ids": list(EMPLOYEES)})


def visible(user_id, role, ids):
    """Return the fixture user_ids whose payslips this identity can see."""
    by_employee_id = {v: k for k, v in ids.items()}
    set_identity(user_id, role)
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT employee_id FROM payslips WHERE employee_id = ANY(:ids)"),
            {"ids": list(ids.values())},
        ).all()
        return sorted(by_employee_id[r[0]] for r in rows)
    finally:
        db.close()


def main():
    owner = create_engine(settings.SCHEMA_DATABASE_URL)
    ids = setup(owner)

    a, b = EMPLOYEES
    cases = [
        ("employee sees only their own payslip", (a, "employee"), [a]),
        ("the other employee likewise", (b, "employee"), [b]),
        ("admin sees both", ("USR-001", "admin"), [a, b]),
        ("accountant sees both", ("USR-001", "accountant"), [a, b]),
    ]

    failures = []
    for label, (uid, role), expected in cases:
        got = visible(uid, role, ids)
        ok = got == expected
        print(f"  {'ok ' if ok else 'FAIL'}  {label}: {got}")
        if not ok:
            failures.append(f"{label}: expected {expected}, got {got}")

    clear_identity()
    db = SessionLocal()
    try:
        got = [r[0] for r in db.execute(
            text("SELECT employee_id FROM payslips WHERE employee_id = ANY(:ids)"),
            {"ids": list(ids.values())}).all()]
    finally:
        db.close()
    ok = got == []
    print(f"  {'ok ' if ok else 'FAIL'}  an unidentified session sees nothing: {got}")
    if not ok:
        failures.append(f"no identity: expected [], got {got}")

    # The explicit cross-tenant attempt: naming the other employee's rows.
    set_identity(a, "employee")
    db = SessionLocal()
    try:
        n = db.execute(text("SELECT count(*) FROM payslips WHERE employee_id = :o"),
                       {"o": ids[b]}).scalar()
    finally:
        db.close()
    ok = n == 0
    print(f"  {'ok ' if ok else 'FAIL'}  {a} asking directly for {b}'s payslip: {n} rows")
    if not ok:
        failures.append(f"cross-tenant read returned {n} rows")

    with owner.begin() as c:
        teardown_sql(c)
    print("  fixtures removed")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll row-level security checks passed.")


if __name__ == "__main__":
    main()
