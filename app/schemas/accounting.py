from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.accounting import PeriodState
from app.models.invoicing import InvoiceDirection, InvoiceProcessingStatus


class BlockingInvoice(BaseModel):
    """One invoice standing in the way of a close.

    The close reports these rather than a count alone: the accountant needs to
    know which invoices to go and finish, and a bare "3 invoices are not
    completed" sends them hunting.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    date_emission: date
    direction: InvoiceDirection
    processing_status: InvoiceProcessingStatus


class CurrencyTotals(BaseModel):
    """One currency's totals for a month (#195): never added to another's."""

    currency: str
    total_ht_outgoing: Decimal
    total_ttc_outgoing: Decimal
    total_ht_incoming: Decimal
    total_ttc_incoming: Decimal


class PeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    periode: date
    state: PeriodState
    closed_at: datetime | None = None
    closed_by_id: str | None = None
    # Recorded at the close. Null while the period is open.
    invoice_count: int | None = None
    total_ht_outgoing: Decimal | None = None
    total_ttc_outgoing: Decimal | None = None
    total_ht_incoming: Decimal | None = None
    total_ttc_incoming: Decimal | None = None
    # Every currency of the month (#195); the four totals above are its TND part.
    totals_by_currency: list[CurrencyTotals] | None = None


class PeriodSummary(BaseModel):
    """What a close would do, or did.

    Returned by the dry-run preview and by the close itself, so the accountant
    can see the same figures before committing to an irreversible action.
    """

    periode: date
    state: PeriodState
    invoice_count: int
    # Income and cost kept apart: added together they mean nothing (#40).
    total_ht_outgoing: Decimal
    total_ttc_outgoing: Decimal
    total_ht_incoming: Decimal
    total_ttc_incoming: Decimal
    # One entry per currency the month used, TND first (#195). The four
    # totals above are the TND entry.
    totals_by_currency: list[CurrencyTotals] = []
    blocking: list[BlockingInvoice] = []

    @property
    def vat_collected(self) -> Decimal:
        """VAT charged on what we issued."""
        return self.total_ttc_outgoing - self.total_ht_outgoing

    @property
    def vat_deductible(self) -> Decimal:
        """VAT paid on what we bought, which is reclaimable."""
        return self.total_ttc_incoming - self.total_ht_incoming

    @property
    def vat_due(self) -> Decimal:
        """What the VAT return owes: collected minus deductible."""
        return self.vat_collected - self.vat_deductible
