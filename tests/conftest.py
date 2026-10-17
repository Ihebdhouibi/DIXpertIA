"""Shared fixtures for the API test suite (#57).

The application cannot be tested against a bare database. It needs two roles
with different privileges, row-level security policies, and the triggers that
carry the accountant's rules - so the suite runs against a real PostgreSQL
built by the same migrations production uses, not against SQLite or a mock.

Point TEST_DATABASE_URL at a throw-away database, as a SUPERUSER:

    TEST_DATABASE_URL=postgresql://postgres:pass@localhost:5432/dixpertia_test pytest

Without it the suite skips rather than silently running against your
development database, which it would empty between tests.

The superuser URL is used to build the schema and to set fixtures up. The
application itself is pointed at the `dixpertia_app` role, exactly as in
production - which matters more than it looks. A superuser bypasses row-level
security entirely, so a suite that let the app connect as one would report
every policy test as passing while proving nothing at all.

On the same server as the development database, the roles keep the passwords
from .env, so a run does not lock the development database out (#150; see
_dev_passwords and db/README.md).
"""

import os
import secrets
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

APP_ROLE = "dixpertia_app"
OWNER_ROLE = "dixpertia_owner"
_LOCAL_HOSTS = {None, "", "localhost", "127.0.0.1", "::1"}


def _server(url) -> tuple:
    """(host, port) with the spellings of "this machine" folded together."""
    host = "localhost" if url.host in _LOCAL_HOSTS else url.host
    return host, url.port or 5432


def _dev_passwords() -> dict:
    """The development roles' passwords, when the test database shares their server.

    PostgreSQL roles belong to the server, not to a database. Provisioning the
    test database resets the passwords of dixpertia_app and dixpertia_owner,
    so on the documented setup (dixpertia_test next to dixpertia on the same
    server) a run with fresh passwords locked the development database out
    until a superuser set them back (#150). Reusing the passwords from
    DATABASE_URL / SCHEMA_DATABASE_URL makes that reset a no-op.

    Only for the same server: a separate test server (CI, Docker) has nothing
    to protect and keeps per-run passwords. Read here, at import, because the
    database fixture points DATABASE_URL at the test database.
    """
    if not TEST_DATABASE_URL:
        return {}
    dev = dotenv_values(ROOT / ".env", encoding="utf-8-sig")
    dev.update({k: os.environ[k] for k in ("DATABASE_URL", "SCHEMA_DATABASE_URL")
                if k in os.environ})
    test_server = _server(make_url(TEST_DATABASE_URL))
    found = {}
    for key in ("DATABASE_URL", "SCHEMA_DATABASE_URL"):
        if not dev.get(key):
            continue
        url = make_url(dev[key])
        if (url.username in (APP_ROLE, OWNER_ROLE) and url.password
                and _server(url) == test_server):
            found[url.username] = url.password
    return found


_DEV_PASSWORDS = _dev_passwords()

# Credentials for the two application roles on the throw-away database. On a
# separate server they are generated per run: they only have to be stable for
# the length of one session, long enough to provision the roles and build the
# two URLs from them.
#
# token_hex, not token_urlsafe: the latter draws from a base64url alphabet that
# includes "-", so roughly one run in thirty produced a password starting with
# a dash, which argparse then read as a flag and the whole suite errored at
# setup with "expected one argument". Hex has no character that is special to
# argparse, a shell or a URL.
APP_PASSWORD = _DEV_PASSWORDS.get(APP_ROLE) or secrets.token_hex(16)
OWNER_PASSWORD = _DEV_PASSWORDS.get(OWNER_ROLE) or secrets.token_hex(16)


def _role_url(role: str, password: str) -> str:
    """The superuser URL with its credentials swapped for a role's.

    Built with make_url so a reused development password containing URL
    characters is encoded rather than splitting the URL.
    """
    url = make_url(TEST_DATABASE_URL).set(username=role, password=password)
    return url.render_as_string(hide_password=False)

