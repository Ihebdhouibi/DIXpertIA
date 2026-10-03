from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

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


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
