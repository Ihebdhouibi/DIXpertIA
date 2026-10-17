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
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


def _unauthorised() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticated_user(token: str, db: Session) -> User | None:
    """The account a token speaks for, or None if it must be refused."""
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    # User.id is a String column ("USR-001"), so it must not be coerced to int.
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.isActive or not user.isVerified:
        return None
    if payload.get("ver") != user.token_version:
        return None
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user = authenticated_user(token, db)
    if user is None:
        raise _unauthorised()
    return user


def require_roles(*roles: str):
    # The role is the one on the account now, not the token's claim: a role
    # change also bumps token_version, so the two cannot disagree for long,
    # and the database is the authority either way.
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
        return user
    return checker
