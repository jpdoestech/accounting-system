from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.purchases import PurchaseBillRead
from app.schemas.sales import SalesInvoiceRead


class GeneralJournalLineRead(BaseModel):
    account_id: str
    description: str | None = None
    debit: str
    credit: str


class GeneralJournalEntryRead(BaseModel):
    entry_date: date
    reference: str | None = None
    memo: str | None = None
    source: str
    status: str
    lines: list[GeneralJournalLineRead]


class CashReceiptBookRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    receipt_number: str
    receipt_date: date
    customer_id: str
    amount: Decimal
    status: str


class CashDisbursementBookRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_number: str
    payment_date: date
    vendor_id: str
    amount: Decimal
    status: str


class VatSummaryRead(BaseModel):
    period_start: date | None = None
    period_end: date | None = None
    output_vat: Decimal
    input_vat: Decimal
    net_vat_payable: Decimal
    taxable_sales: Decimal
    taxable_purchases: Decimal


class AtcBreakdownRowRead(BaseModel):
    atc_code: str
    income_payment: Decimal
    tax_withheld: Decimal


class CertificatePreviewRead(BaseModel):
    vendor_id: str
    period_start: date
    period_end: date
    total_income_payment: Decimal
    total_tax_withheld: Decimal
    breakdown: list[AtcBreakdownRowRead]


class CertificateIssueRequest(BaseModel):
    vendor_id: str
    certificate_number: str
    period_start: date
    period_end: date


class WithholdingTaxCertificateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor_id: str
    certificate_number: str
    period_start: date
    period_end: date
    total_income_payment: Decimal
    total_tax_withheld: Decimal
    status: str
