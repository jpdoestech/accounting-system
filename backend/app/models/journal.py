"""
JournalEntry / JournalLine models.

Spec Section 9: every posted financial transaction must create a
balanced journal entry (total debits = total credits), and the system
must reject unbalanced transactions. This is enforced in the domain
layer (app/accounting/engine/posting.py) -- never trust the frontend
or a raw API payload to have already balanced itself; the engine
re-validates before committing.

Spec Section 117: posted entries are never silently modified. There is
deliberately no "edit journal line" endpoint -- correcting a posted
entry means posting a reversing/adjusting entry, preserving history.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

JOURNAL_ENTRY_STATUSES = ("Draft", "Posted", "Reversed")


class JournalEntry(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "journal_entries"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    period_id: Mapped[str] = mapped_column(ForeignKey("accounting_periods.id"), nullable=False)

    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100))
    memo: Mapped[str | None] = mapped_column(String(500))

    # Free-form source description (e.g. "Sales Invoice", "Manual
    # Journal Voucher") -- later phases will add a typed source_type +
    # source_id pair once sales/purchases exist, without needing to
    # touch this table's shape.
    source: Mapped[str] = mapped_column(String(50), default="Manual")

    status: Mapped[str] = mapped_column(String(20), default="Posted")

    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))

    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="journal_entry", cascade="all, delete-orphan", order_by="JournalLine.line_number"
    )

    def total_debits(self) -> Decimal:
        return sum((line.debit for line in self.lines), Decimal("0.00"))

    def total_credits(self) -> Decimal:
        return sum((line.credit for line in self.lines), Decimal("0.00"))


class JournalLine(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "journal_lines"

    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entries.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    line_number: Mapped[int] = mapped_column(default=0)
    description: Mapped[str | None] = mapped_column(String(500))

    # Exactly one of debit/credit is non-zero per line -- enforced by
    # the posting engine, not by a DB constraint, so a clear
    # application-level error message can be returned (Section 9).
    debit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    credit: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    journal_entry: Mapped["JournalEntry"] = relationship(back_populates="lines")
