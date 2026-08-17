"""
VAT summary.

Aggregates Output VAT (from posted sales invoice lines) and Input VAT
(from posted purchase bill lines) for a period into the figures a BIR
VAT return needs: total output VAT, total input VAT, and the net
VAT payable (or excess input VAT carried over, if negative). Purely
a read-side aggregation over data Phases 4 and 5 already posted --
no new tax calculation happens here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.purchase import PurchaseBill
from app.models.sales import SalesInvoice
from app.utils.money import zero


@dataclass
class VatSummary:
    period_start: date | None
    period_end: date | None
    output_vat: Decimal
    input_vat: Decimal
    net_vat_payable: Decimal  # positive = payable to BIR; negative = excess input VAT carried over
    taxable_sales: Decimal
    taxable_purchases: Decimal


def get_vat_summary(
    db: Session, *, business_id: str, date_from: date | None = None, date_to: date | None = None
) -> VatSummary:
    sales_query = db.query(SalesInvoice).filter(
        SalesInvoice.business_id == business_id, SalesInvoice.status == "Posted"
    )
    if date_from is not None:
        sales_query = sales_query.filter(SalesInvoice.invoice_date >= date_from)
    if date_to is not None:
        sales_query = sales_query.filter(SalesInvoice.invoice_date <= date_to)

    purchase_query = db.query(PurchaseBill).filter(
        PurchaseBill.business_id == business_id, PurchaseBill.status == "Posted"
    )
    if date_from is not None:
        purchase_query = purchase_query.filter(PurchaseBill.bill_date >= date_from)
    if date_to is not None:
        purchase_query = purchase_query.filter(PurchaseBill.bill_date <= date_to)

    output_vat = zero()
    taxable_sales = zero()
    for invoice in sales_query.all():
        output_vat += invoice.tax_total
        taxable_sales += invoice.subtotal

    input_vat = zero()
    taxable_purchases = zero()
    for bill in purchase_query.all():
        input_vat += bill.input_vat_total
        taxable_purchases += bill.subtotal

    return VatSummary(
        period_start=date_from,
        period_end=date_to,
        output_vat=output_vat,
        input_vat=input_vat,
        net_vat_payable=output_vat - input_vat,
        taxable_sales=taxable_sales,
        taxable_purchases=taxable_purchases,
    )
