"""Leave balances (#121): entitlement minus approved days, pending days apart.

The rules of this first version, written on #121:
- a leave day is a working day, Monday to Friday; weekends are not counted;
- public holidays, half days, carry-over and proration are not handled yet
  (#254), so `leave_days` is the one place they will go;
- only paid leave (`paye`) has an entitlement. Sick and unpaid leave are
  counted, not capped;
- a request spanning two years counts in each year for its days in it.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.leaves import LeaveEntitlement, LeaveRequest, LeaveStatus, LeaveType


def leave_days(start: date, end: date) -> int:
    """The working days (Monday to Friday) from `start` to `end`, both included."""
    if end < start:
        return 0
    total = (end - start).days + 1
    weeks, rest = divmod(total, 7)
    days = weeks * 5
    for i in range(rest):
        if (start + timedelta(days=weeks * 7 + i)).weekday() < 5:
            days += 1
    return days


def days_in_year(start: date, end: date, year: int) -> int:
    """The working days of a request that fall in `year`."""
    return leave_days(max(start, date(year, 1, 1)), min(end, date(year, 12, 31)))


def entitlement(db: Session, employee: Employee, year: int) -> Decimal:
    """The paid leave of `employee` for `year`.

    A year already recorded keeps its figure. The current or a past year not
    recorded yet is recorded now, from `annual_entitlement_days`, so a later
    change of that figure never rewrites it. A future year is not recorded:
    it shows today's figure until it starts. Before the year of hire: none.
    """
    if year < employee.hired_on.year:
        return Decimal(0)
    row = _recorded(db, employee.id, year)
    if row is not None:
        return row.days
    days = Decimal(employee.annual_entitlement_days)
    if year > date.today().year:
        return days
    # ON CONFLICT: two first reads at once both try to record the year.
    db.execute(insert(LeaveEntitlement).values(
        employee_id=employee.id, year=year, type_conge=LeaveType.PAYE, days=days,
    ).on_conflict_do_nothing(constraint="uq_employee_year_type"))
    db.commit()
    return _recorded(db, employee.id, year).days


def _recorded(db: Session, employee_id: int, year: int) -> LeaveEntitlement | None:
    return db.query(LeaveEntitlement).filter(
        LeaveEntitlement.employee_id == employee_id,
        LeaveEntitlement.year == year,
        LeaveEntitlement.type_conge == LeaveType.PAYE,
    ).first()


def balances(db: Session, employee: Employee, year: int) -> list[dict]:
    """One balance per leave type, in LeaveType order."""
    first, last = date(year, 1, 1), date(year, 12, 31)
    requests = db.query(LeaveRequest).filter(
        LeaveRequest.employee_id == employee.id,
        LeaveRequest.date_debut <= last,
        LeaveRequest.date_fin >= first,
        LeaveRequest.statut.in_([LeaveStatus.APPROUVE, LeaveStatus.EN_ATTENTE]),
    ).all()

    out = {kind: {"type": kind.value, "entitlement": 0.0, "approvedDays": 0.0,
                  "pendingDays": 0.0, "availableDays": 0.0} for kind in LeaveType}
    for request in requests:
        key = "approvedDays" if request.statut == LeaveStatus.APPROUVE else "pendingDays"
        out[request.type_conge][key] += days_in_year(request.date_debut, request.date_fin, year)

    paid = out[LeaveType.PAYE]
    paid["entitlement"] = float(entitlement(db, employee, year))
    paid["availableDays"] = paid["entitlement"] - paid["approvedDays"]
    return list(out.values())
