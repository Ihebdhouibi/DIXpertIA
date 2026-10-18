"""Recognising a database refusal by its SQLSTATE, not its message (#161).

PostgreSQL writes its own messages in the server's language (lc_messages):
"permission denied" on an English server is "droit refusé" on a French one,
so a test matching the text fails there although the refusal happened. The
SQLSTATE is the same everywhere.

Matching text is still right for messages we write ourselves - a trigger's
RAISE EXCEPTION, or a constraint's name, which PostgreSQL quotes untranslated.
"""

from contextlib import contextmanager

import pytest
from sqlalchemy.exc import DBAPIError

# A missing privilege, and a row that violates a row-level security policy.
INSUFFICIENT_PRIVILEGE = "42501"


@contextmanager
def refused_with(sqlstate: str):
    """Expect the block to be refused by the database with `sqlstate`."""
    with pytest.raises(DBAPIError) as refused:
        yield refused
    code = getattr(refused.value.orig, "pgcode", None)
    assert code == sqlstate, f"refused with SQLSTATE {code}, expected {sqlstate}: {refused.value.orig}"
