"""Single-use account tokens: password reset and account activation (#62).

A token is an opaque random string sent by e-mail. Only its SHA-256 is stored,
so a database read hands out nothing usable. Each token is single use and
expires; issuing a new one for the same purpose spends the ones still live, so
only the latest link works.

Spending a link happens in the database, in auth_spend_account_token() (#76):
the steps that use a link run before anyone is identified, and users is under
row-level security. The function takes the token itself, not its hash, so
reading account_tokens is no way to set a password.

Functions here add to the caller's session and do not commit, like
record_event() and notify(): the token, the change it makes and its audit
event commit together or not at all.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import new_account_token
from app.models.user import AccountToken

RESET = "reset"
ACTIVATION = "activation"
LIFETIME = {RESET: timedelta(hours=1), ACTIVATION: timedelta(hours=72)}
# The query parameter the frontend reads for each kind of link.
LINK_PARAMETER = {RESET: "token", ACTIVATION: "activate"}


def issue_token(db: Session, user_id: str, purpose: str) -> str:
    """A new token for the account, replacing any still live for the same purpose."""
    now = datetime.now(timezone.utc)
    db.query(AccountToken).filter(
        AccountToken.user_id == user_id,
        AccountToken.purpose == purpose,
        AccountToken.used_at.is_(None),
    ).update({AccountToken.used_at: now}, synchronize_session=False)
    token, token_hash = new_account_token()
    db.add(AccountToken(user_id=user_id, purpose=purpose, token_hash=token_hash,
                        created_at=now, expires_at=now + LIFETIME[purpose]))
    db.flush()
    return token


def spend_token(db: Session, token: str, purpose: str, password_hash: str) -> str | None:
    """Spend a live link of `purpose` and set the account's new password.

    Returns the account id, or None for anything else - unknown, expired,
    already used, for the other purpose, or an inactive account - without
    saying which: the caller answers all of them alike. Also activates the
    account for an activation link, and revokes its sessions (token_version).
    """
    return db.execute(
        text("SELECT auth_spend_account_token(:t, :p, :h)"),
        {"t": token, "p": purpose, "h": password_hash},
    ).scalar()


def link(purpose: str, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/?{LINK_PARAMETER[purpose]}={token}"
