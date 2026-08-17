"""
DepreciationEntry model.

One row per posted monthly depreciation run for a fixed asset --
immutable once created, mirroring StockMovement (Phase 8) and
JournalEntry (Phase 2): the record of what was posted, never edited
afterward. Prevents double-posting depreciation for the same
asset/period via a uniqueness constraint.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DepreciationEntry(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "depreciation_entries"
    __table_args__ = (
        UniqueConstraint("asset_id", "period_year", "period_month", name="uq_depreciation_asset_period"),
    )

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("fixed_assets.id"), nullable=False)
    journal_entry_id: Mapped[str] = mapped_column(ForeignKey("journal_entries.id"), nullable=False)

    period_year: Mapped[int] = mapped_column(nullable=False)
    period_month: Mapped[int] = mapped_column(nullable=False)  # 1-12
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)

    depreciation_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    accumulated_depreciation_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    book_value_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
