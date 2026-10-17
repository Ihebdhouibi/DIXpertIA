"""The dashboard's figures, computed by the database (#120).

The dashboard used to add up the lists it loaded in the browser, capped at the
API's page size: 200 invoices, 50 leave requests and employees. Past that cap
every figure was silently partial. Here each one is a COUNT or a SUM over every
row the caller may see.

Role scoping, on the server:
- invoices: admin and accountant. An employee gets no invoice block at all
  (the API already refuses them invoices, #55), not a block of zeros.
- team: admin.
- leave: everyone, through row-level security: an employee or an accountant
  counts their own pending requests, the admin everyone's - the same rule as
  the leave list, held by the same policy.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, case, cast, func, literal_column
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.employee import Employee, EmploymentStatus
from app.models.invoicing import Invoice, InvoiceDirection, InvoiceProcessingStatus, InvoiceStatus
from app.models.leaves import LeaveRequest, LeaveStatus
from app.models.user import User
from app.schemas.api import INVOICE_PROCESSING_STATUS_TO_API, INVOICE_STATUS_TO_API
from app.schemas.dashboard import (
    DashboardSummary, DirectionTotal, InvoiceFigures, LeaveFigures, StatusFigure, TeamFigures,
)

router = APIRouter()

MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"

# In the order the dashboard shows them.
COMMERCIAL = (InvoiceStatus.BROUILLON, InvoiceStatus.ENVOYEE, InvoiceStatus.PAYEE,
              InvoiceStatus.EN_RETARD, InvoiceStatus.ANNULEE)


def _invoice_figures(db: Session, month: Optional[str]) -> InvoiceFigures:
    query = db.query(Invoice)
    if month:
        start = date(int(month[:4]), int(month[5:]), 1)
        end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
        query = query.filter(Invoice.date_emission >= start, Invoice.date_emission < end)
    rows = query.subquery()

    # The commercial status as shown: a sent invoice past its due date is
    # overdue (#117). The same "today" as Invoice.displayed_status(), so the
    # dashboard and the invoice list never disagree. Enum NAMEs, as stored.
    today = date.today()
    shown = case(
        ((rows.c.statut == InvoiceStatus.ENVOYEE) & (rows.c.date_echeance < today), InvoiceStatus.EN_RETARD.name),
        else_=cast(rows.c.statut, Text),
    )
    # One grouped query per axis. The totals below are the sums of these
    # groups, so a count and its amount always come from the same rows.
    # GROUP BY 1, not the expression: `today` would be a second bind
    # parameter there, and PostgreSQL would not see the two as the same.
    first = literal_column("1")
    by_status = {
        name: (count, float(amount or 0))
        for name, count, amount in db.query(shown, func.count(), func.sum(rows.c.montant_ttc)).group_by(first).all()
    }
    processing = cast(rows.c.processing_status, Text)
    by_processing = dict(db.query(processing, func.count()).group_by(first).all())
    direction = cast(rows.c.direction, Text)
    by_direction = {
        name: DirectionTotal(count=count, amount=round(float(amount or 0), 3))
        for name, count, amount in db.query(direction, func.count(), func.sum(rows.c.montant_ttc)).group_by(first).all()
    }
    none = DirectionTotal(count=0, amount=0.0)

    statuses = [
        StatusFigure(status=INVOICE_STATUS_TO_API[s.value],
                     count=by_status.get(s.name, (0, 0.0))[0], amount=by_status.get(s.name, (0, 0.0))[1])
        for s in COMMERCIAL
    ]
    states = [
        StatusFigure(status=INVOICE_PROCESSING_STATUS_TO_API[p.value], count=by_processing.get(p.name, 0))
        for p in InvoiceProcessingStatus
    ]
    return InvoiceFigures(
        count=sum(s.count for s in statuses),
        clients=by_direction.get(InvoiceDirection.OUTGOING.name, none),
        suppliers=by_direction.get(InvoiceDirection.INCOMING.name, none),
        byStatus=statuses,
        byProcessing=states,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(
    month: Optional[str] = Query(None, pattern=MONTH, description="YYYY-MM: invoice figures of that month only"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The figures the dashboard shows, exact whatever the number of rows (#120).

    `invoices` is null for an employee and `team` for anyone but the admin:
    null means "not yours to see", never zero.
    """
    role = current_user.role
    pending = db.query(func.count(LeaveRequest.id)).filter(LeaveRequest.statut == LeaveStatus.EN_ATTENTE).scalar()

    team = None
    if role == "admin":
        total, active = db.query(
            func.count(Employee.id),
            func.count(Employee.id).filter(Employee.employment_status == EmploymentStatus.ACTIVE),
        ).one()
        team = TeamFigures(active=active, total=total)

    return DashboardSummary(
        month=month,
        invoices=_invoice_figures(db, month) if role in ("admin", "accountant") else None,
        leave=LeaveFigures(pending=pending),
        team=team,
    )
