"""Who is calling, and may they still (#62).

One check, used twice:

- require_authentication (main.py) runs it on every non-public request before
  the route, so a route that never asks for the current user is covered too.
- get_current_user runs it again for the routes that need the User row.

A token is accepted only if it is an access token, its account exists, is
active and activated, and the token was issued under the account's current
token_version. Deactivating an account, changing its role or changing its
password bumps the version, so every session issued before is refused on its
next request instead of living out its 60 minutes.

The account's state is read through auth_session() (#76): users is under
row-level security, and require_authentication runs before any identity is
set, so a plain query would see no row at all.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.i18n import ApiError
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def _unauthorised() -> HTTPException:
    return ApiError(status.HTTP_401_UNAUTHORIZED, "auth.not_authenticated",
                    headers={"WWW-Authenticate": "Bearer"})


def session_identity(token: str, db: Session) -> tuple[str, str] | None:
    """(user id, role) if the token may still be used, else None."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    state = db.execute(text("SELECT * FROM auth_session(:u)"), {"u": user_id}).mappings().first()
    if state is None or not state["isActive"] or not state["isVerified"]:
        return None
    if payload.get("ver") != state["token_version"]:
        return None
    return user_id, state["role"]


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    identity = session_identity(token, db)
    if identity is None:
        raise _unauthorised()
    # By now the request's identity is set, and an account always reads its
    # own row. User.id is a String column ("USR-001"), never coerced to int.
    user = db.query(User).filter(User.id == identity[0]).first()
    if user is None:
        raise _unauthorised()
    return user


def require_roles(*roles: str):
    # The role is the one on the account now, not the token's claim: a role
    # change also bumps token_version, so the two cannot disagree for long,
    # and the database is the authority either way.
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise ApiError(status.HTTP_403_FORBIDDEN, "auth.forbidden")
        return user
    return checker
