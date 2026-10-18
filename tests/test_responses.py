"""What leaves the API, and what values the database accepts (#77).

AUDIT-DB-020: rows used to be serialised as obj.__dict__ minus a denylist, so
any column added later was exposed by default. Every JSON route now declares
a response model - an allowlist - and the first test fails for a route that
does not. The second reads every GET route, and the account endpoints, as the
admin, and fails if a secret appears anywhere in a body.

AUDIT-DB-019: roles and statuses were free text in places. Every column that
holds a closed set is now constrained by the database, by a PostgreSQL enum or
a CHECK; the third test fails for a new one that is not.
"""

import re
from datetime import date

import pytest
from sqlalchemy import text

from account_flow import make_account, sign_in
from invoice_flow import draft, submit

pytestmark = pytest.mark.identity("admin")

DOMAIN = "responses-test.tn"

# Returns a file, not JSON: nothing to allowlist.
NOT_JSON = {("GET", "/api/invoices/{invoice_id}/download")}

# A secret, or the name of a column that holds one. None may appear in any
# response body. "$2b$" is the prefix of every bcrypt hash; "!unusable:" the
# placeholder of an account not yet activated.
SECRETS = ("hashedPassword", "resetToken", "token_hash", "token_version",
           "tempPassword", "$2b$", "!unusable:")


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


def test_every_json_route_declares_a_response_model(app):
    from fastapi.routing import APIRoute

    missing = sorted(
        (method, route.path)
        for route in app.routes if isinstance(route, APIRoute) and route.path.startswith("/api")
        for method in route.methods
        if route.response_model is None and route.status_code != 204
        and (method, route.path) not in NOT_JSON
    )
    assert missing == [], f"routes answering with an undeclared shape: {missing}"


def test_no_response_carries_a_secret(app, client, identities, database):
    from fastapi.routing import APIRoute

    admin = identities["admin"]["headers"]
    # Data behind every route: an account with a real bcrypt hash, one not yet
    # activated, an invoice under review, a period, a notification.
    make_account(database, f"real-hash@{DOMAIN}")
    pending = client.post("/api/users", headers=admin, json={
        "email": f"pending@{DOMAIN}", "firstName": "Pen", "lastName": "Ding", "role": "employee"})
    a_client = client.post("/api/clients", headers=admin, json={
        "nom": "Acme", "email": "a@acme.tn", "telephone": "+216 70 000 000", "adresse": "Tunis"}).json()["id"]
    invoice_id = draft(client, admin, a_client).json()["id"]
    submit(client, identities, invoice_id)
    signed_in = sign_in(client, f"real-hash@{DOMAIN}")

    params = {"invoice_id": invoice_id, "month": date.today().strftime("%Y-%m")}
    bodies = {"POST /api/users": pending.text, "POST /api/login": signed_in.text}
    for route in app.routes:
        if not (isinstance(route, APIRoute) and "GET" in route.methods and route.path.startswith("/api")):
            continue
        if ("GET", route.path) in NOT_JSON:
            continue
        path = re.sub(r"\{(\w+)\}", lambda m: str(params[m.group(1)]), route.path)
        for role in ("admin", "accountant", "employee"):
            response = client.get(path, headers=identities[role]["headers"])
            assert response.status_code < 500, f"GET {path} as {role}: {response.status_code}"
            bodies[f"GET {path} as {role}"] = response.text

    assert pending.status_code == 201 and signed_in.status_code == 200
    leaks = [(where, secret) for where, body in bodies.items() for secret in SECRETS if secret in body]
    assert leaks == [], f"secrets in responses: {leaks}"


# Columns that hold a closed set must be constrained by the database. The
# open ones below are open by design, and adding a column here is a decision
# to make in review, not a way to silence the test.
OPEN_BY_DESIGN = {
    ("audit_events", "action"): "event names, grows with every audited feature (#63)",
    ("audit_events", "actor_role"): "a snapshot; the INSERT policy holds it to the caller's real role",
    ("notifications", "kind"): "event names, grows with every notified feature (#116)",
    ("notifications", "ref_type"): "the kind of record a notification points at",
}
CLOSED_SET = re.compile(r"(^|_)(status|statut|state|role|purpose|tone|direction|series|type|action|kind)($|_)")


def test_every_status_and_type_column_is_constrained(database):
    with database.connect() as c:
        columns = c.execute(text("""
            SELECT col.table_name, col.column_name, col.data_type = 'USER-DEFINED' AS is_enum,
                   EXISTS (
                       SELECT 1 FROM pg_constraint k
                       JOIN pg_attribute a ON a.attrelid = k.conrelid AND a.attnum = ANY (k.conkey)
                       WHERE k.contype = 'c'
                         AND k.conrelid = format('public.%I', col.table_name)::regclass
                         AND a.attname = col.column_name
                   ) AS is_checked
            FROM information_schema.columns col
            JOIN information_schema.tables t
              ON t.table_schema = col.table_schema AND t.table_name = col.table_name
            WHERE col.table_schema = 'public' AND t.table_type = 'BASE TABLE'
              AND col.table_name <> 'alembic_version'
        """)).all()

    candidates = [(t, col) for t, col, _, _ in columns if CLOSED_SET.search(col)]
    assert ("users", "role") in candidates, "the scan must see the columns it guards"
    unconstrained = sorted(
        (t, col) for t, col, is_enum, is_checked in columns
        if CLOSED_SET.search(col) and not (is_enum or is_checked) and (t, col) not in OPEN_BY_DESIGN
    )
    assert unconstrained == [], f"closed-set columns the database does not constrain: {unconstrained}"


def test_an_unknown_role_is_refused(database):
    with pytest.raises(Exception, match="ck_users_role"):
        with database.connect() as c:
            c.execute(text(
                'INSERT INTO users (email, "firstName", "lastName", role, "hashedPassword")'
                " VALUES (:e, 'Super', 'Admin', 'superadmin', 'x')"), {"e": f"super@{DOMAIN}"})
