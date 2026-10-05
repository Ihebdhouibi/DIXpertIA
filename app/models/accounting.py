import enum

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class PeriodState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class AccountingPeriod(Base):
    """One month of the accountant's books, and whether it is finished (#42).

    A table rather than a month derived from `date_emission`, because closing
    is an event and not a property of the invoices: it has an actor, a moment,
    and a result worth keeping. Deriving the month would record none of that,
    so nobody could answer "who closed January, and when".

    Closing is irreversible, decided alongside #41. A closed month's figures
    never change afterwards, which is what makes them reportable. A mistake
    found later is corrected by a new document in the open month, referencing
    the original - never by editing a closed one.

    There is deliberately no reopen path. If the accountant turns out to need
    one, it belongs here with an audit record, not as a column someone edits by
    hand; note that it could not un-archive the invoices themselves, which #41
    freezes with a trigger.
    """

    __tablename__ = "accounting_periods"

    id = Column(Integer, primary_key=True)
    # A Date standing for a month, pinned to the 1st - the same convention as
    # payslips.periode, so the two read alike.
    periode = Column(Date, nullable=False, unique=True)
    state = Column(
        Enum(PeriodState),
        nullable=False,
        server_default=PeriodState.OPEN.name,
    )
    # Null while open; both set together at the close. The CHECK below keeps
    # them consistent, so "closed" can never mean "closed by nobody".
    closed_at = Column(DateTime(timezone=True))
    closed_by_id = Column(String, ForeignKey("users.id", ondelete="RESTRICT"))

    # What the close found, recorded at the moment it ran. The invoices are
    # frozen afterwards, so these should still match a recount at any later
    # date; a mismatch means something bypassed the rules.
    #
    # Split by direction (#40). One pair of totals would add revenue to cost and
    # produce a figure meaning nothing. Kept apart, the same columns also give
    # the VAT return: ttc - ht on the outgoing side is VAT collected, and on the
    # incoming side VAT deductible, and the difference is what is owed.
    invoice_count = Column(Integer)
    total_ht_outgoing = Column(Numeric(12, 2))
    total_ttc_outgoing = Column(Numeric(12, 2))
    total_ht_incoming = Column(Numeric(12, 2))
    total_ttc_incoming = Column(Numeric(12, 2))

    closed_by = relationship("User")

    __table_args__ = (
        CheckConstraint(
            "extract(day FROM periode) = 1",
            name="ck_period_is_month_start",
        ),
        # Not for reads: closed_by_id is ON DELETE RESTRICT, so without this
        # deleting a user who has closed nothing scans the whole table to prove
        # it, while holding locks (#61).
        Index("ix_accounting_periods_closed_by_id", "closed_by_id"),
        # An open period knows nothing about a close; a closed one records all
        # of it. Without this a row could claim to be closed with no actor.
        CheckConstraint(
            "(state = 'OPEN' AND closed_at IS NULL AND closed_by_id IS NULL"
            " AND invoice_count IS NULL AND total_ht_outgoing IS NULL"
            " AND total_ttc_outgoing IS NULL AND total_ht_incoming IS NULL"
            " AND total_ttc_incoming IS NULL)"
            " OR (state = 'CLOSED' AND closed_at IS NOT NULL AND closed_by_id IS NOT NULL"
            " AND invoice_count IS NOT NULL AND total_ht_outgoing IS NOT NULL"
            " AND total_ttc_outgoing IS NOT NULL AND total_ht_incoming IS NOT NULL"
            " AND total_ttc_incoming IS NOT NULL)",
            name="ck_period_close_is_complete",
        ),
    )
