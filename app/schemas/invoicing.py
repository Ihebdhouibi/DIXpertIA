from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

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
    """Mirrors ck_invoice_items_* so the API answers 422 with a field name
    instead of letting the database raise and returning 500 (#58)."""

    designation: str = Field(min_length=1)
    quantite: Decimal = Field(default=Decimal(1), gt=0)
    prix_unitaire: Decimal = Field(ge=0)
    taux_tva: Decimal = Field(default=Decimal(19), ge=0, le=100)


class InvoiceItemOut(InvoiceItemCreate):
    id: int

    class Config:
        from_attributes = True


class InvoiceCreate(BaseModel):
    client_id: int
    date_echeance: date
    items: list[InvoiceItemCreate] = []

    @field_validator("date_echeance")
    @classmethod
    def _not_in_the_past(cls, value: date) -> date:
        # ck_invoices_dates requires date_echeance >= date_emission, and
        # date_emission is always today for a new invoice.
        if value < date.today():
            raise ValueError("date_echeance cannot be before today")
        return value


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
