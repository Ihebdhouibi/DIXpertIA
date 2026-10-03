"""Create every table declared on the application's declarative Base.

Run once against an empty database:

    python tables.py

This is a stopgap until `alembic/versions/` actually contains migrations —
see the backlog item about generating an initial revision.
"""

# Importing Base from app.core.database is essential: the models register
# themselves on *that* Base's metadata. Declaring a fresh declarative_base()
# here (as this script previously did) leaves the metadata empty, so
# create_all() silently creates nothing while still printing success.
from sqlalchemy import create_engine

from app.core.config import settings
from app.core.database import Base

# These imports look unused but are required: importing each module is what
# attaches the model to Base.metadata.
from app.models.user import User  # noqa: F401
from app.models.payroll import Payslip  # noqa: F401
from app.models.leaves import LeaveRequest  # noqa: F401
from app.models.service import Service, TeamMember  # noqa: F401
from app.models.invoicing import Client, Invoice, InvoiceItem, Device  # noqa: F401


# Schema DDL runs as the owner role, not the application role. The application
# role has no CREATE privilege by design (#70).
engine = create_engine(settings.SCHEMA_DATABASE_URL)


def main():
    # Never print settings.DATABASE_URL: it contains the database password.
    print(f"Target database: {engine.url.database} on {engine.url.host}")
    tables = sorted(Base.metadata.tables)
    if not tables:
        raise SystemExit("No tables registered on Base.metadata - check the model imports.")

    Base.metadata.create_all(bind=engine)
    print(f"Created or verified {len(tables)} tables:")
    for name in tables:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
