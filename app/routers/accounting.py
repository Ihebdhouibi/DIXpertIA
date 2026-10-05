"""The accountant's monthly close (#42).

Closing a month is irreversible, so the endpoints here are deliberately
cautious: a preview shows exactly what a close would do, the close itself
refuses while any invoice in the month is unfinished, and it names the ones
blocking it rather than reporting a count.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.models.accounting import AccountingPeriod, PeriodState
from app.models.invoicing import (
    Invoice,
    InvoiceDirection,
    InvoiceProcessingStatus,
)
from app.models.user import User
from app.schemas.accounting import BlockingInvoice, PeriodOut, PeriodSummary

# Keeping the books is the accountant's job, and the admin's by virtue of
# running the company. `rh` is excluded, as it is for an invoice's processing
# status: this is bookkeeping, not a commercial act.
router = APIRouter(dependencies=[Depends(require_roles("admin", "accountant"))])

MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


def _month_bounds(month: str) -> tuple[date, date]:
    """Return the first day of `month` and the first day of the next one."""
    year, mon = int(month[:4]), int(month[5:])
    start = date(year, mon, 1)
    end = date(year + (mon == 12), mon % 12 + 1, 1)
    return start, end


def _summarise(db: Session, start: date, end: date) -> dict:
    """Count the month's invoices and total them, income apart from cost.

    Adding the two together would produce a figure meaning nothing. Kept apart,
    these also give the VAT return: ttc - ht is VAT collected on the outgoing
    side and VAT deductible on the incoming one (#40).
    """
    def totals(direction):
        row = db.query(
            func.count(Invoice.id),
            func.coalesce(func.sum(Invoice.montant_ht), 0),
            func.coalesce(func.sum(Invoice.montant_ttc), 0),
        ).filter(
            Invoice.date_emission >= start,
            Invoice.date_emission < end,
            Invoice.direction == direction,
        ).one()
        return row

    out = totals(InvoiceDirection.OUTGOING)
    inc = totals(InvoiceDirection.INCOMING)
    return {
        "invoice_count": out[0] + inc[0],
        "total_ht_outgoing": out[1],
        "total_ttc_outgoing": out[2],
        "total_ht_incoming": inc[1],
        "total_ttc_incoming": inc[2],
    }


def _blocking(db: Session, start: date, end: date) -> list[Invoice]:
    """Invoices in the month that are not yet completed.

    An invoice still pending or processed means the month's books are not
    finished, so closing it would freeze unfinished work: archived is terminal
    (#41), and those invoices could never be booked afterwards.
    """
    return (
        db.query(Invoice)
        .filter(
            Invoice.date_emission >= start,
            Invoice.date_emission < end,
            Invoice.processing_status != InvoiceProcessingStatus.COMPLETED,
        )
        .order_by(Invoice.date_emission, Invoice.id)
        .all()
    )


@router.get("/periods", response_model=list[PeriodOut])
def list_periods(db: Session = Depends(get_db)):
    """Every period on record, newest first."""
    return db.query(AccountingPeriod).order_by(AccountingPeriod.periode.desc()).all()


@router.get("/periods/{month}", response_model=PeriodSummary)
def preview_period(
    month: str = Path(pattern=MONTH, description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    """Show what closing this month would do, without doing it.

    Exists because the close cannot be undone. The accountant sees the same
    figures and the same blocking list beforehand as the close would act on.
    """
    start, end = _month_bounds(month)
    period = db.query(AccountingPeriod).filter(
        AccountingPeriod.periode == start).first()
    return PeriodSummary(
        periode=start,
        state=period.state if period else PeriodState.OPEN,
        blocking=[BlockingInvoice.model_validate(i) for i in _blocking(db, start, end)],
        **_summarise(db, start, end),
    )


@router.post("/periods/{month}/close", response_model=PeriodSummary)
def close_period(
    response: Response,
    month: str = Path(pattern=MONTH, description="YYYY-MM"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Close a month: archive its invoices and seal it.

    Refused while any invoice in the month is not `completed`, and the response
    names them. Closing with unfinished work would archive it, and an archived
    invoice is terminal - nobody could book it afterwards.

    Irreversible by design. There is no reopen: a closed month's figures never
    change, which is what makes them reportable. A mistake found later is
    corrected by a new document in the open month.
    """
    start, end = _month_bounds(month)

    period = db.query(AccountingPeriod).filter(
        AccountingPeriod.periode == start).with_for_update().first()
    if period and period.state == PeriodState.CLOSED:
        raise HTTPException(
            status_code=409,
            detail=f"the accounting period {month} is already closed and cannot be reopened",
        )

    blocking = _blocking(db, start, end)
    if blocking:
        # 409 rather than 422: the request is well formed, the books are not
        # ready. The list is the accountant's worklist.
        response.status_code = 409
        return PeriodSummary(
            periode=start,
            state=PeriodState.OPEN,
            blocking=[BlockingInvoice.model_validate(i) for i in blocking],
            **_summarise(db, start, end),
        )

    totals = _summarise(db, start, end)

    # Archive, then seal, both in one transaction: either the month closes
    # completely or nothing changed. The order is not load-bearing - the
    # period trigger watches INSERT and date_emission, which this update does
    # not touch - but it reads in the order the accountant thinks in.
    db.query(Invoice).filter(
        Invoice.date_emission >= start,
        Invoice.date_emission < end,
    ).update({Invoice.processing_status: InvoiceProcessingStatus.ARCHIVED},
             synchronize_session=False)

    if period is None:
        period = AccountingPeriod(periode=start)
        db.add(period)
    period.state = PeriodState.CLOSED
    period.closed_at = func.now()
    period.closed_by_id = current_user.id
    for field, value in totals.items():
        setattr(period, field, value)

    db.commit()
    return PeriodSummary(periode=start, state=PeriodState.CLOSED,
                         blocking=[], **totals)
