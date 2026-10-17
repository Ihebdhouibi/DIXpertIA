"""Single-use account tokens: password reset and account activation (#62).

A token is an opaque random string sent by e-mail. Only its SHA-256 is stored,
so a database read hands out nothing usable. Each token is single use and
expires; issuing a new one for the same purpose spends the ones still live, so
only the latest link works.

Functions here add to the caller's session and do not commit, like
record_event() and notify(): the token, the change it makes and its audit
event commit together or not at all.
"""

import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_account_token, new_account_token
from app.models.user import AccountToken, User

RESET = "reset"
ACTIVATION = "activation"
LIFETIME = {RESET: timedelta(hours=1), ACTIVATION: timedelta(hours=72)}
# The query parameter the frontend reads for each kind of link.
LINK_PARAMETER = {RESET: "token", ACTIVATION: "activate"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def issue_token(db: Session, user: User, purpose: str) -> str:
    """A new token for `user`, replacing any still live for the same purpose."""
    now = _now()
    db.query(AccountToken).filter(
        AccountToken.user_id == user.id,
        AccountToken.purpose == purpose,
        AccountToken.used_at.is_(None),
    ).update({AccountToken.used_at: now}, synchronize_session=False)
    token, token_hash = new_account_token()
    db.add(AccountToken(user_id=user.id, purpose=purpose, token_hash=token_hash,
                        created_at=now, expires_at=now + LIFETIME[purpose]))
    db.flush()
    return token


def spend_token(db: Session, token: str, purpose: str) -> User | None:
    """The account a live token of `purpose` belongs to, marking it used.

    None for anything else - unknown, expired, already used, or issued for the
    other purpose - without saying which: the caller answers all of them alike.
    The row is locked so two requests cannot spend the same token.
    """
    token_hash = hash_account_token(token)
    row = (
        db.query(AccountToken)
        .filter(AccountToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )
    # The lookup is by hash; the comparison is repeated in constant time so
    # the decision never depends on how much of a string matched.
    if row is None or not hmac.compare_digest(row.token_hash, token_hash):
        return None
    if row.purpose != purpose or row.used_at is not None or row.expires_at <= _now():
        return None
    row.used_at = _now()
    return db.get(User, row.user_id)


def link(purpose: str, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/?{LINK_PARAMETER[purpose]}={token}"
