from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InventoryItemCreate(BaseModel):
    sku: str
    name: str
    unit_of_measure: str | None = None
    inventory_account_id: str
    cogs_account_id: str


class InventoryItemUpdate(BaseModel):
    sku: str | None = None
    name: str | None = None
    unit_of_measure: str | None = None
    inventory_account_id: str | None = None
    cogs_account_id: str | None = None
    is_active: bool | None = None


class InventoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    unit_of_measure: str | None = None
    inventory_account_id: str
    cogs_account_id: str
    quantity_on_hand: Decimal
    average_cost: Decimal
    is_active: bool


class StockAdjustmentCreate(BaseModel):
    item_id: str
    quantity: Decimal  # positive = increase, negative = decrease
    unit_cost: Decimal | None = None  # required for a positive (receipt) adjustment
    movement_date: date
    memo: str | None = None


class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    item_id: str
    movement_date: date
    movement_type: str
    quantity: Decimal
    unit_cost: Decimal
    total_cost: Decimal
    balance_qty_after: Decimal
    balance_value_after: Decimal
    reference_type: str | None = None
    reference_id: str | None = None