# Business data only. `users` and `employees` hold the fixture accounts every
# test signs in as, and alembic_version must survive or the schema is rebuilt.
TRUNCATED_BETWEEN_TESTS = (
    # TRUNCATE, not DELETE, which the append-only trigger refuses (#63).
    "audit_events",
    "notifications",
    "invoice_reviews",
    "invoice_items",
    "invoices",
    "invoice_sequences",
    "accounting_periods",
    "clients",
    "suppliers",
    "payslips",
    "leave_requests",
)

ACCOUNTS = {
    "admin": ("TEST-ADMIN", "admin@test.tn", "admin"),
    "accountant": ("TEST-ACCT", "acct@test.tn", "accountant"),
    "employee": ("TEST-EMP", "emp@test.tn", "employee"),
}


def _require_database() -> str:
    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL is not set. The suite needs a throw-away "
            "PostgreSQL: it truncates business tables between tests.",
            allow_module_level=True,
        )
    return TEST_DATABASE_URL


def _provision(url: str) -> None:
    """Create the two application roles and their grants.

    The "--flag=value" form rather than "--flag", "value": argparse reads a
    value beginning with a dash as another flag, so the separated form makes
    the suite depend on what a random password happens to start with.
    """
    _run("db/setup_roles.py", f"--superuser-url={url}",
         f"--app-password={APP_PASSWORD}", f"--owner-password={OWNER_PASSWORD}")


def _run(script: str, *args: str) -> None:
    """Run one of the db/ provisioning scripts against the test database."""
    result = subprocess.run(
        [sys.executable, script, *args], cwd=ROOT, env=os.environ,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script} failed:\n{result.stdout}\n{result.stderr}")


@pytest.fixture(scope="session", autouse=True)
def database():
    """Build the schema once, exactly the way an environment is provisioned.

    Deliberately the real procedure from db/README.md rather than
    Base.metadata.create_all(): create_all does not run the migrations, so it
    would miss every trigger, policy and CHECK that lives in them - which is
    most of what this suite exists to protect.
    """
    url = _require_database()
    os.environ.setdefault("SECRET_KEY", "test-secret-key-at-least-32-characters-long")
    # The application runs as the least-privileged role, as it does in
    # production. Migrations and fixtures run as the owner.
    os.environ["REMINDERS_ENABLED"] = "false"  # tests call the job directly (#134)
    os.environ["DATABASE_URL"] = _role_url(APP_ROLE, APP_PASSWORD)
    os.environ["SCHEMA_DATABASE_URL"] = _role_url(OWNER_ROLE, OWNER_PASSWORD)

    superuser = create_engine(url, isolation_level="AUTOCOMMIT")
    with superuser.connect() as c:
        # A previous run may have left the schema behind. Starting from empty
        # means a migration that only works on an existing database cannot pass
        # here by accident.
        c.execute(text("DROP SCHEMA public CASCADE"))
        c.execute(text("CREATE SCHEMA public"))

    # The roles the policies name must exist before the migrations create
    # policies that reference them.
    _provision(url)
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                   cwd=ROOT, check=True, capture_output=True, env=os.environ)
    # Table-level DELETE grants, which could not apply before the tables existed.
    _provision(url)

    _seed_accounts(superuser)
    # Tests that assert directly in SQL use the owner: it is subject to the
    # same triggers and CHECKs, so a rule cannot pass here by privilege, but
    # its *_owner_all policies let a fixture see every row.
    owner = create_engine(_role_url(OWNER_ROLE, OWNER_PASSWORD),
                          isolation_level="AUTOCOMMIT")
    yield owner
    superuser.dispose()


