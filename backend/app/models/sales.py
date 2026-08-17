"""
SalesInvoice / SalesInvoiceLine models.

Spec: the sales module composes the accounting engine (Phase 2) and
tax engine (Phase 3) rather than reimplementing posting or tax logic.
An invoice starts as Draft (editable, not yet in the books) and
becomes Posted through app/services/sales.py, which is the only code
path allowed to create the invoice's JournalEntry -- same rule as the
accounting engine itself (never post from this model or the API
layer directly).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

SALES_INVOICE_STATUSES = ("Draft", "Posted", "Void")


class SalesInvoice(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sales_invoices"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    memo: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(String(20), default="Draft")

    # Set once the invoice is posted -- links the sales document to
    # the journal entry the posting service created for it, so a user
    # can jump from an invoice to its ledger impact and back.
    journal_entry_id: Mapped[str | None] = mapped_column(ForeignKey("journal_entries.id"))

    subtotal: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    lines: Mapped[list["SalesInvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="SalesInvoiceLine.line_number"
    )


class SalesInvoiceLine(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "sales_invoice_lines"

    invoice_id: Mapped[str] = mapped_column(ForeignKey("sales_invoices.id"), nullable=False)
    revenue_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    # If set, this line is inventory-tracked: posting the invoice also
    # issues stock and posts an additional COGS/Inventory entry
    # (app/services/inventory.py).
    item_id: Mapped[str | None] = mapped_column(ForeignKey("inventory_items.id"))

    line_number: Mapped[int] = mapped_column(default=0)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("1.0000"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Optional: the tax rule (e.g. "VAT_STANDARD") to apply to this
    # line via the tax engine. NULL = no tax on this line (e.g. a
    # VAT-exempt or zero-rated item).
    tax_rule_code: Mapped[str | None] = mapped_column(String(50))

    line_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))  # qty * unit_price
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=Decimal("0.00"))

    invoice: Mapped["SalesInvoice"] = relationship(back_populates="lines")
