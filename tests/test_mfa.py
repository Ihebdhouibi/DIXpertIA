"""Two-factor authentication (#44), one test or more per acceptance criterion.

Enrolment completes only after a working code; the secret is encrypted at
rest and never in a response; recovery codes are single use and stored as
HMACs; sign-in is two steps with a short-lived, single-purpose challenge
token; wrong codes lock code entry; a used code cannot be replayed; disabling
needs the password; a role that requires two-factor enrols at sign-in; the
admin resets a lost phone; the application role cannot read the tables, and
the functions refuse to change someone else's second factor.
"""

import os
import time
from datetime import datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet
from jose import jwt
from sqlalchemy import create_engine, text

from account_flow import PASSWORD, bearer, make_account, sign_in
from db_errors import INSUFFICIENT_PRIVILEGE, refused_with

pytestmark = pytest.mark.identity("admin")

DOMAIN = "mfa-test.tn"


@pytest.fixture(autouse=True)
def mfa_on(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "MFA_REQUIRED_ROLES", frozenset({"admin", "accountant"}))
    monkeypatch.setattr(settings, "MFA_MAX_FAILURES", 5)


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        for table in ("user_mfa_recovery", "user_mfa"):
            c.execute(text(f"DELETE FROM {table} WHERE user_id IN (SELECT id FROM users WHERE email LIKE :d)"),
                      {"d": f"%@{DOMAIN}"})
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})
        c.commit()


def session_for(client, database, name, role="employee"):
    email = f"{name}@{DOMAIN}"
    make_account(database, email, role)
    response = sign_in(client, email)
    assert response.status_code == 200, response.text
    return email, response.json()["access_token"]


def code_at(secret, offset_steps=0):
    return pyotp.TOTP(secret).at(time.time() + 30 * offset_steps)


def enrol(client, token):
    """Set up and confirm with the current code. Returns (secret, codes, fresh token)."""
    setup = client.post("/api/mfa/setup", headers=bearer(token))
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    confirmed = client.post("/api/mfa/confirm", headers=bearer(token), json={"code": code_at(secret)})
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    return secret, body["recoveryCodes"], body["access_token"]


# --- Enrolment -------------------------------------------------------------------------

def test_setup_gives_a_qr_code_and_a_secret_but_is_not_active_until_a_code_is_proven(client, database):
    _, token = session_for(client, database, "setup")
    setup = client.post("/api/mfa/setup", headers=bearer(token)).json()
    assert setup["qrCode"].startswith("data:image/svg+xml;base64,")
    assert setup["otpauthUri"].startswith("otpauth://totp/")
    assert len(setup["secret"]) >= 16
    assert client.get("/api/mfa", headers=bearer(token)).json()["enabled"] is False

    wrong = client.post("/api/mfa/confirm", headers=bearer(token), json={"code": "000000"})
    assert wrong.status_code == 400 and wrong.json()["code"] == "mfa.wrong_code"
    assert client.get("/api/mfa", headers=bearer(token)).json()["enabled"] is False


def test_confirming_enables_it_and_signs_older_sessions_out(client, database):
    _, token = session_for(client, database, "confirm")
    _, codes, fresh = enrol(client, token)
    assert len(codes) == 10 and len(set(codes)) == 10
    assert client.get("/api/me", headers=bearer(token)).status_code == 401, "the session before enrolment"
    status = client.get("/api/mfa", headers=bearer(fresh)).json()
    assert status["enabled"] is True and status["recoveryCodesLeft"] == 10


def test_the_secret_is_encrypted_at_rest_and_never_in_a_response(client, database):
    email, token = session_for(client, database, "atrest")
    secret, codes, fresh = enrol(client, token)
    with database.connect() as c:
        stored = c.execute(text(
            "SELECT m.secret_enc FROM user_mfa m JOIN users u ON u.id = m.user_id WHERE u.email = :e"),
            {"e": email}).scalar_one()
        hashes = c.execute(text(
            "SELECT r.code_hash FROM user_mfa_recovery r JOIN users u ON u.id = r.user_id WHERE u.email = :e"),
            {"e": email}).scalars().all()
    assert secret not in stored and stored.startswith("gAAAA"), "Fernet ciphertext, not the secret"
    assert not set(codes) & set(hashes), "recovery codes are stored as HMACs only"
    for path in ("/api/mfa", "/api/me"):
        body = client.get(path, headers=bearer(fresh)).text
        assert secret not in body and "secret_enc" not in body, path
        assert not any(code in body for code in codes), path


# --- Signing in in two steps ------------------------------------------------------------