def _seed_accounts(owner) -> None:
    """One login account and employee record per role.

    Every test signs in as one of these. They are created once and never
    truncated, so a test can rely on `employee` existing without creating it.
    """
    with owner.connect() as c:
        for user_id, email, role in ACCOUNTS.values():
            c.execute(text(
                'INSERT INTO users (id, email, "firstName", "lastName", role,'
                ' "hashedPassword", "isActive", "isVerified", "createdAt")'
                " VALUES (:id, :em, 'Test', :role, :role, 'x', true, true, now())"
                " ON CONFLICT (id) DO NOTHING"),
                {"id": user_id, "em": email, "role": role})
            c.execute(text(
                "INSERT INTO employees (user_id, job_title, hired_on,"
                " annual_entitlement_days)"
                " VALUES (:u, 'Tester', '2024-01-01', 21)"
                " ON CONFLICT (user_id) DO NOTHING"), {"u": user_id})


@pytest.fixture(autouse=True)
def clean_business_data(database):  # noqa: D401 - the docstring below explains it
    """Empty the business tables before each test.

    TRUNCATE rather than DELETE on purpose: `invoice_is_never_deleted` (#38)
    refuses to delete an invoice, and archived invoices are frozen as well
    (#41). Both are correct and neither is meant to govern fixtures. TRUNCATE
    does not fire row triggers, so it removes the data without disabling the
    rules the tests are about to check.
    """
    with database.connect() as c:
        c.execute(text(
            f"TRUNCATE {', '.join(TRUNCATED_BETWEEN_TESTS)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def app(database):
    """The real application, imported after the environment is pointed at the test database."""
    import main
    return main.app


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient
    # raise_server_exceptions=False so a 500 is asserted as a 500 rather than
    # blowing up the test: "this route returns 500" is a thing worth testing.
    # English by default: the suite's assertions read English messages. The
    # API's own default, without the header, is French (#135); test_i18n.py
    # covers both languages.
    return TestClient(app, raise_server_exceptions=False, headers={"Accept-Language": "en"})


@pytest.fixture
def mailbox(app, monkeypatch):
    """The e-mails the API sends, captured instead of sent: dicts of to, subject, body.

    Activation and reset links travel only by e-mail, and only their hash is
    stored (#62), so a test that follows a link has to read it from here.
    """
    import main

    sent = []

    def capture(to_email, subject, body):
        sent.append({"to": to_email, "subject": subject, "body": body})
        return True

    monkeypatch.setattr(main, "send_email", capture)
    return sent


@pytest.fixture
def identities(database):
    """Per-role bearer tokens, plus the employee id each account resolves to."""
    from app.core.security import create_access_token

    with database.connect() as c:
        rows = dict(c.execute(text(
            "SELECT user_id, id FROM employees WHERE user_id = ANY(:ids)"),
            {"ids": [u for u, _, _ in ACCOUNTS.values()]}).all())

    out = {}
    for role, (user_id, email, _) in ACCOUNTS.items():
        out[role] = {
            "user_id": user_id,
            "email": email,
            "employee_id": rows.get(user_id),
            "headers": {
                "Authorization":
                    f"Bearer {create_access_token({'sub': user_id, 'role': role})}",
            },
        }
    out["anonymous"] = {"user_id": None, "email": None, "employee_id": None,
                        "headers": {}}
    return out


@pytest.fixture(autouse=True)
def request_identity(request, identities):
    """Mirror the signed-in identity into the contextvar the engine reads.

    In production `require_authentication` sets this per request, and the
    `after_begin` listener turns it into the transaction-local settings the
    policies read. TestClient runs the app in a worker thread whose contextvar
    does not inherit from the test, so a test that signs in as a role must set
    it here too, or every policy sees "no identity" and filters everything out.

    Mark a test with @pytest.mark.identity("employee") to choose the role.
    """
    from app.core.identity import clear_identity, set_identity

    marker = request.node.get_closest_marker("identity")
    role = marker.args[0] if marker else None
    if role and role != "anonymous":
        who = identities[role]
        set_identity(who["user_id"], role)
    yield
    clear_identity()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "identity(role): sign the test in as admin, accountant, employee or anonymous",
    )
