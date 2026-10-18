"""Limits on sign-in and on the public routes (#175).

Four limits, each kept as rows of auth_attempts and checked by
auth_throttle_hit(), a SECURITY DEFINER function, so they hold across workers
and restarts (see the migration):

- public_ip: requests to any public route, per address, per minute. Past it,
  429 with Retry-After.
- login_ip: failed sign-ins from one address, whatever the account. Stops
  one address trying a password list against many accounts. 429.
- login_account: failed sign-ins on one e-mail. Past it the account is locked
  for a while, and the answer is the same 401 as a wrong password, so it
  says nothing about whether the account exists. A success resets it.
- reset_mail: reset e-mails sent to one account per hour. Past it nothing is
  sent, and the answer is the same as when one is: nobody's inbox is flooded.

Keys are HMACs with the server secret: an address or an e-mail is never
stored, only something that counts it.

The client address is request.client.host. Behind a reverse proxy, uvicorn
sets it from X-Forwarded-For only when the proxy is a trusted address
(--forwarded-allow-ips, 127.0.0.1 by default), and the proxy must set that
header itself. Otherwise every visitor shares the proxy's address, and one
limit.
"""

import hashlib
import hmac

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.i18n import ApiError

PUBLIC_IP = "public_ip"
LOGIN_IP = "login_ip"
LOGIN_ACCOUNT = "login_account"
RESET_MAIL = "reset_mail"


def _key(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()


def ip_key(request: Request) -> str:
    return _key("ip:" + (request.client.host if request.client else "unknown"))


def email_key(email: str) -> str:
    # Case folded: "Admin@x.tn" must not be a fresh counter for "admin@x.tn".
    return _key("email:" + email.strip().lower())


def hit(db: Session, bucket: str, key: str, limit: int, window_seconds: int) -> int:
    """Count one attempt if the limit allows it.

    Returns the attempt's id (positive), or minus the seconds until the limit
    allows another. Does not commit: the caller commits before it answers, so
    the attempt counts even when the request then fails.
    """
    return db.execute(text("SELECT auth_throttle_hit(:b, :k, :n, :w)"),
                      {"b": bucket, "k": key, "n": limit, "w": window_seconds}).scalar_one()


def forget(db: Session, attempt_id: int) -> None:
    db.execute(text("SELECT auth_throttle_forget(:i)"), {"i": attempt_id})


def clear(db: Session, bucket: str, key: str) -> None:
    db.execute(text("SELECT auth_throttle_clear(:b, :k)"), {"b": bucket, "k": key})


def too_many(wait_seconds: int) -> ApiError:
    return ApiError(429, "auth.too_many_requests", headers={"Retry-After": str(wait_seconds)})


def limit_public_requests(request: Request, db: Session = Depends(get_db)) -> None:
    """Dependency of every public route: at most PUBLIC_REQUESTS_PER_MINUTE per address."""
    result = hit(db, PUBLIC_IP, ip_key(request), settings.PUBLIC_REQUESTS_PER_MINUTE, 60)
    db.commit()
    if result < 0:
        raise too_many(-result)
