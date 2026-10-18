"""Row-level security on users, and the password hash closed to the application (#76).

Direct queries as the application role, not API calls: the point is that the
rules hold even when the application's own checks are wrong or bypassed. The
API paths that read users before anyone is identified - sign-in, the reset and
activation links, the per-request session check - are exercised end to end by
test_account_lifecycle.py and test_audit_trail.py.
"""

import os

import pytest
from sqlalchemy import create_engine, text

from account_flow import link_token, make_account
from db_errors import INSUFFICIENT_PRIVILEGE, refused_with

DOMAIN = "users-rls-test.tn"
FUNCTIONS = ("auth_account_by_email", "auth_session", "auth_spend_account_token", "auth_set_locale")


@pytest.fixture(autouse=True)
def remove_created_users(database):
    yield
    with database.connect() as c:
        c.execute(text("DELETE FROM users WHERE email LIKE :d"), {"d": f"%@{DOMAIN}"})


@pytest.fixture
def as_app_role():
    """Connections as dixpertia_app carrying an identity, like a request's."""
    engines = []

    def connect(user_id, role):
        engine = create_engine(os.environ["DATABASE_URL"])
        engines.append(engine)
        conn = engine.connect()
        conn.execute(text("SELECT set_config('app.user_id', :u, false), set_config('app.user_role', :r, false)"),
                     {"u": user_id or "", "r": role or ""})
        conn.commit()
        return conn

    yield connect
    for engine in engines:
        engine.dispose()


def fixture_ids(conn, identities):
    ids = [identities[r]["user_id"] for r in ("admin", "accountant", "employee")]
    return sorted(r[0] for r in conn.execute(text("SELECT id FROM users WHERE id = ANY(:i)"), {"i": ids}))


# --- Rows ---------------------------------------------------------------------------

def test_an_employee_reads_only_their_own_account(as_app_role, identities):
    me = identities["employee"]["user_id"]
    assert fixture_ids(as_app_role(me, "employee"), identities) == [me]


@pytest.mark.parametrize("role", ["admin", "accountant"])
def test_admin_and_accountant_read_every_account(as_app_role, identities, role):
    """The accountant too: payslips and the invoice review history show other
    people's names, as the employees table already allows."""
    everyone = sorted(identities[r]["user_id"] for r in ("admin", "accountant", "employee"))
    assert fixture_ids(as_app_role(identities[role]["user_id"], role), identities) == everyone


def test_an_unidentified_session_reads_no_account(as_app_role, identities):
    assert fixture_ids(as_app_role(None, None), identities) == []


def test_an_employee_cannot_change_their_own_role(as_app_role, identities, database):
    me = identities["employee"]["user_id"]
    conn = as_app_role(me, "employee")
    with conn.begin():
        changed = conn.execute(text("UPDATE users SET role = 'admin' WHERE id = :u"), {"u": me}).rowcount
    assert changed == 0
    with database.connect() as c:
        assert c.execute(text("SELECT role FROM users WHERE id = :u"), {"u": me}).scalar_one() == "employee"


# --- The password hash --------------------------------------------------------------

@pytest.mark.parametrize("role", ["admin", "employee"])
def test_the_password_hash_is_unreadable_even_ones_own(as_app_role, identities, role):
    me = identities[role]["user_id"]
    conn = as_app_role(me, role)
    with refused_with(INSUFFICIENT_PRIVILEGE):
        conn.execute(text('SELECT "hashedPassword" FROM users WHERE id = :u'), {"u": me}).all()


def test_the_password_hash_cannot_be_written_directly(as_app_role, identities):
    conn = as_app_role(identities["admin"]["user_id"], "admin")
    with refused_with(INSUFFICIENT_PRIVILEGE):
        with conn.begin():
            conn.execute(text('UPDATE users SET "hashedPassword" = \'x\' WHERE id = :u'),
                         {"u": identities["employee"]["user_id"]})


def test_a_stored_token_hash_cannot_set_a_password(as_app_role, client, database, mailbox):
    """auth_spend_account_token() takes the token, not its hash: reading
    account_tokens, which the application role can, is no way in."""
    user_id = make_account(database, f"victim@{DOMAIN}")
    client.post("/api/forgot-password", json={"email": f"victim@{DOMAIN}"})
    link_token(mailbox, f"victim@{DOMAIN}")
    conn = as_app_role(None, None)
    with conn.begin():
        stored = conn.execute(text("SELECT token_hash FROM account_tokens WHERE user_id = :u"),
                              {"u": user_id}).scalar_one()
        spent = conn.execute(text("SELECT auth_spend_account_token(:h, 'reset', 'x')"), {"h": stored}).scalar()
    assert spent is None


# --- The functions ------------------------------------------------------------------

@pytest.mark.parametrize("name", FUNCTIONS)
def test_each_function_pins_search_path_and_is_not_public(database, name):
    with database.connect() as c:
        definer, config, acl = c.execute(text(
            "SELECT prosecdef, proconfig, proacl::text FROM pg_proc WHERE proname = :n"), {"n": name}).one()
    assert definer, "SECURITY DEFINER"
    assert "search_path=pg_catalog, public" in (config or []), config
    # An ACL entry "=X/..." would mean EXECUTE for PUBLIC.
    assert acl and "{=X" not in acl and ",=X" not in acl, acl
    assert "dixpertia_app=X" in acl, acl


def test_the_session_check_returns_no_hash(as_app_role, identities):
    conn = as_app_role(None, None)
    columns = set(conn.execute(text("SELECT * FROM auth_session(:u)"),
                               {"u": identities["employee"]["user_id"]}).mappings().one())
    assert columns == {"role", "isActive", "isVerified", "token_version"}
