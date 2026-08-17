"""
Inventory stock movement service.

Implements moving-average costing: every receipt recalculates the
item's average cost as a weighted average of what was on hand and
what came in; every issue draws quantity down at the *current*
average cost without changing it. This is the only code path allowed
to change InventoryItem.quantity_on_hand/average_cost or create a
StockMovement -- app/services/sales.py and purchases.py call into
this module rather than touching those fields directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.inventory_item import InventoryItem
from app.models.stock_movement import StockMovement
from app.utils.money import to_money, zero


class InventoryError(Exception):
    """Raised when a stock movement cannot be recorded."""


@dataclass
class IssueResult:
    quantity_issued: Decimal
    unit_cost_used: Decimal
    total_cost: Decimal
    movement: StockMovement


def receive_stock(
    db: Session,
    *,
    item: InventoryItem,
    quantity: Decimal,
    unit_cost: Decimal,
    movement_date: date,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> StockMovement:
    if quantity <= 0:
        raise InventoryError("Received quantity must be positive.")

    unit_cost = to_money(unit_cost)

    old_qty = item.quantity_on_hand
    old_value = to_money(old_qty * item.average_cost)
    incoming_value = to_money(quantity * unit_cost)

    new_qty = old_qty + quantity
    new_value = old_value + incoming_value
    new_average_cost = (new_value / new_qty) if new_qty > 0 else zero()

    item.quantity_on_hand = new_qty
    item.average_cost = new_average_cost

    movement = StockMovement(
        business_id=item.business_id,
        item_id=item.id,
        movement_date=movement_date,
        movement_type="Purchase" if reference_type == "PurchaseBill" else "Adjustment",
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=incoming_value,
        balance_qty_after=new_qty,
        balance_value_after=new_value,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(movement)
    db.flush()
    return movement


def issue_stock(
    db: Session,
    *,
    item: InventoryItem,
    quantity: Decimal,
    movement_date: date,
    reference_type: str | None = None,
    reference_id: str | None = None,
) -> IssueResult:
    if quantity <= 0:
        raise InventoryError("Issued quantity must be positive.")
    if quantity > item.quantity_on_hand:
        raise InventoryError(
            f"Cannot issue {quantity} of '{item.name}': only {item.quantity_on_hand} on hand."
        )

    unit_cost = item.average_cost
    total_cost = to_money(quantity * unit_cost)

    new_qty = item.quantity_on_hand - quantity
    new_value = to_money(new_qty * item.average_cost)

    item.quantity_on_hand = new_qty
    # average_cost is unchanged by an issue -- moving-average costing
    # only recalculates on receipt.

    movement = StockMovement(
        business_id=item.business_id,
        item_id=item.id,
        movement_date=movement_date,
        movement_type="Sale" if reference_type == "SalesInvoice" else "Adjustment",
        quantity=-quantity,
        unit_cost=unit_cost,
        total_cost=-total_cost,
        balance_qty_after=new_qty,
        balance_value_after=new_value,
        reference_type=reference_type,
        reference_id=reference_id,
    )
    db.add(movement)
    db.flush()

    return IssueResult(quantity_issued=quantity, unit_cost_used=unit_cost, total_cost=total_cost, movement=movement)
