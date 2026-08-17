from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class BankAccountCreate(BaseModel):
    name: str
    gl_account_id: str
    bank_name: str | None = None
    account_number: str | None = None
    currency_code: str = "PHP"
    opening_balance: Decimal = Decimal("0.00")
    opening_balance_date: date | None = None


class BankAccountUpdate(BaseModel):
    name: str | None = None
    bank_name: str | None = None
    account_number: str | None = None
    currency_code: str | None = None


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    gl_account_id: str
    bank_name: str | None = None
    account_number: str | None = None
    currency_code: str
    opening_balance: Decimal
    opening_balance_date: date | None = None
    is_active: bool


class AllocationInputSchema(BaseModel):
    document_id: str
    amount_applied: Decimal


class CashReceiptCreate(BaseModel):
    bank_account_id: str
    customer_id: str
    receipt_number: str
    receipt_date: date
    amount: Decimal
    memo: str | None = None
    allocations: list[AllocationInputSchema] = []


class CashReceiptAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sales_invoice_id: str
    amount_applied: Decimal


class CashReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bank_account_id: str
    customer_id: str
    receipt_number: str
    receipt_date: date
    amount: Decimal
    memo: str | None = None
    status: str
    journal_entry_id: str | None = None
    is_cleared: bool
    cleared_date: date | None = None
    allocations: list[CashReceiptAllocationRead]


class CashDisbursementCreate(BaseModel):
    bank_account_id: str
    vendor_id: str
    payment_number: str
    payment_date: date
    amount: Decimal
    memo: str | None = None
    allocations: list[AllocationInputSchema] = []


class CashDisbursementAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    purchase_bill_id: str
    amount_applied: Decimal


class CashDisbursementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bank_account_id: str
    vendor_id: str
    payment_number: str
    payment_date: date
    amount: Decimal
    memo: str | None = None
    status: str
    journal_entry_id: str | None = None
    is_cleared: bool
    cleared_date: date | None = None
    allocations: list[CashDisbursementAllocationRead]


class BankReconciliationRequest(BaseModel):
    statement_date: date
    statement_ending_balance: Decimal
    receipt_ids_to_clear: list[str] = []
    disbursement_ids_to_clear: list[str] = []


class BankReconciliationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    bank_account_id: str
    statement_date: date
    statement_ending_balance: Decimal
    book_balance: Decimal
    difference: Decimal
    status: str
