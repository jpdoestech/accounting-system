from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class VendorCreate(BaseModel):
    name: str
    tin: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int | None = None
    is_vat_registered: bool = True


class VendorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tin: str | None = None
    address: str | None = None
    email: str | None = None
    phone: str | None = None
    payment_terms_days: int | None = None
    is_vat_registered: bool


class PurchaseBillLineInput(BaseModel):
    expense_account_id: str
    description: str
    quantity: Decimal = Decimal("1.0000")
    unit_price: Decimal
    tax_rule_code: str | None = None
    withholding_tax_rule_code: str | None = None
    item_id: str | None = None


class PurchaseBillCreate(BaseModel):
    vendor_id: str
    bill_number: str
    bill_date: date
    due_date: date | None = None
    memo: str | None = None
    lines: list[PurchaseBillLineInput]


class PurchaseBillLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    expense_account_id: str
    line_number: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rule_code: str | None = None
    withholding_tax_rule_code: str | None = None
    item_id: str | None = None
    line_amount: Decimal
    tax_amount: Decimal
    withholding_tax_amount: Decimal


class PurchaseBillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor_id: str
    bill_number: str
    bill_date: date
    due_date: date | None = None
    memo: str | None = None
    status: str
    journal_entry_id: str | None = None
    subtotal: Decimal
    input_vat_total: Decimal
    withholding_tax_total: Decimal
    grand_total: Decimal
    amount_due_to_vendor: Decimal
    lines: list[PurchaseBillLineRead]
