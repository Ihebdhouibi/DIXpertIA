import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, Numeric, Enum
from sqlalchemy.orm import relationship

from app.core.database import Base


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


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(30), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    date_emission = Column(Date, nullable=False)
    date_echeance = Column(Date, nullable=False)
    montant_ht = Column(Numeric(10, 2), default=0)
    montant_ttc = Column(Numeric(10, 2), default=0)
    statut = Column(Enum(InvoiceStatus), default=InvoiceStatus.BROUILLON)
    cree_par_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    client = relationship("Client", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    designation = Column(String(255), nullable=False)
    quantite = Column(Numeric(8, 2), default=1)
    prix_unitaire = Column(Numeric(10, 2), nullable=False)
    taux_tva = Column(Numeric(4, 2), default=19)

    invoice = relationship("Invoice", back_populates="items")
