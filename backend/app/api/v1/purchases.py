"""
Purchases API endpoints: vendors and purchase bills. Mirrors
app/api/v1/sales.py -- see that module's docstring for the
Draft-then-explicit-Post reasoning.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business
from app.models.purchase import PurchaseBill
from app.models.user import User, UserBusinessRole
from app.models.vendor import Vendor
from app.schemas.purchases import (
    PurchaseBillCreate,
    PurchaseBillRead,
    VendorCreate,
    VendorRead,
    VendorUpdate,
)
from app.services.purchases import (
    BillLineInput,
    PurchasePostingError,
    create_draft_bill,
    post_bill,
    update_draft_bill,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["purchases"])


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


# ----------------------------------------------------------------- vendors

@router.post("/vendors", response_model=VendorRead, status_code=201)
def create_vendor(
    business_id: str,
    payload: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    vendor = Vendor(business_id=business_id, **payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors", response_model=list[VendorRead])
def list_vendors(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return db.query(Vendor).filter(Vendor.business_id == business_id).order_by(Vendor.name).all()


def _get_vendor_or_404(business_id: str, vendor_id: str, db: Session) -> Vendor:
    vendor = (
        db.query(Vendor)
        .filter(Vendor.id == vendor_id, Vendor.business_id == business_id)
        .first()
    )
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/vendors/{vendor_id}", response_model=VendorRead)
def update_vendor(
    business_id: str,
    vendor_id: str,
    payload: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    vendor = _get_vendor_or_404(business_id, vendor_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.delete("/vendors/{vendor_id}", status_code=204)
def delete_vendor(
    business_id: str,
    vendor_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    vendor = _get_vendor_or_404(business_id, vendor_id, db)
    db.delete(vendor)
    db.commit()
    return None


# ----------------------------------------------------------- purchase bills

@router.post("/purchase-bills", response_model=PurchaseBillRead, status_code=201)
def create_purchase_bill(
    business_id: str,
    payload: PurchaseBillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)

    vendor = db.get(Vendor, payload.vendor_id)
    if not vendor or vendor.business_id != business_id:
        raise HTTPException(status_code=400, detail="Vendor not found for this business.")

    lines = [
        BillLineInput(
            expense_account_id=l.expense_account_id,
            description=l.description,
            quantity=l.quantity,
            unit_price=l.unit_price,
            tax_rule_code=l.tax_rule_code,
            withholding_tax_rule_code=l.withholding_tax_rule_code,
            item_id=l.item_id,
        )
        for l in payload.lines
    ]

    try:
        bill = create_draft_bill(
            db,
            business_id=business_id,
            vendor_id=payload.vendor_id,
            bill_number=payload.bill_number,
            bill_date=payload.bill_date,
            due_date=payload.due_date,
            lines=lines,
            memo=payload.memo,
        )
    except PurchasePostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return bill


@router.get("/purchase-bills", response_model=list[PurchaseBillRead])
def list_purchase_bills(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(PurchaseBill)
        .filter(PurchaseBill.business_id == business_id)
        .order_by(PurchaseBill.bill_date.desc())
        .all()
    )


@router.get("/purchase-bills/{bill_id}", response_model=PurchaseBillRead)
def get_purchase_bill(
    business_id: str,
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    bill = db.get(PurchaseBill, bill_id)
    if not bill or bill.business_id != business_id:
        raise HTTPException(status_code=404, detail="Purchase bill not found.")
    return bill


@router.put("/purchase-bills/{bill_id}", response_model=PurchaseBillRead)
def update_purchase_bill(
    business_id: str,
    bill_id: str,
    payload: PurchaseBillCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    bill = db.get(PurchaseBill, bill_id)
    if not bill or bill.business_id != business_id:
        raise HTTPException(status_code=404, detail="Purchase bill not found.")
    if bill.status != "Draft":
        raise HTTPException(status_code=400, detail="Only draft bills can be edited. Void/reverse a posted bill instead.")

    vendor = db.get(Vendor, payload.vendor_id)
    if not vendor or vendor.business_id != business_id:
        raise HTTPException(status_code=400, detail="Vendor not found for this business.")

    lines = [
        BillLineInput(
            expense_account_id=l.expense_account_id,
            description=l.description,
            quantity=l.quantity,
            unit_price=l.unit_price,
            tax_rule_code=l.tax_rule_code,
            withholding_tax_rule_code=l.withholding_tax_rule_code,
            item_id=l.item_id,
        )
        for l in payload.lines
    ]

    try:
        bill = update_draft_bill(
            db,
            bill=bill,
            vendor_id=payload.vendor_id,
            bill_number=payload.bill_number,
            bill_date=payload.bill_date,
            due_date=payload.due_date,
            lines=lines,
            memo=payload.memo,
        )
    except PurchasePostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return bill


@router.delete("/purchase-bills/{bill_id}", status_code=204)
def delete_purchase_bill(
    business_id: str,
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    bill = db.get(PurchaseBill, bill_id)
    if not bill or bill.business_id != business_id:
        raise HTTPException(status_code=404, detail="Purchase bill not found.")
    if bill.status != "Draft":
        raise HTTPException(status_code=400, detail="Only draft bills can be deleted. Posted bills are permanent records.")
    db.delete(bill)
    db.commit()
    return None


@router.post("/purchase-bills/{bill_id}/post", response_model=PurchaseBillRead)
def post_purchase_bill(
    business_id: str,
    bill_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    bill = db.get(PurchaseBill, bill_id)
    if not bill or bill.business_id != business_id:
        raise HTTPException(status_code=404, detail="Purchase bill not found.")

    try:
        bill = post_bill(db, bill=bill, created_by_user_id=current_user.id)
    except PurchasePostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return bill
