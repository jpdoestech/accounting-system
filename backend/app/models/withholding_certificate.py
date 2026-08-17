"""
WithholdingTaxCertificate model.

Represents a generated BIR Form 2307 (Certificate of Creditable Tax
Withheld at Source) issued to a vendor for a period. The certificate
is generated from data already captured on posted purchase bills
(app/models/purchase.py::PurchaseBillLine.withholding_tax_amount,
tracked since Phase 5) -- this model persists the *result* of that
generation (so a certificate number, once issued, stays stable and
reissuable) rather than recomputing from scratch every time it's
viewed.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

CERTIFICATE_STATUSES = ("Draft", "Issued")


class WithholdingTaxCertificate(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "withholding_tax_certificates"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)

    certificate_number: Mapped[str] = mapped_column(String(50), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    total_income_payment: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total_tax_withheld: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="Draft")
