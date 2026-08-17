"""
Chart of Accounts models.

Spec Section 13: fully configurable chart of accounts, hierarchical,
with system/control account flags so the accounting engine can find
its required accounts (e.g. AR control account) without hard-coding
account codes anywhere in Python.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

# Account types are a fixed accounting concept (not a business rule
# that changes with regulation), so this stays as a constrained string
# rather than a configurable table -- unlike tax rules, which change.
ACCOUNT_TYPES = (
    "Asset",
    "Liability",
    "Equity",
    "Revenue",
    "Cost of Sales",
    "Expense",
    "Other Income",
    "Other Expense",
)

# Normal balance side per account type -- used by the posting engine
# and trial balance to know which column (debit/credit) an account's
# balance should appear in.
NORMAL_BALANCE = {
    "Asset": "debit",
    "Liability": "credit",
    "Equity": "credit",
    "Revenue": "credit",
    "Cost of Sales": "debit",
    "Expense": "debit",
    "Other Income": "credit",
    "Other Expense": "debit",
}


class AccountGroup(UUIDPKMixin, TimestampMixin, Base):
    """Optional grouping/heading used to organize accounts in reports."""

    __tablename__ = "account_groups"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("account_groups.id"))


class Account(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("business_id", "code", name="uq_account_code_per_business"),)

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(30), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    group_id: Mapped[str | None] = mapped_column(ForeignKey("account_groups.id"))
    description: Mapped[str | None] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # System accounts are created/required by the engine itself (e.g.
    # a default AR/AP control account) and cannot be deleted from the UI.
    is_system_account: Mapped[bool] = mapped_column(Boolean, default=False)
    is_control_account: Mapped[bool] = mapped_column(Boolean, default=False)

    # Default tax treatment is a configurable hint, not enforced logic
    # here -- the tax engine (Phase 3) owns actual tax calculation.
    default_tax_treatment: Mapped[str | None] = mapped_column(String(50))

    children: Mapped[list["Account"]] = relationship(
        "Account", backref="parent", remote_side="Account.id"
    )
