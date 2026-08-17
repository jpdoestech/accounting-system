"""
CashReceipt / CashReceiptAllocation models.

A cash receipt records money coming in from a customer against a bank
account. Its journal entry is always the same two-line shape --
Debit Bank, Credit Accounts Receivable -- regardless of how many
invoices it's applied to; the allocations exist to track *which*
invoices the payment covers (for AR reporting/aging in a later
phase), not to add more journal lines. A receipt can leave part of
its amount unallocated (an on-account/advance payment) -- allocations
may sum to less than the receipt amount, but never more.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

CASH_RECEIPT_STATUSES = ("Draft", "Posted", "Void")


class CashReceipt(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cash_receipts"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)

    receipt_number: Mapped[str] = mapped_column(String(50), nullable=False)
    receipt_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="Draft")
    journal_entry_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entries.id"))

    # Bank reconciliation fields -- set once this receipt is matched
    # against a bank statement line (see app/services/reconciliation.py).
    is_cleared: Mapped[bool] = mapped_column(default=False)
    cleared_date: Mapped[date | None] = mapped_column(Date)

    allocations: Mapped[list["CashReceiptAllocation"]] = relationship(
        back_populates="receipt", cascade="all, delete-orphan"
    )


class CashReceiptAllocation(UUIDPKMixin, TimestampMixin, Base):
    """Which sales invoice(s) this receipt pays down, and how much."""

    __tablename__ = "cash_receipt_allocations"

    receipt_id: Mapped[str] = mapped_column(ForeignKey("cash_receipts.id"), nullable=False)
    sales_invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id"), nullable=False)
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    receipt: Mapped["CashReceipt"] = relationship(back_populates="allocations")