def test_sign_in_with_it_on_gives_a_challenge_not_a_session(client, database):
    email, token = session_for(client, database, "twostep")
    secret, _, _ = enrol(client, token)
    first = sign_in(client, email).json()
    assert first["mfaRequired"] is True and first["access_token"] is None and first["user"] is None
    challenge = first["challengeToken"]
    assert client.get("/api/me", headers=bearer(challenge)).status_code == 401, "a challenge is not a session"

    # The enrolment used the current step: the next one is fresh, within the drift allowed.
    done = client.post("/api/mfa/verify", json={"challengeToken": challenge, "code": code_at(secret, 1)})
    assert done.status_code == 200, done.text
    assert client.get("/api/me", headers=bearer(done.json()["access_token"])).json()["email"] == email


def test_a_code_cannot_be_replayed(client, database):
    email, token = session_for(client, database, "replay")
    secret, _, _ = enrol(client, token)
    code = code_at(secret, 1)
    first = client.post("/api/mfa/verify", json={"challengeToken": sign_in(client, email).json()["challengeToken"],
                                                  "code": code})
    assert first.status_code == 200
    again = client.post("/api/mfa/verify", json={"challengeToken": sign_in(client, email).json()["challengeToken"],
                                                  "code": code})
    assert again.status_code == 400 and again.json()["code"] == "mfa.wrong_code"
    enrolment_code = client.post("/api/mfa/verify", json={
        "challengeToken": sign_in(client, email).json()["challengeToken"], "code": code_at(secret)})
    assert enrolment_code.status_code == 400, "the enrolment's own code is spent too"


