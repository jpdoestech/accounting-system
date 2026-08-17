"""
BankReconciliation model.

Records one reconciliation attempt for a bank account against a bank
statement: the statement's ending balance, the book-side balance
computed from cleared receipts/disbursements as of that date, and the
difference. A reconciliation with zero difference is Completed;
otherwise it stays Draft so a bookkeeper can keep marking transactions
cleared (or investigating discrepancies) before finishing.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

RECONCILIATION_STATUSES = ("Draft", "Completed")


class BankReconciliation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "bank_reconciliations"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)

    statement_date: Mapped[date] = mapped_column(Date, nullable=False)
    statement_ending_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    book_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    difference: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="Draft")
