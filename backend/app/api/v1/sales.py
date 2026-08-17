"""
Sales API endpoints: customers and sales invoices.

Invoice creation builds a Draft (via app.services.sales.create_draft_invoice)
and posting is a separate explicit step (via post_invoice) -- this
mirrors how a real invoice workflow works (review before it hits the
books) and keeps this router from ever constructing a JournalEntry
itself.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business
from app.models.customer import Customer
from app.models.sales import SalesInvoice
from app.models.user import User, UserBusinessRole
from app.schemas.sales import (
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    SalesInvoiceCreate,
    SalesInvoiceRead,
)
from app.services.sales import InvoiceLineInput, SalesPostingError, create_draft_invoice, post_invoice

router = APIRouter(prefix="/businesses/{business_id}", tags=["sales"])


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


# --------------------------------------------------------------- customers

@router.post("/customers", response_model=CustomerRead, status_code=201)
def create_customer(
    business_id: str,
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    customer = Customer(business_id=business_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return db.query(Customer).filter(Customer.business_id == business_id).order_by(Customer.name).all()


def _get_customer_or_404(business_id: str, customer_id: str, db: Session) -> Customer:
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.business_id == business_id)
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.put("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    business_id: str,
    customer_id: str,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    customer = _get_customer_or_404(business_id, customer_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}", status_code=204)
def delete_customer(
    business_id: str,
    customer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    customer = _get_customer_or_404(business_id, customer_id, db)
    db.delete(customer)
    db.commit()
    return None


# ---------------------------------------------------------- sales invoices

@router.post("/sales-invoices", response_model=SalesInvoiceRead, status_code=201)
def create_sales_invoice(
    business_id: str,
    payload: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)

    customer = db.get(Customer, payload.customer_id)
    if not customer or customer.business_id != business_id:
        raise HTTPException(status_code=400, detail="Customer not found for this business.")

    lines = [
        InvoiceLineInput(
            revenue_account_id=l.revenue_account_id,
            description=l.description,
            quantity=l.quantity,
            unit_price=l.unit_price,
            tax_rule_code=l.tax_rule_code,
            item_id=l.item_id,
        )
        for l in payload.lines
    ]

    try:
        invoice = create_draft_invoice(
            db,
            business_id=business_id,
            customer_id=payload.customer_id,
            invoice_number=payload.invoice_number,
            invoice_date=payload.invoice_date,
            due_date=payload.due_date,
            lines=lines,
            memo=payload.memo,
        )
    except SalesPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return invoice


@router.get("/sales-invoices", response_model=list[SalesInvoiceRead])
def list_sales_invoices(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(SalesInvoice)
        .filter(SalesInvoice.business_id == business_id)
        .order_by(SalesInvoice.invoice_date.desc())
        .all()
    )


@router.get("/sales-invoices/{invoice_id}", response_model=SalesInvoiceRead)
def get_sales_invoice(
    business_id: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    invoice = db.get(SalesInvoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Sales invoice not found.")
    return invoice


@router.post("/sales-invoices/{invoice_id}/post", response_model=SalesInvoiceRead)
def post_sales_invoice(
    business_id: str,
    invoice_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    invoice = db.get(SalesInvoice, invoice_id)
    if not invoice or invoice.business_id != business_id:
        raise HTTPException(status_code=404, detail="Sales invoice not found.")

    try:
        invoice = post_invoice(db, invoice=invoice, created_by_user_id=current_user.id)
    except SalesPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return invoice
