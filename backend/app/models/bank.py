"""
BankAccount model.

Each bank account links to a GL account (an Asset account in the
chart of accounts, e.g. "1010 - BDO Checking") -- postings to this
bank account always hit that GL account, never a hard-coded "Cash"
code. A business can have multiple bank accounts, each with its own
GL account, so the trial balance always reflects actual cash position
per bank.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class BankAccount(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "bank_accounts"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    gl_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "BDO Checking"
    bank_name: Mapped[str | None] = mapped_column(String(255))
    account_number: Mapped[str | None] = mapped_column(String(50))
    currency_code: Mapped[str] = mapped_column(String(3), default="PHP")

    opening_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    opening_balance_date: Mapped[date | None] = mapped_column(Date)

    is_active: Mapped[bool] = mapped_column(default=True)
