"""
Business and BusinessSettings models.

Spec Section 11 (Philippine Business Profile) and Section 12
(Multi-Business). Every business-specific record elsewhere in the
system will carry a business_id foreign key so backend queries can
enforce business isolation.
"""
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Business(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "businesses"

    registered_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_name: Mapped[str | None] = mapped_column(String(255))
    tin: Mapped[str | None] = mapped_column(String(20))
    branch_code: Mapped[str | None] = mapped_column(String(10))
    rdo_code: Mapped[str | None] = mapped_column(String(10))
    registered_address: Mapped[str | None] = mapped_column(String(500))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    telephone: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(255))
    line_of_business: Mapped[str | None] = mapped_column(String(255))

    # Configurable classifications -- not hard-coded enums baked into
    # logic, just descriptive values administrators set (Section 2).
    taxpayer_classification: Mapped[str | None] = mapped_column(String(50))
    vat_registration_status: Mapped[str | None] = mapped_column(String(50))
    taxpayer_type: Mapped[str | None] = mapped_column(String(50))

    fiscal_year_start_month: Mapped[int] = mapped_column(default=1)
    currency_code: Mapped[str] = mapped_column(String(3), default="PHP")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    settings: Mapped["BusinessSettings"] = relationship(
        back_populates="business", uselist=False, cascade="all, delete-orphan"
    )


class BusinessSettings(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "business_settings"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), unique=True)

    decimal_precision: Mapped[int] = mapped_column(default=2)
    default_currency_code: Mapped[str] = mapped_column(String(3), default="PHP")
    invoice_number_prefix: Mapped[str | None] = mapped_column(String(20))
    default_payment_terms_days: Mapped[int] = mapped_column(default=30)

    # Control accounts used by transactional modules (Sales, Purchases,
    # etc.) when composing journal entries -- configurable per business
    # rather than hard-coded account codes anywhere in Python. Nullable:
    # a business must set these before posting invoices/bills; the
    # posting services raise a clear error if they're missing rather
    # than guessing an account.
    ar_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    output_vat_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    ap_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    input_vat_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))
    withholding_tax_payable_account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id"))

    business: Mapped["Business"] = relationship(back_populates="settings")
