"""Every route, against every identity (#57).

This is the test that protects the other remediations. The audit found routes
reachable without authentication at all, and the fix for each was a one-line
dependency - exactly the kind of line that gets dropped in a refactor without
anybody noticing. Here, dropping it fails the suite.

The matrix below is the *contract*, not a description of current behaviour. If
a change makes a route more permissive, this file is what says so.

Routes are exercised with throw-away ids where they take one: the point is the
authorisation decision, which is taken before the row is looked up, so a 404 on
a missing row still proves the caller got past the guard. Anything in the 200s,
404 or 422 counts as "allowed through"; 401 and 403 count as "refused".
"""

import pytest

PUBLIC = "public"
AUTHENTICATED = "any signed-in user"
ADMIN_ONLY = "admin"
BOOKKEEPING = "admin or accountant"
# The accountant's verification decisions (#118): not even the admin, who
# creates the invoices and must not approve their own.
ACCOUNTANT_ONLY = "accountant"
BILLING = "admin, accountant or rh"
EMPLOYEE_SELF = "any signed-in user, scoped to their own rows"

# (method, path, who may reach it)
#
# "Reach" means pass the authorisation guard. A route may still refuse the
# *request* afterwards - a 404 for a missing invoice, a 422 for a bad body -
# and that is not an authorisation failure.
ROUTES = [
    # --- public: authentication itself, and the reset flow ------------------
    ("POST", "/api/login", PUBLIC),
    ("POST", "/api/forgot-password", PUBLIC),
    ("POST", "/api/reset-password", PUBLIC),
    ("POST", "/api/activate", PUBLIC),

    # --- identity ----------------------------------------------------------
    ("GET", "/api/me", AUTHENTICATED),

    # --- notifications (#116): everyone has a list, scoped to their own rows -
    ("GET", "/api/notifications", EMPLOYEE_SELF),
    ("POST", "/api/notifications/1/read", EMPLOYEE_SELF),
    ("POST", "/api/notifications/read-all", EMPLOYEE_SELF),
    ("POST", "/api/notifications/1/dismiss", EMPLOYEE_SELF),
    ("POST", "/api/notifications/dismiss-all", EMPLOYEE_SELF),

    # --- audit trail (#63): read by the admin only, written by the server ---
    ("GET", "/api/audit-events", ADMIN_ONLY),

    # --- payroll and leave: scoped by row-level security, not by role -------
    ("GET", "/api/payslips", EMPLOYEE_SELF),
    ("GET", "/api/leave-requests", EMPLOYEE_SELF),
    ("POST", "/api/leave-requests", EMPLOYEE_SELF),
    ("GET", "/api/employees", EMPLOYEE_SELF),

    # --- leave decisions: admin only ---------------------------------------
    ("POST", "/api/leave-requests/1/approve", ADMIN_ONLY),
    ("POST", "/api/leave-requests/1/reject", ADMIN_ONLY),

    # --- accounts ----------------------------------------------------------
    ("GET", "/api/users", ADMIN_ONLY),
    ("POST", "/api/users", ADMIN_ONLY),
    # Account lifecycle (#62): edit, deactivate, resend the activation link.
    ("PATCH", "/api/users/USR-999", ADMIN_ONLY),
    ("POST", "/api/users/USR-999/deactivate", ADMIN_ONLY),
    ("POST", "/api/users/USR-999/activation", ADMIN_ONLY),
    ("POST", "/api/employees", ADMIN_ONLY),

    # --- billing -----------------------------------------------------------
    ("GET", "/api/clients", BILLING),
    ("POST", "/api/clients", BILLING),
    ("GET", "/api/suppliers", BILLING),
    ("POST", "/api/suppliers", BILLING),
    ("GET", "/api/invoices", BILLING),
    ("GET", "/api/invoices/1", BILLING),
    # By internal id since #86; the generic /api/invoices/1 normalisation below covers it.
    ("GET", "/api/invoices/1/download", BILLING),

    # --- bookkeeping: narrower than billing, rh excluded --------------------
    ("POST", "/api/invoices", ADMIN_ONLY),
    # Correcting a draft (#125): admin only, like creation - the accountant
    # reviews invoices and must not edit what she reviews.
    ("PATCH", "/api/invoices/1", ADMIN_ONLY),
    # Verification before sending (#118): the admin submits and sends, the
    # accountant approves or rejects.
    ("POST", "/api/invoices/1/submit", ADMIN_ONLY),
    ("POST", "/api/invoices/1/approve", ACCOUNTANT_ONLY),
    ("POST", "/api/invoices/1/reject", ACCOUNTANT_ONLY),
    ("POST", "/api/invoices/1/send", ADMIN_ONLY),
    ("POST", "/api/supplier-invoices", BOOKKEEPING),
    ("PATCH", "/api/invoices/1/processing-status", BOOKKEEPING),
    ("GET", "/api/periods", BOOKKEEPING),
    ("GET", "/api/periods/2026-01", BOOKKEEPING),
    ("POST", "/api/periods/2026-01/close", BOOKKEEPING),
]

