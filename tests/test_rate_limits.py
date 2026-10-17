"""Limits on sign-in and the public routes (#175).

Before this, sign-in accepted any number of password guesses and
forgot-password any number of reset e-mails. These tests pin each limit, what
a refused caller is told - nothing more than a wrong password tells them, for
a locked account - and that the counters hold no address in clear.

The limits are lowered per test with monkeypatch, so a test does not need
dozens of requests. TestClient always comes from the same address.
"""

import os

import pytest
from sqlalchemy import create_engine, text

from account_flow import make_account, sign_in
from db_errors import INSUFFICIENT_PRIVILEGE, refused_with

DOMAIN = "limits.test.tn"


@pytest.fixture
def limits(monkeypatch):
    from app.core.config import settings

    def set_(**values):
        for name, value in values.items():
            monkeypatch.setattr(settings, name, value)
    return set_


def counted(database, bucket):
    with database.connect() as c:
        return c.execute(text("SELECT count(*) FROM auth_attempts WHERE bucket = :b"), {"b": bucket}).scalar_one()


def age_attempts(database, minutes):
    """Move every counted attempt `minutes` into the past, as if time had passed."""
    with database.connect() as c:
        c.execute(text("UPDATE auth_attempts SET created_at = created_at - make_interval(mins => :m)"),
                  {"m": minutes})
        c.commit()


# --- One account: locked after repeated failures ---------------------------------

def test_an_account_locks_after_too_many_failures(client, database, limits):
    limits(LOGIN_MAX_FAILURES=3)
    email = f"locked@{DOMAIN}"
    make_account(database, email)
    wrong = [sign_in(client, email, "wrong-password") for _ in range(3)]
    assert [r.status_code for r in wrong] == [401, 401, 401]

    locked = sign_in(client, email)
    assert locked.status_code == 401, "the right password is refused while locked"
    assert locked.json() == wrong[0].json(), "a locked account says nothing a wrong password does not"
    assert "Retry-After" not in locked.headers


def test_an_unknown_email_locks_the_same_way(client, database, limits):
    """Otherwise the lock itself would tell which e-mails have accounts."""
    limits(LOGIN_MAX_FAILURES=2)
    email = f"nobody@{DOMAIN}"
    answers = [sign_in(client, email, "guess").json() for _ in range(4)]
    assert all(a == answers[0] for a in answers)
    assert counted(database, "login_account") == 2, "counted like a real account, and no further while locked"


def test_the_lock_lifts_when_the_failures_age_out(client, database, limits):
    limits(LOGIN_MAX_FAILURES=2, LOGIN_LOCKOUT_MINUTES=15)
    email = f"later@{DOMAIN}"
    make_account(database, email)
    for _ in range(2):
        sign_in(client, email, "wrong-password")
    assert sign_in(client, email).status_code == 401
    age_attempts(database, 16)
    assert sign_in(client, email).status_code == 200


def test_case_does_not_give_a_fresh_counter(client, database, limits):
    limits(LOGIN_MAX_FAILURES=2)
    email = f"case@{DOMAIN}"
    make_account(database, email)
    sign_in(client, email, "wrong-password")
    sign_in(client, email.upper(), "wrong-password")
    assert sign_in(client, email).status_code == 401, "Case@ and case@ share one counter"


def test_a_success_resets_the_account_counter(client, database, limits):
    limits(LOGIN_MAX_FAILURES=3)
    email = f"reset@{DOMAIN}"
    make_account(database, email)
    for _ in range(2):
        assert sign_in(client, email, "wrong-password").status_code == 401
    assert sign_in(client, email).status_code == 200
    for _ in range(2):
        assert sign_in(client, email, "wrong-password").status_code == 401
    assert sign_in(client, email).status_code == 200, "two failures since the last success: not locked"


# --- One address: failures across accounts ------------------------------------

def test_one_address_failing_on_many_accounts_gets_429(client, limits):
    limits(LOGIN_MAX_FAILURES_PER_IP=3)
    answers = [sign_in(client, f"user{n}@{DOMAIN}", "guess") for n in range(4)]
    assert [r.status_code for r in answers] == [401, 401, 401, 429]
    refused = answers[-1]
    assert refused.json()["code"] == "auth.too_many_requests"
    assert 1 <= int(refused.headers["Retry-After"]) <= 15 * 60


