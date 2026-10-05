import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
# Imported for its side effect, not for direct use: loading this module registers
# the `users` table on Base.metadata, which Invoice.cree_par_id needs in order to
# resolve ForeignKey("users.id"). Do not let a linter auto-remove it.
from app.models.user import User  # noqa: F401


class InvoiceStatus(str, enum.Enum):
    BROUILLON = "brouillon"
    ENVOYEE = "envoyee"
    PAYEE = "payee"
    EN_RETARD = "en_retard"
    ANNULEE = "annulee"


class InvoiceProcessingStatus(str, enum.Enum):
    """The accountant's workflow state, independent of the commercial state.

    This is a second axis, not a renaming of InvoiceStatus (#41). The two
    describe different things and move for different reasons:

        statut            what the client sees - issued, paid, overdue
        processing_status what the books see   - booked, reconciled, closed

    An invoice is routinely PAYEE and still `pending`: the client has paid, but
    nobody has entered it in the books yet. The reverse happens too - an invoice
    can be `completed` in the accounts while the client has not paid, because
    booking an expectation and collecting on it are separate events. Collapsing
    the two into one enum would make "paid but not yet booked" inexpressible,
    which is the normal state of most invoices mid-month.

    Meanings, as confirmed with the accountant:

        pending    it exists, nobody has handled it. The state on creation.
        processed  entered in the books.
        completed  booked AND matched against an actual payment.
        archived   the month it belongs to has been closed.

    `processed` and `completed` are deliberately distinct: booking an invoice
    and reconciling it against a bank line are separate acts, often days apart,
    and the gap between them is exactly what the accountant chases at month end.
    """

    PENDING = "pending"
    PROCESSED = "processed"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    nom = Column(String(150), nullable=False)
    email = Column(String(100), default="")
    telephone = Column(String(30), default="")
    adresse = Column(Text, default="")

    invoices = relationship("Invoice", back_populates="client")

    __table_args__ = (
        # Stops "Acme Corp" and "ACME CORP" becoming two customers.
        Index("ux_clients_nom_ci", text("lower(nom)"), unique=True),
    )


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    numero = Column(String(30), unique=True, nullable=False)
    # RESTRICT: a client with invoices must not be deletable.
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    date_emission = Column(Date, nullable=False)
    date_echeance = Column(Date, nullable=False)
    montant_ht = Column(Numeric(10, 2), nullable=False)
    montant_ttc = Column(Numeric(10, 2), nullable=False)
    # NOT NULL with a default: the status was nullable and never set, so every
    # invoice was created with statut = NULL. InvoiceOut requires it, so
    # serialising the response failed *after* the commit - the invoice was
    # saved, the client got a 500, and the retry created a second invoice with
    # a new legal number (AUDIT-DB-010).
    # server_default uses the enum NAME, not .value: SQLAlchemy's Enum type
    # stores Python enum names as the PostgreSQL labels, so the labels here are
    # BROUILLON/ENVOYEE/..., while .value would give 'brouillon' and the ALTER
    # would be rejected as an invalid input value for the enum.
    statut = Column(Enum(InvoiceStatus), nullable=False,
                    server_default=InvoiceStatus.BROUILLON.name)
    # Make cree_par_id nullable so we can insert without it
    # RESTRICT: authorship of an issued invoice must survive.
    cree_par_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    # The accountant's workflow state. Separate from `statut` above - see
    # InvoiceProcessingStatus for why these are two fields and not one.
    # server_default uses the enum NAME, as `statut` does: SQLAlchemy stores
    # Python enum names as the PostgreSQL labels, so 'pending' would be rejected
    # as an invalid input value while 'PENDING' is the actual label.
    processing_status = Column(
        Enum(InvoiceProcessingStatus),
        nullable=False,
        server_default=InvoiceProcessingStatus.PENDING.name,
    )
    # Set from the Idempotency-Key header. UNIQUE, so a retried request cannot
    # create a second invoice: in accounting an issued invoice cannot be
    # deleted, so each duplicate would need a credit note.
    idempotency_key = Column(String(64), unique=True, nullable=True)

    client = relationship("Client", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("montant_ht >= 0 AND montant_ttc >= montant_ht",
                        name="ck_invoices_amounts"),
        CheckConstraint("date_echeance >= date_emission", name="ck_invoices_dates"),
        # Indexes below were chosen by measuring, not by habit: db/seed_perf_data.py
        # fills the tables and db/measure_indexes.py prints the resulting plans.
        #
        # Ascending, although the list reads newest first: PostgreSQL scans a
        # btree backward at the same cost, and one ascending index then serves
        # both the newest-first list and the accountant's ascending month range.
        Index("ix_invoices_date_emission", "date_emission", "id"),
        # Invoices for one client.
        Index("ix_invoices_client_id", "client_id"),
        # Not for reads: without it, deleting a user who has issued no invoices
        # makes the RESTRICT check scan the whole table to prove absence.
        Index("ix_invoices_cree_par_id", "cree_par_id"),
        # Only five distinct statuses, so this earns about 2x rather than the
        # large factors above - kept because the accountant's workflow filters
        # by status constantly.
        Index("ix_invoices_statut", "statut"),
        # Composite, not a single column on processing_status. Measured at 10k
        # invoices, the paginated list never uses either: with four roughly
        # equal values the filter is 25% selective, so ix_invoices_date_emission
        # plus a LIMIT beats both. What this does earn is the unbounded count
        # behind "how many invoices are still awaiting me" - 1.13 ms to 0.49 ms
        # against a sequential scan - and the month-scoped close query, where
        # leading with the status and then the date beats a single column
        # (0.14 ms against 0.33 ms). Re-check with db/measure_indexes.py.
        Index("ix_invoices_processing_status", "processing_status", "date_emission"),
        # Serves the two triggers that police the legal series (#38, #39). Both
        # extract the year and number from `numero` with substring(), which no
        # ordinary index on `numero` can serve, so without this every insert
        # scanned the table. Partial, because only FA-YYYY-NNNN is the series.
        Index(
            "ix_invoices_series",
            text("substring(numero from 4 for 4)"),
            text("substring(numero from 9)::integer"),
            postgresql_where=text("numero ~ '^FA-[0-9]{4}-[0-9]+$'"),
        ),
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True)
    # CASCADE, matching the ORM cascade on Invoice.items. Previously the ORM
    # deleted lines while a direct SQL delete was refused - the same operation
    # with two different outcomes depending on the code path (#60).
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    designation = Column(String(255), nullable=False)
    quantite = Column(Numeric(8, 2), default=1)
    prix_unitaire = Column(Numeric(10, 2), nullable=False)
    taux_tva = Column(Numeric(4, 2), default=19)

    invoice = relationship("Invoice", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantite > 0", name="ck_invoice_items_quantite"),
        CheckConstraint("prix_unitaire >= 0", name="ck_invoice_items_prix"),
        CheckConstraint("taux_tva >= 0 AND taux_tva <= 100", name="ck_invoice_items_tva"),
        # The single largest win measured: loading one invoice's lines went from
        # a full scan of invoice_items to an index lookup. Every invoice detail
        # view and every PDF render takes this path.
        Index("ix_invoice_items_invoice_id", "invoice_id"),
    )