ROLES = ["anonymous", "employee", "accountant", "admin"]

ALLOWED_THROUGH = {200, 201, 204, 400, 404, 409, 422}
REFUSED = {401, 403}


def _may_reach(rule: str, role: str) -> bool:
    if rule == PUBLIC:
        return True
    if role == "anonymous":
        return False
    if rule in (AUTHENTICATED, EMPLOYEE_SELF):
        return True
    if rule == ADMIN_ONLY:
        return role == "admin"
    if rule == BOOKKEEPING:
        return role in ("admin", "accountant")
    if rule == ACCOUNTANT_ONLY:
        return role == "accountant"
    if rule == BILLING:
        return role in ("admin", "accountant")  # 'rh' has no fixture account
    raise AssertionError(f"unknown rule {rule!r}")


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("method,path,rule", ROUTES,
                         ids=[f"{m}:{p}" for m, p, _ in ROUTES])
def test_authorisation_matrix(client, identities, method, path, rule, role):
    """Each identity either reaches the route or is refused - never silently both."""
    headers = identities[role]["headers"]
    response = client.request(method, path, headers=headers, json={})

    expected_through = _may_reach(rule, role)
    got_through = response.status_code in ALLOWED_THROUGH
    got_refused = response.status_code in REFUSED

    assert got_through or got_refused, (
        f"{method} {path} as {role} returned {response.status_code}, which is "
        f"neither a clear refusal nor a request that got through. A 500 here "
        f"usually means the route crashed before deciding."
    )

    if expected_through:
        assert got_through, (
            f"{method} {path} should be reachable by {role} ({rule}), "
            f"but returned {response.status_code}"
        )
    else:
        assert got_refused, (
            f"{method} {path} must be refused for {role} ({rule}), "
            f"but returned {response.status_code}"
        )


def test_every_route_is_covered(app):
    """The matrix must list every route, so a new one cannot arrive untested.

    Without this, adding an endpoint and forgetting to add it here would leave
    it unprotected and the suite would still pass - which is precisely the
    failure mode the audit found.
    """
    declared = set()
    for method, path, _ in ROUTES:
        # Normalise the sample ids back to their templates.
        normalised = (path
                      .replace("/api/leave-requests/1/", "/api/leave-requests/{req_id}/")
                      .replace("/api/notifications/1/", "/api/notifications/{notification_id}/")
                      .replace("/api/invoices/1/processing-status",
                               "/api/invoices/{invoice_id}/processing-status")
                      .replace("/api/invoices/1", "/api/invoices/{invoice_id}")
                      .replace("/api/periods/2026-01/close", "/api/periods/{month}/close")
                      .replace("/api/periods/2026-01", "/api/periods/{month}")
                      .replace("/api/users/USR-999", "/api/users/{user_id}"))
        declared.add((method, normalised))

    actual = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api"):
            continue
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}:
            actual.add((method, path))

    missing = actual - declared
    assert not missing, (
        "These routes are not in the authorisation matrix, so nothing checks "
        f"who may call them: {sorted(missing)}"
    )

    stale = declared - actual
    assert not stale, (
        f"These matrix entries no longer match a real route: {sorted(stale)}"
    )
