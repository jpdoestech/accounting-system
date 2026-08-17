"""
PurchaseBill / PurchaseBillLine models.

Mirrors SalesInvoice/SalesInvoiceLine (Phase 4), with one addition
specific to Philippine purchases: expanded/creditable withholding tax.
When a business pays a vendor for services (or certain goods), it
often must withhold a percentage and remit it to the BIR on the
vendor's behalf -- so the amount actually paid to the vendor is less
than the invoice's grand total, and the difference is a liability
(Withholding Tax Payable) rather than cash paid out.

Draft -> Posted lifecycle, same immutability rule as JournalEntry and
SalesInvoice: correcting a posted bill means reversing it, not editing
it in place.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

PURCHASE_BILL_STATUSES = ("Draft", "Posted", "Void")


class PurchaseBill(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "purchase_bills"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    vendor_id: Mapped[str] = mapped_column(ForeignKey("vendors.id"), nullable=False)

    bill_number: Mapped[str] = mapped_column(String(50), nullable=False)  # vendor's own invoice/OR number
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    memo: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="Draft")
    journal_entry_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entries.id"))

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    input_vat_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    withholding_tax_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))  # subtotal + input VAT
    amount_due_to_vendor: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), default=Decimal("0.00")
    )  # grand_total - withholding_tax_total

    lines: Mapped[list["PurchaseBillLine"]] = relationship(
        back_populates="bill", cascade="all, delete-orphan", order_by="PurchaseBillLine.line_number"
    )


class PurchaseBillLine(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "purchase_bill_lines"

    bill_id: Mapped[str] = mapped_column(ForeignKey("purchase_bills.id"), nullable=False)
    expense_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    # If set, this line is inventory-tracked: the debit goes to the
    # item's inventory account instead of expense_account_id, and
    # posting the bill also receives stock (app/services/inventory.py).
    item_id: Mapped[str | None] = mapped_column(ForeignKey("inventory_items.id"))

    line_number: Mapped[int] = mapped_column(default=0)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("1.0000"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Input VAT rule (e.g. "VAT_STANDARD"). NULL = no VAT on this line.
    tax_rule_code: Mapped[str | None] = mapped_column(String(50))
    # Withholding tax rule/ATC (e.g. "WT_EWT_PROF_FEES"). NULL = nothing withheld on this line.
    withholding_tax_rule_code: Mapped[str | None] = mapped_column(String(50))

    line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    withholding_tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    bill: Mapped["PurchaseBill"] = relationship(back_populates="lines")
