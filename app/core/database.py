from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.core.config import settings
from app.core.identity import get_identity

# hide_parameters=True keeps bound values out of SQLAlchemy error text. Without
# it an IntegrityError prints every parameter - on user creation that includes
# the e-mail and the bcrypt hash of the temporary password (AUDIT-DB-008).
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    hide_parameters=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


@event.listens_for(Session, "after_begin")
def _apply_request_identity(session, transaction, connection):
    """Publish the current request's identity to the database transaction.

    Hooked on "after_begin" rather than set once per request on purpose: a
    handler that calls commit() ends the transaction, and SET LOCAL dies with
    it. Anything the handler does afterwards - db.refresh() for instance -
    would then run with no identity and, under RLS, silently see nothing. This
    re-applies the identity to every transaction the session opens.

    set_config(..., is_local => true) is the function form of SET LOCAL, and
    unlike SET LOCAL it takes bind parameters. It is scoped to the
    transaction, so it cannot leak into the next request that borrows this
    pooled connection - which a plain SET would do.
    """
    user_id, user_role = get_identity()
    if user_id is None and user_role is None:
        return
    connection.execute(
        text("SELECT set_config('app.user_id', :uid, true), "
             "set_config('app.user_role', :role, true)"),
        {"uid": user_id or "", "role": user_role or ""},
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
