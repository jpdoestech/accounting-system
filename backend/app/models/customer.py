"""
Customer model.

Spec: customer master data for accounts receivable. Kept simple in
this phase -- no customer-specific pricing/credit-limit rules yet
(reasonable Phase 4.x/10 extension).
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Customer(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tin: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(500))
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    payment_terms_days: Mapped[int | None] = mapped_column()
