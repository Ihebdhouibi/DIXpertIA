import enum
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
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


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
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

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(30), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
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
    cree_par_id = Column(String, ForeignKey("users.id"), nullable=False)
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
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    designation = Column(String(255), nullable=False)
    quantite = Column(Numeric(8, 2), default=1)
    prix_unitaire = Column(Numeric(10, 2), nullable=False)
    taux_tva = Column(Numeric(4, 2), default=19)

    invoice = relationship("Invoice", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantite > 0", name="ck_invoice_items_quantite"),
        CheckConstraint("prix_unitaire >= 0", name="ck_invoice_items_prix"),
        CheckConstraint("taux_tva >= 0 AND taux_tva <= 100", name="ck_invoice_items_tva"),
    )


class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    model = Column(String)
    serialNumber = Column(String)
    price = Column(Float)
    status = Column(String, default="Available")
    createdAt = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_devices_price"),
        # Serial numbers identify hardware. Partial, so several devices may
        # still have no serial recorded.
        Index("ux_devices_serial", "serialNumber", unique=True,
              postgresql_where=text('"serialNumber" IS NOT NULL')),
    )
