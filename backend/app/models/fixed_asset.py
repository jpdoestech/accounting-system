"""
FixedAsset model.

Each asset links to three configurable GL accounts: the Asset account
(where acquisition cost sits), an Accumulated Depreciation contra-
asset account, and a Depreciation Expense account -- never hard-coded.
Depreciation is straight-line only (spec-reasonable default for PH
SMEs); useful_life_months and salvage_value together with
acquisition_cost determine the monthly depreciation amount, computed
by app/services/fixed_assets.py, never stored redundantly here.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

FIXED_ASSET_STATUSES = ("Active", "Fully Depreciated", "Disposed")


class FixedAsset(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "fixed_assets"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    asset_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    accumulated_depreciation_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    depreciation_expense_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    asset_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False)
    acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    salvage_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    useful_life_months: Mapped[int] = mapped_column(nullable=False)

    accumulated_depreciation: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="Active")
