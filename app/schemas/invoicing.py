import re
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.invoicing import (
    InvoiceProcessingStatus,
)


Currency = Literal["TND", "EUR", "USD", "GBP"]


class ClientBase(BaseModel):
    nom: str
    email: str = ""
    telephone: str = ""
    adresse: str = ""
    # The language the client's invoices are printed in (#135).
    locale: Literal["fr", "en"] = "fr"
    # A client abroad, billed for an export of services without VAT, and the
    # currency their invoices are in (#195).
    export: bool = False
    devise: Currency = "TND"
    # A foreign VAT number or a matricule fiscal; printed only when filled.
    identifiant_fiscal: str | None = None


def export_currency_problem(export: bool, devise: str) -> bool:
    """This release's rule (#195): an export client always pays in a foreign
    currency. Mirrors ck_clients_export_in_foreign_currency; lifting the rule
    is removing both."""
    return bool(export) and devise == "TND"


def _tax_id(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > 50:
        raise ValueError("the tax ID is at most 50 characters")
    return value or None


def _client_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("the client name is required")
    if len(value) > 150:
        raise ValueError("the client name is at most 150 characters")
    return value


def _client_email(value: str) -> str:
    value = value.strip()
    # Optional, but when given it must look like an address: it is printed on
    # the invoice and shown as the client's contact (#192).
    if value and not _EMAIL.fullmatch(value):
        raise ValueError("the e-mail address is not valid")
    return value


_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class ClientCreate(ClientBase):
    """A new client (#192). Lengths follow the columns: name 150, e-mail 100,
    phone 30; the address is free text, capped at 500 characters."""

    email: str = Field(default="", max_length=100)
    telephone: str = Field(default="", max_length=30)
    adresse: str = Field(default="", max_length=500)

    _name = field_validator("nom")(_client_name)
    _mail = field_validator("email")(_client_email)
    _tax = field_validator("identifiant_fiscal")(_tax_id)

    @field_validator("telephone", "adresse")
    @classmethod
    def _trim(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def _export_in_foreign_currency(self):
        if export_currency_problem(self.export, self.devise):
            raise ValueError("an export client pays in a foreign currency (EUR, USD or GBP)")
        return self


class ClientUpdate(BaseModel):
    """A correction to a client (#192): only the fields sent change."""

    nom: str | None = None
    email: str | None = Field(default=None, max_length=100)
    telephone: str | None = Field(default=None, max_length=30)
    adresse: str | None = Field(default=None, max_length=500)
    locale: Literal["fr", "en"] | None = None
    export: bool | None = None
    devise: Currency | None = None
    # "" clears it; omitted leaves it as it is.
    identifiant_fiscal: str | None = None

    @field_validator("identifiant_fiscal")
    @classmethod
    def _tax(cls, value: str | None) -> str | None:
        return None if value is None else (_tax_id(value) or "")

    @field_validator("nom")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return None if value is None else _client_name(value)

    @field_validator("email")
    @classmethod
    def _mail(cls, value: str | None) -> str | None:
        return None if value is None else _client_email(value)

    @field_validator("telephone", "adresse")
    @classmethod
    def _trim(cls, value: str | None) -> str | None:
        return None if value is None else value.strip()


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
    # Both optional (#194): a description under the designation, and the unit
    # of the quantity ("days", "flat fee"). Blank is stored as NULL.
    detail: str | None = Field(default=None, max_length=1000)
    unite: str | None = Field(default=None, max_length=30)

    @field_validator("detail", "unite", mode="before")
    @classmethod
    def _blank_is_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


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


class InvoicePayment(BaseModel):
    """Marking an invoice paid (#126): paid in full, on this date."""

    paid_on: date


class InvoiceCancellation(BaseModel):
    """Why an invoice is cancelled (#126). Mandatory, drafts included."""

    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("a cancellation needs a reason")
        return value


class InvoiceRejection(BaseModel):
    """The accountant's reason for sending an invoice back (#118). Mandatory:
    it is what the admin corrects from; mirrors ck_invoice_reviews_rejection_has_comment."""

    comment: str = Field(min_length=1, max_length=2000)

    @field_validator("comment")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("a rejection needs a comment")
        return value


class InvoiceUpdate(BaseModel):
    """Correction of a draft invoice (#125): the full set of lines and the due date.

    The lines replace the existing ones rather than being patched one by one,
    so a correction is a single request that either applies whole or not at
    all. Everything else - number, issue date, client, direction - is not
    editable and is deliberately absent. At least one line: a correction is not
    a way to empty an invoice.
    """

    date_echeance: date
    items: list[InvoiceItemCreate] = Field(min_length=1)


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
