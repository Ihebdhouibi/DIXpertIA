from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.models.invoicing import (
    InvoiceProcessingStatus,
)


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


class SupplierBase(BaseModel):
    nom: str
    email: str = ""
    telephone: str = ""
    adresse: str = ""


class SupplierCreate(SupplierBase):
    pass


class SupplierOut(SupplierBase):
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


class SupplierInvoiceCreate(BaseModel):
    """A bill a supplier issued to us (#40).

    Different from InvoiceCreate in three ways that follow from the direction:

    - `date_emission` is supplied, not today's date. The bill carries the
      supplier's date, and it is routinely entered days later.
    - `supplier_reference` is required. It is the number printed on the bill,
      stored exactly as received; our own FF-YYYY-NNNN reference is separate.
    - amounts are supplied rather than computed from line items, because a
      supplier's totals are theirs and may not equal our arithmetic over their
      lines - rounding conventions differ. Entering what the bill says is the
      point; inventing a total from the lines would misstate the expense.
    """

    supplier_id: int
    supplier_reference: str = Field(min_length=1, max_length=60)
    date_emission: date
    date_echeance: date
    montant_ht: Decimal = Field(ge=0)
    montant_ttc: Decimal = Field(ge=0)
    items: list[InvoiceItemCreate] = []

    @field_validator("date_echeance")
    @classmethod
    def _due_not_before_issue(cls, value: date, info) -> date:
        # Mirrors ck_invoices_dates, so the API answers 422 with a field name
        # rather than letting the database raise and returning 500.
        issued = info.data.get("date_emission")
        if issued and value < issued:
            raise ValueError("date_echeance cannot be before date_emission")
        return value

    @field_validator("montant_ttc")
    @classmethod
    def _ttc_not_below_ht(cls, value: Decimal, info) -> Decimal:
        # Mirrors ck_invoices_amounts.
        ht = info.data.get("montant_ht")
        if ht is not None and value < ht:
            raise ValueError("montant_ttc cannot be below montant_ht")
        return value


# InvoiceOut deliberately does not live here. The API's output contract is the
# translated one in app/schemas/api.py (#37 Option C): this module holds the
# ORM-shaped schemas that validate input, and having two classes called
# InvoiceOut in one codebase was a trap waiting for whoever imported the wrong
# one.


class ProcessingStatusUpdate(BaseModel):
    """Body of the processing-status transition.

    Only the target state: the rules about which moves are legal live in the
    database, not here, so that a direct SQL write cannot bypass them.
    """

    processing_status: InvoiceProcessingStatus
