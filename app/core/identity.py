"""Per-request database identity, carried in context variables.

RLS policies read `app.user_id` and `app.user_role` through current_setting().
Those have to be set on the connection the request will actually use, and they
must not survive into the next request that borrows the same pooled connection.

The identity comes from the JWT claims, never from a database lookup: the
lookup itself is subject to the policies, so deriving identity from it would be
circular.

contextvars rather than a module global: FastAPI runs sync endpoints in a
worker thread, and anyio copies the context into that thread, so the value
follows the request. A module global would be shared across concurrent
requests.
"""

from contextvars import ContextVar
from typing import Optional

_user_id: ContextVar[Optional[str]] = ContextVar("dixpertia_user_id", default=None)
_user_role: ContextVar[Optional[str]] = ContextVar("dixpertia_user_role", default=None)


def set_identity(user_id: Optional[str], user_role: Optional[str]) -> None:
    _user_id.set(user_id)
    _user_role.set(user_role)


def clear_identity() -> None:
    _user_id.set(None)
    _user_role.set(None)


def get_identity() -> tuple[Optional[str], Optional[str]]:
    return _user_id.get(), _user_role.get()
