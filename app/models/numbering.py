from sqlalchemy import CheckConstraint, Column, Integer, String

from app.core.database import Base


class InvoiceSequence(Base):
    """The next invoice number, one row per year (#38).

    A counter table rather than a PostgreSQL sequence, because a sequence is
    explicitly NOT gapless: it does not roll back when a transaction fails, by
    design, so that concurrent writers never block each other. An invoice
    number is a legal artefact and must have no holes, so the opposite
    trade-off is the right one here.

    Allocation happens inside the transaction that creates the invoice:

        UPDATE invoice_sequences SET last_number = last_number + 1
        WHERE year = :year RETURNING last_number

    That takes a row lock held until commit, which gives both properties the
    accountant asked for:

    - two concurrent creates serialise, so neither can take the same number
    - a failed create rolls the counter back with it, so no number is burned

    The cost is that invoice creation serialises on this row. That is a
    deliberate choice, not an oversight: a gapless counter and high write
    concurrency are fundamentally in tension, and this company issues a few
    invoices a day. If volume ever makes the lock hurt, the answer is to
    allocate at issue time rather than at draft creation, not to drop the lock.

    The series restarts each year, which is why `year` is part of the key:
    FA-2026-0001 follows FA-2025-0184. Decided with the accountant on #38.

    `series` is the other half of the key, added with #40. Sales and purchases
    each run their own numbering - FA for invoices we issue, FF for the internal
    reference we give a supplier's bill - and a shared counter would interleave
    them, so FA-2026-0003 could be followed by FA-2026-0007 with the gap taken
    by a purchase.
    """

    __tablename__ = "invoice_sequences"

    # 'FA' for outgoing, 'FF' for incoming. Two characters, matching the prefix
    # of the numbers it hands out.
    series = Column(String(2), primary_key=True)
    year = Column(Integer, primary_key=True, autoincrement=False)
    # The last number handed out. 0 means the year has issued nothing yet, so
    # the first invoice of a year is 1 - the accountant's "starts at 1".
    last_number = Column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        CheckConstraint("last_number >= 0", name="ck_invoice_sequence_not_negative"),
        CheckConstraint("year BETWEEN 2000 AND 2999", name="ck_invoice_sequence_year"),
        CheckConstraint("series IN ('FA', 'FF')", name="ck_invoice_sequence_series"),
    )
