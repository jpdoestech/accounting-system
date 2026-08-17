"""
TaxRule model.

Spec principle: tax rates and rules are configurable data, never
hard-coded constants in Python, because BIR regulations change. Every
rule is versioned and effective-dated so a historical transaction
always uses the rule version that was in force on its transaction
date -- rules are never retroactively reapplied to already-posted
transactions (spec Section 117 / core requirement on rule versioning).

`tax_type` distinguishes the two PH tax families this phase supports:
  - "VAT": value-added tax (output/input VAT), rate-based.
  - "Withholding": creditable/expanded withholding tax, identified by
    an ATC (Alphanumeric Tax Code), rate-based.

Rules can be business-specific (business_id set) or global defaults
(business_id NULL) that every business inherits unless it defines its
own override -- see app/tax/engine/rules.py for the lookup order.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

TAX_TYPES = ("VAT", "Withholding")
TAX_RULE_STATUSES = ("Draft", "Active", "Superseded", "Retired")


class TaxRule(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "tax_rules"

    # NULL business_id = a system-wide default rule (e.g. standard
    # 12% VAT). A business_id override takes precedence -- see
    # app/tax/engine/rules.py::find_effective_rule.
    business_id: Mapped[str | None] = mapped_column(ForeignKey("businesses.id"))

    rule_code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "VAT_STANDARD", "WT_EWT_1"
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # For withholding rules, the ATC this rule corresponds to (spec:
    # BIR alphanumeric tax codes for expanded withholding tax).
    atc_code: Mapped[str | None] = mapped_column(String(20))

    rate_percent: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)  # e.g. 12.0000, 1.0000

    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)  # NULL = still in effect

    status: Mapped[str] = mapped_column(String(20), default="Active")

    legal_basis: Mapped[str | None] = mapped_column(String(255))  # e.g. "NIRC Sec. 106, as amended by CREATE Act"
    source_reference: Mapped[str | None] = mapped_column(String(255))  # e.g. RR/RMC number
