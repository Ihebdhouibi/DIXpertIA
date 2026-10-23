"""Locked out, then back in (#220).

On staging, an admin "changed" their password in Settings, a form that sent
nothing; the new password then failed, the e-mail locked (#175), and the real
password was refused too, as "wrong". These pin the three fixes: a reset or an
activation lifts the lock at once; changing one's password works, signs other
sessions out, and cannot be used to guess the current one; the database
refuses to change someone else's.
"""

import os
import secrets

import pytest
from sqlalchemy import create_engine, text

from account_flow import PASSWORD, bearer, link_token, make_account, sign_in
from db_errors import INSUFFICIENT_PRIVILEGE, refused_with

pytestmark = pytest.mark.identity("admin")

DOMAIN = "password-test.tn"
# Generated per run, like account_flow.PASSWORD: nothing to leak or reuse.
NEW_PASSWORD = secrets.token_hex(12)


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("TRUNCATE audit_events"))
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})
        c.commit()


@pytest.fixture
def admin(identities):
    return identities["admin"]["headers"]


@pytest.fixture
def limits(monkeypatch):
    from app.core.config import settings

    def set_(**values):
        for name, value in values.items():
            monkeypatch.setattr(settings, name, value)
    return set_


def lock(client, email, failures):
    for _ in range(failures):
        sign_in(client, email, "wrong-password")
    assert sign_in(client, email).status_code == 429, "locked"


# --- A reset or an activation lifts the lock -----------------------------------------

def test_a_password_reset_lifts_the_lock_at_once(client, database, mailbox, limits):
    limits(LOGIN_MAX_FAILURES=2)
    email = f"resetlock@{DOMAIN}"
    make_account(database, email)
    lock(client, email, 2)

    client.post("/api/forgot-password", json={"email": email})
    reset = client.post("/api/reset-password", json={"token": link_token(mailbox, email),
                                                      "newPassword": NEW_PASSWORD})
    assert reset.status_code == 200, reset.text
    assert sign_in(client, email, NEW_PASSWORD).status_code == 200, "no waiting out the lock"


def test_an_activation_lifts_the_lock(client, admin, mailbox, limits):
    limits(LOGIN_MAX_FAILURES=2)
    email = f"activatelock@{DOMAIN}"
    created = client.post("/api/users", headers=admin, json={
        "email": email, "firstName": "New", "lastName": "Person", "role": "employee"})
    assert created.status_code == 201, created.text
    lock(client, email, 2)
    activated = client.post("/api/activate", json={"token": link_token(mailbox, email), "newPassword": NEW_PASSWORD})
    assert activated.status_code == 200, activated.text
    assert sign_in(client, email, NEW_PASSWORD).status_code == 200


# --- Changing one's own password ---------------------------------------------------------

def test_changing_ones_password_works_and_signs_other_sessions_out(client, database):
    email = f"change@{DOMAIN}"
    make_account(database, email)
    old_session = sign_in(client, email).json()["access_token"]
    changed = client.post("/api/me/password", headers=bearer(old_session),
                          json={"currentPassword": PASSWORD, "newPassword": NEW_PASSWORD})
    assert changed.status_code == 200, changed.text
    fresh = changed.json()["access_token"]

    assert client.get("/api/me", headers=bearer(old_session)).status_code == 401, "other sessions are out"
    assert client.get("/api/me", headers=bearer(fresh)).status_code == 200, "this browser keeps going"
    assert sign_in(client, email, PASSWORD).status_code == 401, "the old password no longer works"
    assert sign_in(client, email, NEW_PASSWORD).status_code == 200
    with database.connect() as c:
        logged = c.execute(text("SELECT count(*) FROM audit_events WHERE action = 'user.password_changed'")).scalar()
    assert logged == 1


def test_a_wrong_current_password_is_refused_and_counts_towards_the_lock(client, database, limits):
    limits(LOGIN_MAX_FAILURES=3)
    email = f"guess@{DOMAIN}"
    make_account(database, email)
    session = sign_in(client, email).json()["access_token"]

    def change(current):
        return client.post("/api/me/password", headers=bearer(session),
                           json={"currentPassword": current, "newPassword": NEW_PASSWORD})

    answers = [change("not-it").status_code for _ in range(3)]
    assert answers == [400, 400, 400]
    assert change("not-it").json()["code"] == "auth.locked", "it cannot be used to guess the password"
    assert change(PASSWORD).status_code == 429, "even the right one, while locked"


def test_the_new_password_follows_the_rules(client, database):
    email = f"weak@{DOMAIN}"
    make_account(database, email)
    session = sign_in(client, email).json()["access_token"]
    weak = client.post("/api/me/password", headers=bearer(session),
                       json={"currentPassword": PASSWORD, "newPassword": "short"})
    assert weak.status_code == 422 and weak.json()["code"] == "password.too_short"
    assert sign_in(client, email, PASSWORD).status_code == 200, "nothing changed"


def test_the_database_refuses_to_change_someone_elses_password(identities):
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT set_config('app.user_id', :u, false),"
                              " set_config('app.user_role', 'admin', false)"), {"u": identities["admin"]["user_id"]})
            with refused_with(INSUFFICIENT_PRIVILEGE):
                conn.execute(text("SELECT auth_set_own_password(:other, 'x')"),
                             {"other": identities["employee"]["user_id"]})
    finally:
        engine.dispose()
