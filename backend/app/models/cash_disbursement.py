"""
CashDisbursement / CashDisbursementAllocation models.

Mirrors CashReceipt for money going out to a vendor. Its journal
entry is always Debit Accounts Payable, Credit Bank -- the amount
paid should typically equal a bill's amount_due_to_vendor (grand
total minus any withholding tax already recorded when the bill was
posted, Phase 5), not the bill's full grand_total.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

CASH_DISBURSEMENT_STATUSES = ("Draft", "Posted", "Void")


class CashDisbursement(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "cash_disbursements"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(ForeignKey("bank_accounts.id"), nullable=False)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)

    payment_number: Mapped[str] = mapped_column(String(50), nullable=False)  # check no. / reference
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    memo: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="Draft")
    journal_entry_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entries.id"))

    is_cleared: Mapped[bool] = mapped_column(default=False)
    cleared_date: Mapped[date | None] = mapped_column(Date)

    allocations: Mapped[list["CashDisbursementAllocation"]] = relationship(
        back_populates="disbursement", cascade="all, delete-orphan"
    )


class CashDisbursementAllocation(UUIDPKMixin, TimestampMixin, Base):
    """Which purchase bill(s) this payment settles, and how much."""

    __tablename__ = "cash_disbursement_allocations"

    disbursement_id: Mapped[str] = mapped_column(ForeignKey("cash_disbursements.id"), nullable=False)
    purchase_bill_id: Mapped[str] = mapped_column(ForeignKey("purchase_bills.id"), nullable=False)
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    disbursement: Mapped["CashDisbursement"] = relationship(back_populates="allocations")
