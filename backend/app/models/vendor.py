"""
Vendor model.

Spec: vendor master data for accounts payable -- the mirror of
Customer (Phase 4). Kept simple in this phase, same reasoning as
Customer: no vendor-specific pricing/credit rules yet.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Vendor(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "vendors"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tin: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    payment_terms_days: Mapped[int | None] = mapped_column()

    # Whether this vendor is itself VAT-registered and whether the
    # business should withhold tax on payments to them -- configurable
    # data a bookkeeper sets per vendor, not inferred by the system.
    is_vat_registered: Mapped[bool] = mapped_column(default=True)
