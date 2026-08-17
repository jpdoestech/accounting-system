"""
InventoryItem model.

Each item links to two GL accounts -- an Inventory Asset account
(where stock value sits while unsold) and a COGS Expense account
(where cost moves to when sold) -- both configurable, never hard-
coded. quantity_on_hand and average_cost are maintained by
app/services/inventory.py using the moving-average costing method:
every receipt recalculates the average; every issue draws down
quantity at the current average without changing it.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class InventoryItem(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("business_id", "sku", name="uq_item_sku_per_business"),)

    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    inventory_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    cogs_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_of_measure: Mapped[str | None] = mapped_column(String(20))

    quantity_on_hand: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"))
    average_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=Decimal("0.0000"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
