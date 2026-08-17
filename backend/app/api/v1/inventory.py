"""
Inventory API endpoints: items and stock movements. Stock adjustments
(manual quantity corrections, e.g. after a physical count) go through
the same receive_stock/issue_stock functions sales and purchases use
-- no separate adjustment logic to keep in sync with the costing
method.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business
from app.models.inventory_item import InventoryItem
from app.models.stock_movement import StockMovement
from app.models.user import User, UserBusinessRole
from app.schemas.inventory import (
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    StockAdjustmentCreate,
    StockMovementRead,
)
from app.services.inventory import InventoryError, issue_stock, receive_stock

router = APIRouter(prefix="/businesses/{business_id}", tags=["inventory"])


def _get_authorized_business(business_id: str, db: Session, current_user: User) -> Business:
    access = (
        db.query(UserBusinessRole)
        .filter(
            UserBusinessRole.user_id == current_user.id,
            UserBusinessRole.business_id == business_id,
        )
        .first()
    )
    if not access:
        raise HTTPException(status_code=404, detail="Business not found")
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.post("/inventory-items", response_model=InventoryItemRead, status_code=201)
def create_inventory_item(
    business_id: str,
    payload: InventoryItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    existing = (
        db.query(InventoryItem)
        .filter(InventoryItem.business_id == business_id, InventoryItem.sku == payload.sku)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"SKU '{payload.sku}' already exists.")

    item = InventoryItem(business_id=business_id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/inventory-items", response_model=list[InventoryItemRead])
def list_inventory_items(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(InventoryItem)
        .filter(InventoryItem.business_id == business_id)
        .order_by(InventoryItem.sku)
        .all()
    )


@router.put("/inventory-items/{item_id}", response_model=InventoryItemRead)
def update_inventory_item(
    business_id: str,
    item_id: str,
    payload: InventoryItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    item = (
        db.query(InventoryItem)
        .filter(InventoryItem.id == item_id, InventoryItem.business_id == business_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    updates = payload.model_dump(exclude_unset=True)
    if "sku" in updates and updates["sku"] != item.sku:
        clash = (
            db.query(InventoryItem)
            .filter(InventoryItem.business_id == business_id, InventoryItem.sku == updates["sku"])
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail=f"SKU '{updates['sku']}' already exists.")
    for field, value in updates.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.get("/inventory-items/{item_id}/movements", response_model=list[StockMovementRead])
def list_stock_movements(
    business_id: str,
    item_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    item = db.get(InventoryItem, item_id)
    if not item or item.business_id != business_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")
    return (
        db.query(StockMovement)
        .filter(StockMovement.item_id == item_id)
        .order_by(StockMovement.movement_date, StockMovement.created_at)
        .all()
    )


@router.post("/stock-adjustments", response_model=StockMovementRead, status_code=201)
def create_stock_adjustment(
    business_id: str,
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    item = db.get(InventoryItem, payload.item_id)
    if not item or item.business_id != business_id:
        raise HTTPException(status_code=404, detail="Inventory item not found.")

    try:
        if payload.quantity > 0:
            if payload.unit_cost is None:
                raise InventoryError("unit_cost is required for a positive (stock-in) adjustment.")
            movement = receive_stock(
                db,
                item=item,
                quantity=payload.quantity,
                unit_cost=payload.unit_cost,
                movement_date=payload.movement_date,
                reference_type="Adjustment",
                reference_id=None,
            )
        else:
            result = issue_stock(
                db,
                item=item,
                quantity=-payload.quantity,
                movement_date=payload.movement_date,
                reference_type="Adjustment",
                reference_id=None,
            )
            movement = result.movement
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    db.commit()
    db.refresh(movement)
    return movement