def test_wrong_codes_lock_code_entry(client, database, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MFA_MAX_FAILURES", 3)
    email, token = session_for(client, database, "brute")
    secret, _, _ = enrol(client, token)
    challenge = sign_in(client, email).json()["challengeToken"]
    answers = [client.post("/api/mfa/verify", json={"challengeToken": challenge, "code": "000000"}).status_code
               for _ in range(3)]
    assert answers == [400, 400, 400]
    locked = client.post("/api/mfa/verify", json={"challengeToken": challenge, "code": code_at(secret, 1)})
    assert locked.status_code == 429, "even the right code, once locked"
    assert "Retry-After" in locked.headers


def test_an_expired_or_wrong_purpose_token_is_refused(client, database):
    email, token = session_for(client, database, "expired")
    secret, _, fresh = enrol(client, token)
    from app.core.config import settings

    user_id = client.get("/api/me", headers=bearer(fresh)).json()["id"]
    expired = jwt.encode({"sub": user_id, "ver": 1, "typ": "mfa_challenge",
                          "exp": datetime.utcnow() - timedelta(minutes=1)}, settings.SECRET_KEY, algorithm="HS256")
    for wrong in (expired, fresh):
        response = client.post("/api/mfa/verify", json={"challengeToken": wrong, "code": code_at(secret, 1)})
        assert response.status_code == 401 and response.json()["code"] == "mfa.expired"


def test_a_recovery_code_works_once(client, database):
    email, token = session_for(client, database, "recovery")
    _, codes, _ = enrol(client, token)

    def with_recovery(code):
        challenge = sign_in(client, email).json()["challengeToken"]
        return client.post("/api/mfa/verify", json={"challengeToken": challenge, "recoveryCode": code})

    used = with_recovery(codes[0].upper())
    assert used.status_code == 200, "case and dash do not matter"
    assert client.get("/api/mfa", headers=bearer(used.json()["access_token"])).json()["recoveryCodesLeft"] == 9
    assert with_recovery(codes[0]).status_code == 400, "spent"
    assert with_recovery("aaaaa-aaaaa").status_code == 400


def test_new_recovery_codes_need_a_current_code_and_replace_the_old(client, database):
    email, token = session_for(client, database, "renew")
    secret, old, fresh = enrol(client, token)
    assert client.post("/api/mfa/recovery-codes", headers=bearer(fresh), json={"code": "000000"}).status_code == 400
    renewed = client.post("/api/mfa/recovery-codes", headers=bearer(fresh), json={"code": code_at(secret, 1)})
    assert renewed.status_code == 200
    new = renewed.json()["recoveryCodes"]
    assert len(new) == 10 and not set(new) & set(old)
    challenge = sign_in(client, email).json()["challengeToken"]
    stale = client.post("/api/mfa/verify", json={"challengeToken": challenge, "recoveryCode": old[1]})
    assert stale.status_code == 400, "the old codes stop working"


# --- Turning it off -------------------------------------------------------------------

def test_disabling_needs_the_password(client, database):
    email, token = session_for(client, database, "disable")
    _, _, fresh = enrol(client, token)
    wrong = client.post("/api/mfa/disable", headers=bearer(fresh), json={"password": "wrong-password"})
    assert wrong.status_code == 401
    off = client.post("/api/mfa/disable", headers=bearer(fresh), json={"password": PASSWORD})
    assert off.status_code == 200
    assert client.get("/api/me", headers=bearer(fresh)).status_code == 401, "older sessions signed out"
    assert sign_in(client, email).json()["access_token"], "the password alone suffices again"


def test_a_required_role_cannot_turn_it_off(client, database):
    _, token = session_for(client, database, "notoff", role="employee")
    _, _, fresh = enrol(client, token)
    from app.core.config import settings

    settings.MFA_REQUIRED_ROLES = frozenset({"admin", "accountant", "employee"})
    refused = client.post("/api/mfa/disable", headers=bearer(fresh), json={"password": PASSWORD})
    assert refused.status_code == 409 and refused.json()["code"] == "mfa.required"


# --- A role that requires it ------------------------------------------------------------

def test_a_required_role_enrols_at_sign_in_before_any_session(client, database):
    email = f"boss@{DOMAIN}"
    make_account(database, email, "accountant")
    first = sign_in(client, email).json()
    assert first["mfaEnrolmentRequired"] is True and first["access_token"] is None
    enrol_token = first["enrolToken"]
    assert client.get("/api/me", headers=bearer(enrol_token)).status_code == 401, "not a session"

    setup = client.post("/api/mfa/enrol/setup", json={"enrolToken": enrol_token})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    done = client.post("/api/mfa/enrol/confirm", json={"enrolToken": enrol_token, "code": code_at(secret)})
    assert done.status_code == 200, done.text
    body = done.json()
    assert len(body["recoveryCodes"]) == 10 and body["user"]["email"] == email
    assert client.get("/api/me", headers=bearer(body["access_token"])).status_code == 200
    assert sign_in(client, email).json()["mfaRequired"] is True, "from now on, the code"


def test_without_the_key_nothing_asks_for_a_second_factor(client, database, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MFA_ENCRYPTION_KEY", "")
    email = f"nokey@{DOMAIN}"
    make_account(database, email, "admin")
    assert sign_in(client, email).json()["access_token"], "two-factor is off without its key"


# --- The admin's reset, for a lost phone ----------------------------------------------------

def test_the_admin_resets_someone_elses_second_factor(client, database, identities):
    email, token = session_for(client, database, "lostphone")
    _, _, fresh = enrol(client, token)
    user_id = client.get("/api/me", headers=bearer(fresh)).json()["id"]
    admin = identities["admin"]["headers"]
    assert client.post(f"/api/users/{user_id}/mfa/reset", headers=admin).status_code == 204
    assert client.get("/api/me", headers=bearer(fresh)).status_code == 401, "signed out everywhere"
    assert sign_in(client, email).json()["access_token"], "an employee signs in with the password again"
    with database.connect() as c:
        logged = c.execute(text("SELECT count(*) FROM audit_events WHERE action = 'user.mfa_reset' AND entity_id = :u"),
                           {"u": user_id}).scalar_one()
    assert logged == 1


def test_the_admin_cannot_reset_their_own(client, identities):
    admin = identities["admin"]
    response = client.post(f"/api/users/{admin['user_id']}/mfa/reset", headers=admin["headers"])
    assert response.status_code == 409 and response.json()["code"] == "mfa.reset_self"


# --- The database's own rules --------------------------------------------------------------

def test_the_application_role_cannot_read_the_secrets():
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with engine.connect() as conn:
            for table in ("user_mfa", "user_mfa_recovery"):
                with refused_with(INSUFFICIENT_PRIVILEGE):
                    conn.execute(text(f"SELECT * FROM {table}"))
                conn.rollback()
    finally:
        engine.dispose()


def test_the_functions_refuse_to_change_someone_elses_second_factor(identities):
    """An application flaw that calls them for another account is refused by the database."""
    engine = create_engine(os.environ["DATABASE_URL"])
    employee, accountant = identities["employee"], identities["accountant"]
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT set_config('app.user_id', :u, false),"
                              " set_config('app.user_role', 'employee', false)"), {"u": employee["user_id"]})
            for call in ("SELECT auth_mfa_begin(:other, 'x')",
                         "SELECT auth_mfa_enable(:other, 1, ARRAY[]::text[])",
                         "SELECT auth_mfa_replace_recovery(:other, ARRAY[]::text[])",
                         "SELECT auth_mfa_remove(:other)"):
                with refused_with(INSUFFICIENT_PRIVILEGE):
                    conn.execute(text(call), {"other": accountant["user_id"]})
                conn.rollback()
    finally:
        engine.dispose()
