"""Helpers for the account lifecycle (#62): links from e-mails, accounts to sign in as."""

import re
import secrets

from sqlalchemy import text

# Generated per run, like conftest's role passwords: nothing to leak or reuse.
PASSWORD = secrets.token_hex(12)

_LINK = re.compile(r"[?&](?:token|activate)=([A-Za-z0-9_-]+)")


def link_token(mailbox, to: str) -> str:
    """The token in the last e-mail sent to `to`."""
    mails = [m for m in mailbox if m["to"] == to]
    assert mails, f"no e-mail was sent to {to}"
    match = _LINK.search(mails[-1]["body"])
    assert match, "the e-mail carries no link"
    return match.group(1)


def make_account(database, email: str, role: str = "employee", *, active=True, verified=True,
                 password: str = PASSWORD) -> str:
    """An account with a known password, inserted directly. Returns its id."""
    # Imported here, not at the top: app.core.config refuses to load before
    # the database fixture has set DATABASE_URL, and modules are collected first.
    from app.core.security import hash_password

    with database.connect() as c:
        return c.execute(text(
            'INSERT INTO users (email, "firstName", "lastName", role, "hashedPassword",'
            ' "isActive", "isVerified") VALUES (:e, :f, \'Test\', :r, :h, :a, :v) RETURNING id'),
            {"e": email, "f": email.split("@")[0], "r": role, "h": hash_password(password),
             "a": active, "v": verified}).scalar_one()


def sign_in(client, email: str, password: str = PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
