"""The account lifecycle (#62): who may still sign in, and for how long.

One test or more per acceptance criterion of the issue:
inactive accounts are refused, deactivation and role or password changes
revoke sessions already issued, a reset token is never a session, reset and
activation tokens are stored as hashes and work once, a new account cannot sign
in before activation, and login time does not reveal whether an account exists.
"""

import statistics
import time
from datetime import datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy import text

from account_flow import bearer, link_token, make_account, sign_in

pytestmark = pytest.mark.identity("admin")

DOMAIN = "lifecycle-test.tn"


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        # account_tokens follow their user (ON DELETE CASCADE).
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


def token_for(client, email):
    response = sign_in(client, email)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def actions(database, user_id):
    with database.connect() as c:
        return [r[0] for r in c.execute(text(
            "SELECT action FROM audit_events WHERE entity = 'user' AND entity_id = :u ORDER BY id"),
            {"u": user_id})]


# --- Inactive accounts, and sessions revoked on the spot -----------------------

def test_an_inactive_account_cannot_sign_in(client, database):
    make_account(database, f"gone@{DOMAIN}", active=False)
    response = sign_in(client, f"gone@{DOMAIN}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials", "the same answer as a wrong password"


def test_deactivation_revokes_a_token_already_issued(client, admin, database):
    user_id = make_account(database, f"leaver@{DOMAIN}", role="accountant")
    token = token_for(client, f"leaver@{DOMAIN}")
    assert client.get("/api/me", headers=bearer(token)).status_code == 200
    assert client.get("/api/invoices", headers=bearer(token)).status_code == 200

    deactivated = client.post(f"/api/users/{user_id}/deactivate", headers=admin)
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["isActive"] is False

    assert client.get("/api/me", headers=bearer(token)).status_code == 401
    assert client.get("/api/invoices", headers=bearer(token)).status_code == 401
    assert sign_in(client, f"leaver@{DOMAIN}").status_code == 401
    assert actions(database, user_id) == ["user.deactivated"]


def test_a_role_change_revokes_tokens_and_reactivation_works(client, admin, database):
    user_id = make_account(database, f"mover@{DOMAIN}", role="accountant")
    token = token_for(client, f"mover@{DOMAIN}")

    changed = client.patch(f"/api/users/{user_id}", headers=admin, json={"role": "employee"})
    assert changed.status_code == 200 and changed.json()["role"] == "employee"
    assert client.get("/api/me", headers=bearer(token)).status_code == 401, "a token of the old role"

    # A fresh sign-in carries the new role.
    fresh = token_for(client, f"mover@{DOMAIN}")
    assert client.get("/api/me", headers=bearer(fresh)).json()["role"] == "employee"

    client.patch(f"/api/users/{user_id}", headers=admin, json={"isActive": False})
    client.patch(f"/api/users/{user_id}", headers=admin, json={"isActive": True})
    assert sign_in(client, f"mover@{DOMAIN}").status_code == 200, "reactivated"
    assert actions(database, user_id) == ["user.role_changed", "user.deactivated", "user.reactivated"]


def test_editing_a_name_does_not_sign_anyone_out(client, admin, database):
    user_id = make_account(database, f"renamed@{DOMAIN}")
    token = token_for(client, f"renamed@{DOMAIN}")
    response = client.patch(f"/api/users/{user_id}", headers=admin, json={"lastName": "Married"})
    assert response.json()["lastName"] == "Married"
    assert client.get("/api/me", headers=bearer(token)).status_code == 200
    assert actions(database, user_id) == ["user.updated"]


def test_an_unchanged_edit_records_nothing(client, admin, database):
    user_id = make_account(database, f"same@{DOMAIN}")
    assert client.patch(f"/api/users/{user_id}", headers=admin, json={"role": "employee"}).status_code == 200
    assert actions(database, user_id) == []


def test_an_admin_cannot_demote_or_deactivate_themselves(client, admin, identities):
    me = identities["admin"]["user_id"]
    assert client.patch(f"/api/users/{me}", headers=admin, json={"role": "employee"}).status_code == 409
    assert client.post(f"/api/users/{me}/deactivate", headers=admin).status_code == 409
    assert client.get("/api/me", headers=admin).json()["role"] == "admin"


# --- Reset tokens: never a session, stored hashed, single use -------------------

def test_a_reset_token_is_not_a_session(client, database, mailbox):
    user_id = make_account(database, f"reset@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"reset@{DOMAIN}"})
    reset = link_token(mailbox, f"reset@{DOMAIN}")
    assert client.get("/api/me", headers=bearer(reset)).status_code == 401

    # Imported here, not at the top: app.core.config refuses to load before
    # the database fixture has set DATABASE_URL, and modules are collected first.
    from app.core.config import settings

    # Nor is a JWT signed with the session key for another purpose, the shape
    # the old reset token had: only typ "access" opens a session.
    forged = jwt.encode({"sub": user_id, "purpose": "reset", "ver": 0,
                         "exp": datetime.utcnow() + timedelta(hours=1)},
                        settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert client.get("/api/me", headers=bearer(forged)).status_code == 401


def test_only_the_hash_of_a_reset_token_is_stored(client, database, mailbox):
    # Imported here, not at the top: app.core.config refuses to load before
    # the database fixture has set DATABASE_URL, and modules are collected first.
    from app.core.security import hash_account_token

    user_id = make_account(database, f"hashed@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"hashed@{DOMAIN}"})
    reset = link_token(mailbox, f"hashed@{DOMAIN}")
    with database.connect() as c:
        stored = c.execute(text("SELECT token_hash FROM account_tokens WHERE user_id = :u"),
                           {"u": user_id}).scalar_one()
        row = c.execute(text("SELECT row_to_json(u)::text FROM users u WHERE id = :u"),
                        {"u": user_id}).scalar_one()
    assert stored == hash_account_token(reset) and stored != reset
    assert reset not in row


def test_a_reset_works_once_and_signs_out_old_sessions(client, database, mailbox):
    make_account(database, f"once@{DOMAIN}")
    old_session = token_for(client, f"once@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"once@{DOMAIN}"})
    reset = link_token(mailbox, f"once@{DOMAIN}")

    body = {"token": reset, "newPassword": "a-brand-new-password"}
    assert client.post("/api/reset-password", json=body).status_code == 200
    assert client.post("/api/reset-password", json=body).status_code == 400, "single use"
    assert client.get("/api/me", headers=bearer(old_session)).status_code == 401
    assert sign_in(client, f"once@{DOMAIN}", "a-brand-new-password").status_code == 200


def test_an_expired_or_superseded_reset_link_is_refused(client, database, mailbox):
    user_id = make_account(database, f"late@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"late@{DOMAIN}"})
    first = link_token(mailbox, f"late@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"late@{DOMAIN}"})
    second = link_token(mailbox, f"late@{DOMAIN}")
    assert client.post("/api/reset-password", json={
        "token": first, "newPassword": "a-brand-new-password"}).status_code == 400, "superseded"

    with database.connect() as c:
        c.execute(text("UPDATE account_tokens SET created_at = now() - interval '2 hours',"
                       " expires_at = now() - interval '1 hour' WHERE user_id = :u"), {"u": user_id})
    assert client.post("/api/reset-password", json={
        "token": second, "newPassword": "a-brand-new-password"}).status_code == 400, "expired"


def test_a_weak_password_is_refused(client, database, mailbox):
    make_account(database, f"weak@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"weak@{DOMAIN}"})
    reset = link_token(mailbox, f"weak@{DOMAIN}")
    assert client.post("/api/reset-password", json={"token": reset, "newPassword": "short"}).status_code == 422
    assert client.post("/api/reset-password", json={"token": reset, "newPassword": "x" * 73}).status_code == 422
    # The refusal did not spend the link.
    assert client.post("/api/reset-password", json={
        "token": reset, "newPassword": "a-long-enough-password"}).status_code == 200


def test_an_inactive_account_gets_no_reset_link(client, database, mailbox):
    make_account(database, f"inactive@{DOMAIN}", active=False)
    assert client.post("/api/forgot-password", json={"email": f"inactive@{DOMAIN}"}).status_code == 200
    assert mailbox == []


# --- New accounts: no password returned, activation first ----------------------

def test_a_new_account_gets_an_activation_link_and_no_password(client, admin, database, mailbox):
    email = f"newcomer@{DOMAIN}"
    created = client.post("/api/users", headers=admin, json={
        "email": email, "firstName": "New", "lastName": "Comer", "role": "employee"})
    assert created.status_code == 201, created.text
    assert set(created.json()) == {"id", "email", "activationEmailSent"}
    assert created.json()["activationEmailSent"] is True
    assert "temporary password" not in mailbox[-1]["body"].lower()
    with database.connect() as c:
        verified = c.execute(text('SELECT "isVerified" FROM users WHERE email = :e'), {"e": email}).scalar_one()
    assert verified is False

    # No password exists yet, so none can work before activation.
    assert sign_in(client, email).status_code == 401

    activation = link_token(mailbox, email)
    assert client.post("/api/reset-password", json={
        "token": activation, "newPassword": "my-first-password"}).status_code == 400, \
        "an activation link is not a reset link"
    assert client.post("/api/activate", json={
        "token": activation, "newPassword": "my-first-password"}).status_code == 200
    assert sign_in(client, email, "my-first-password").status_code == 200
    assert client.post("/api/activate", json={
        "token": activation, "newPassword": "my-first-password"}).status_code == 400, "single use"


def test_resending_the_activation_link_replaces_the_old_one(client, admin, mailbox):
    email = f"resend@{DOMAIN}"
    user_id = client.post("/api/users", headers=admin, json={
        "email": email, "firstName": "Re", "lastName": "Send", "role": "employee"}).json()["id"]
    first = link_token(mailbox, email)
    resent = client.post(f"/api/users/{user_id}/activation", headers=admin)
    assert resent.status_code == 200 and resent.json()["activationEmailSent"] is True
    second = link_token(mailbox, email)
    assert first != second
    assert client.post("/api/activate", json={"token": first, "newPassword": "my-first-password"}).status_code == 400
    assert client.post("/api/activate", json={"token": second, "newPassword": "my-first-password"}).status_code == 200
    assert client.post(f"/api/users/{user_id}/activation", headers=admin).status_code == 409, "already active"


# --- Login time does not reveal whether an account exists ----------------------

def test_login_takes_as_long_for_an_unknown_email(client, database):
    make_account(database, f"timing@{DOMAIN}")

    def median_ms(email):
        samples = []
        for _ in range(7):
            start = time.perf_counter()
            assert sign_in(client, email, "wrong-password").status_code == 401
            samples.append((time.perf_counter() - start) * 1000)
        return statistics.median(samples)

    known = median_ms(f"timing@{DOMAIN}")
    unknown = median_ms(f"nobody@{DOMAIN}")
    # The audit measured 24 ms against 292 ms. Both now run one bcrypt check;
    # the bound is loose so a busy CI runner cannot make it flaky.
    assert unknown > known / 3, f"unknown e-mail {unknown:.0f} ms vs known {known:.0f} ms"
