"""
FiscalYear and AccountingPeriod models.

Spec Section 117: "The system must never silently modify posted
accounting data ... closed periods." Once a period's status is
Closed, the posting engine must refuse new/modified entries dated
inside it.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

PERIOD_STATUSES = ("Open", "Closed", "Locked")


class FiscalYear(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "fiscal_years"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_fiscal_year_name"),)

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "FY2026"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Open")


class AccountingPeriod(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "accounting_periods"
    __table_args__ = (UniqueConstraint("business_id", "start_date", "end_date", name="uq_period_range"),)

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    fiscal_year_id: Mapped[str] = mapped_column(ForeignKey("fiscal_years.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "2026-01"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Open")