def test_successful_sign_ins_do_not_count_against_the_address(client, database, limits):
    """An office behind one address signs in all morning without being refused."""
    limits(LOGIN_MAX_FAILURES_PER_IP=2)
    for n in range(5):
        email = f"staff{n}@{DOMAIN}"
        make_account(database, email)
        assert sign_in(client, email).status_code == 200


# --- Public routes, per address -------------------------------------------------

@pytest.mark.parametrize("path, body", [
    ("/api/forgot-password", {"email": f"someone@{DOMAIN}"}),
    ("/api/reset-password", {"token": "not-a-real-token", "newPassword": "a-long-enough-password"}),
    ("/api/activate", {"token": "not-a-real-token", "newPassword": "a-long-enough-password"}),
    ("/api/login", {"email": f"someone@{DOMAIN}", "password": "guess"}),
    ("/api/contact", {"name": "Amira", "email": f"amira@{DOMAIN}", "topic": "other",
                      "message": "A question about your services."}),
])
def test_each_public_route_is_limited_per_address(client, limits, path, body):
    limits(PUBLIC_REQUESTS_PER_MINUTE=3)
    answers = [client.post(path, json=body) for _ in range(4)]
    assert all(r.status_code != 429 for r in answers[:3]), [r.status_code for r in answers]
    assert answers[3].status_code == 429
    assert answers[3].json()["code"] == "auth.too_many_requests"
    assert 1 <= int(answers[3].headers["Retry-After"]) <= 60


def test_the_public_limit_is_shared_across_routes(client, limits):
    limits(PUBLIC_REQUESTS_PER_MINUTE=2)
    client.post("/api/forgot-password", json={"email": f"a@{DOMAIN}"})
    client.post("/api/login", json={"email": f"a@{DOMAIN}", "password": "guess"})
    assert client.post("/api/forgot-password", json={"email": f"a@{DOMAIN}"}).status_code == 429


def test_the_public_limit_refuses_in_the_caller_s_language(client, limits):
    limits(PUBLIC_REQUESTS_PER_MINUTE=1)
    client.post("/api/forgot-password", json={"email": f"a@{DOMAIN}"})
    refused = client.post("/api/forgot-password", json={"email": f"a@{DOMAIN}"},
                          headers={"Accept-Language": "fr"})
    assert refused.status_code == 429 and refused.json()["detail"].startswith("Trop de tentatives")


@pytest.mark.identity("employee")
def test_signed_in_routes_are_not_limited(client, identities, limits):
    limits(PUBLIC_REQUESTS_PER_MINUTE=1)
    for _ in range(3):
        assert client.get("/api/me", headers=identities["employee"]["headers"]).status_code == 200


# --- Reset e-mails, per account ----------------------------------------------------

def test_reset_mails_are_capped_per_account_silently(client, database, mailbox, limits):
    limits(RESET_MAILS_PER_HOUR=2)
    email = f"inbox@{DOMAIN}"
    make_account(database, email)
    answers = [client.post("/api/forgot-password", json={"email": email}) for _ in range(4)]
    assert all(r.status_code == 200 for r in answers)
    assert all(r.json() == answers[0].json() for r in answers), "the answer never changes"
    assert len([m for m in mailbox if m["to"] == email]) == 2


# --- The counters themselves -------------------------------------------------------

def test_no_address_or_e_mail_is_stored_in_clear(client, database):
    email = f"private@{DOMAIN}"
    sign_in(client, email, "guess")
    with database.connect() as c:
        rows = c.execute(text("SELECT bucket, key_hash FROM auth_attempts")).all()
    assert rows, "the attempt was counted"
    for bucket, key in rows:
        assert len(key) == 64 and "@" not in key and "testclient" not in key, (bucket, key)


def test_the_application_role_cannot_touch_the_counters():
    """Only through the functions: a flaw in the API cannot read or wipe them."""
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            with refused_with(INSUFFICIENT_PRIVILEGE):
                conn.execute(text("SELECT count(*) FROM auth_attempts"))
            conn.rollback()
            with refused_with(INSUFFICIENT_PRIVILEGE):
                conn.execute(text("DELETE FROM auth_attempts"))
    finally:
        engine.dispose()
