"""Create the least-privilege database roles and apply their grants.

Run once per environment, as a PostgreSQL superuser:

    python db/setup_roles.py --superuser-url postgresql://postgres:PASS@localhost:5432/dixpertia

Re-running is safe: the SQL is idempotent and passwords are reset to the values
used for that run. With no --app-password / --owner-password a strong one is
generated and printed once.

Why a Python runner rather than psql: psql is not installed on the team's
Windows machines, psycopg2 already is. The SQL itself lives in
db/sql/001-roles-and-grants.sql so it stays reviewable and versioned.
"""

import argparse
import pathlib
import secrets
import string
import sys

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, adapt

SQL_FILE = pathlib.Path(__file__).parent / "sql" / "001-roles-and-grants.sql"
APP_ROLE = "dixpertia_app"
OWNER_ROLE = "dixpertia_owner"


def generate_password(length: int = 28) -> str:
    # No shell metacharacters or '@' / ':' / '/': the value ends up inside a
    # DATABASE_URL, where those would need percent-encoding.
    alphabet = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def render_sql(app_password: str, owner_password: str) -> str:
    """Substitute the psql-style placeholders with safely quoted literals."""
    text = SQL_FILE.read_text(encoding="utf-8")
    for placeholder, value in (
        (":'app_password'", app_password),
        (":'owner_password'", owner_password),
    ):
        if placeholder not in text:
            sys.exit(f"Placeholder {placeholder} missing from {SQL_FILE.name}")
        literal = adapt(value).getquoted().decode("utf-8")
        text = text.replace(placeholder, literal)
    return text


def verify(cur) -> list[str]:
    """Check the acceptance criteria and return any failures."""
    failures = []

    cur.execute(
        "SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole "
        "FROM pg_roles WHERE rolname = %s",
        (APP_ROLE,),
    )
    row = cur.fetchone()
    if row is None:
        return [f"{APP_ROLE} was not created"]
    if any(row):
        failures.append(
            f"{APP_ROLE} still has elevated attributes: super={row[0]} "
            f"bypassrls={row[1]} createdb={row[2]} createrole={row[3]}"
        )

    # DELETE must be granted only on the two tables the application deletes from.
    cur.execute(
        "SELECT table_name FROM information_schema.role_table_grants "
        "WHERE grantee = %s AND privilege_type = 'DELETE' ORDER BY table_name",
        (APP_ROLE,),
    )
    granted = {r[0] for r in cur.fetchall()}
    expected = {"devices", "services"}
    if granted != expected:
        failures.append(f"DELETE grants are {sorted(granted)}, expected {sorted(expected)}")

    cur.execute(
        "SELECT count(*) FROM information_schema.role_table_grants "
        "WHERE grantee = %s AND privilege_type = 'TRUNCATE'",
        (APP_ROLE,),
    )
    if cur.fetchone()[0]:
        failures.append(f"{APP_ROLE} holds TRUNCATE on at least one table")

    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--superuser-url", required=True,
                        help="connection string for a superuser on the target database")
    parser.add_argument("--app-password")
    parser.add_argument("--owner-password")
    args = parser.parse_args()

    app_password = args.app_password or generate_password()
    owner_password = args.owner_password or generate_password()
    generated = (args.app_password is None, args.owner_password is None)

    statements = render_sql(app_password, owner_password)

    conn = psycopg2.connect(args.superuser_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    try:
        with conn.cursor() as cur:
            cur.execute(statements)
            print(f"Applied {SQL_FILE.name}")
            failures = verify(cur)
            cur.execute("SELECT current_database()")
            database = cur.fetchone()[0]
    finally:
        conn.close()

    if failures:
        print("\nVERIFICATION FAILED:")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print("Verified: app role is NOSUPERUSER / NOBYPASSRLS, DELETE limited to "
          "devices+services, no TRUNCATE.")

    parsed = psycopg2.extensions.parse_dsn(args.superuser_url)
    host = parsed.get("host", "localhost")
    port = parsed.get("port", "5432")
    print("\nSet these in .env (shown once):")
    if generated[0]:
        print(f'  DATABASE_URL="postgresql://{APP_ROLE}:{app_password}@{host}:{port}/{database}"')
    else:
        print(f'  DATABASE_URL="postgresql://{APP_ROLE}:<your app password>@{host}:{port}/{database}"')
    print("\nFor schema changes only (tables.py, Alembic):")
    if generated[1]:
        print(f'  SCHEMA_DATABASE_URL="postgresql://{OWNER_ROLE}:{owner_password}@{host}:{port}/{database}"')
    else:
        print(f'  SCHEMA_DATABASE_URL="postgresql://{OWNER_ROLE}:<your owner password>@{host}:{port}/{database}"')


if __name__ == "__main__":
    main()
