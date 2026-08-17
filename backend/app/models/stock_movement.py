"""
StockMovement model.

An immutable audit trail of every quantity/value change to an
InventoryItem -- created only by app/services/inventory.py, never
edited afterward, mirroring the "no silent changes to posted data"
principle used for JournalEntry since Phase 2. Each row records the
item's running balance immediately after the movement, so the
movement history alone can reconstruct stock value at any point in
time without recomputing from the beginning.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

STOCK_MOVEMENT_TYPES = ("Purchase", "Sale", "Adjustment")


class StockMovement(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "stock_movements"

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    item_id: Mapped[str] = mapped_column(ForeignKey("inventory_items.id"), nullable=False)

    movement_date: Mapped[date] = mapped_column(Date, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # Signed: positive = stock in (purchase, positive adjustment),
    # negative = stock out (sale, negative adjustment).
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    balance_qty_after: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    balance_value_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # e.g. "PurchaseBill" / "SalesInvoice" + the document's id, so a
    # movement can be traced back to what caused it.
    reference_type: Mapped[str | None] = mapped_column(String(50))
    reference_id: Mapped[str | None] = mapped_column(String(50))
