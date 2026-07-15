from datetime import date
from decimal import Decimal
from pydantic import BaseModel

from app.models.invoicing import InvoiceStatus


class ClientBase(BaseModel):
    nom: str
    email: str = ""
    telephone: str = ""
    adresse: str = ""


class ClientCreate(ClientBase):
    pass


class ClientOut(ClientBase):
    id: int

    class Config:
        from_attributes = True


class InvoiceItemCreate(BaseModel):
    designation: str
    quantite: Decimal = Decimal(1)
    prix_unitaire: Decimal
    taux_tva: Decimal = Decimal(19)


class InvoiceItemOut(InvoiceItemCreate):
    id: int

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    client_id: int
    date_echeance: date
    items: list[InvoiceItemCreate] = []


class InvoiceOut(BaseModel):
    id: int
    numero: str
    client_id: int
    date_emission: date
    date_echeance: date
    montant_ht: Decimal
    montant_ttc: Decimal
    statut: InvoiceStatus
    items: list[InvoiceItemOut] = []

    class Config:
        from_attributes = True
