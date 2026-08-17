"""
Budget / BudgetLine models.

An annual budget: one amount per account for the whole fiscal year
(not monthly-granular, to keep this phase's scope reasonable -- see
Phase 10 report's Known Issues). Variance reporting
(app/reports/financial/budget_variance.py) compares this against
actual activity for the same fiscal year, read entirely from posted
journal lines -- budgets never affect posting or the accounting engine
in any way; they're purely a comparison target.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

BUDGET_STATUSES = ("Draft", "Approved")


class Budget(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (UniqueConstraint("business_id", "fiscal_year_id", "name", name="uq_budget_name_per_fy"),)

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    fiscal_year_id: Mapped[str] = mapped_column(ForeignKey("fiscal_years.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft")

    lines: Mapped[list["BudgetLine"]] = relationship(back_populates="budget", cascade="all, delete-orphan")


class BudgetLine(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "budget_lines"
    __table_args__ = (UniqueConstraint("budget_id", "account_id", name="uq_budget_line_account"),)

    budget_id: Mapped[str] = mapped_column(ForeignKey("budgets.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    budgeted_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    budget: Mapped["Budget"] = relationship(back_populates="lines")
