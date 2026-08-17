from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    name: str
    tin: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    tin: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tin: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int | None = None


class SalesInvoiceLineInput(BaseModel):
    revenue_account_id: str
    description: str
    quantity: Decimal = Decimal("1.0000")
    unit_price: Decimal
    tax_rule_code: str | None = None
    item_id: str | None = None


class SalesInvoiceCreate(BaseModel):
    customer_id: str
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    memo: str | None = None
    lines: list[SalesInvoiceLineInput]


class SalesInvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    revenue_account_id: str
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rule_code: str | None = None
    item_id: str | None = None
    line_amount: Decimal
    tax_amount: Decimal


class SalesInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    memo: str | None = None
    status: str
    journal_entry_id: str | None = None
    subtotal: Decimal
    tax_total: Decimal
    grand_total: Decimal
    lines: list[SalesInvoiceLineRead]
