"""
BIR Form 2307 -- Certificate of Creditable Tax Withheld at Source.

Aggregates the withholding tax already recorded per purchase bill
line (Phase 5: PurchaseBillLine.withholding_tax_amount) for one
vendor across a period, groups it by ATC (Alphanumeric Tax Code, from
the TaxRule the line used), and persists the result as a
WithholdingTaxCertificate. This module never calculates withholding
tax itself -- it only summarizes what the tax engine already
calculated and the purchases module already posted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.purchase import PurchaseBill, PurchaseBillLine
from app.models.tax_rule import TaxRule
from app.models.withholding_certificate import WithholdingTaxCertificate
from app.utils.money import to_money, zero


class CertificateGenerationError(Exception):
    """Raised when a withholding tax certificate cannot be generated."""


@dataclass
class AtcBreakdownRow:
    atc_code: str
    income_payment: Decimal
    tax_withheld: Decimal


@dataclass
class CertificatePreview:
    vendor_id: str
    period_start: date
    period_end: date
    total_income_payment: Decimal
    total_tax_withheld: Decimal
    breakdown: list[AtcBreakdownRow] = field(default_factory=list)


def preview_certificate(
    db: Session, *, business_id: str, vendor_id: str, period_start: date, period_end: date
) -> CertificatePreview:
    """
    Computes what a certificate for this vendor/period would contain,
    without persisting anything -- lets a caller review before issuing.
    """
    lines = (
        db.query(PurchaseBillLine)
        .join(PurchaseBill, PurchaseBillLine.bill_id == PurchaseBill.id)
        .filter(
            PurchaseBill.business_id == business_id,
            PurchaseBill.vendor_id == vendor_id,
            PurchaseBill.status == "Posted",
            PurchaseBill.bill_date >= period_start,
            PurchaseBill.bill_date <= period_end,
            PurchaseBillLine.withholding_tax_amount > 0,
        )
        .all()
    )

    by_atc: dict[str, AtcBreakdownRow] = {}
    for line in lines:
        rule = (
            db.query(TaxRule).filter(TaxRule.rule_code == line.withholding_tax_rule_code).first()
        )
        atc = rule.atc_code if rule and rule.atc_code else (line.withholding_tax_rule_code or "UNSPECIFIED")

        if atc not in by_atc:
            by_atc[atc] = AtcBreakdownRow(atc_code=atc, income_payment=zero(), tax_withheld=zero())
        by_atc[atc].income_payment += line.line_amount
        by_atc[atc].tax_withheld += line.withholding_tax_amount

    breakdown = sorted(by_atc.values(), key=lambda r: r.atc_code)
    total_income_payment = sum((r.income_payment for r in breakdown), zero())
    total_tax_withheld = sum((r.tax_withheld for r in breakdown), zero())

    return CertificatePreview(
        vendor_id=vendor_id,
        period_start=period_start,
        period_end=period_end,
        total_income_payment=to_money(total_income_payment),
        total_tax_withheld=to_money(total_tax_withheld),
        breakdown=breakdown,
    )


def issue_certificate(
    db: Session,
    *,
    business_id: str,
    vendor_id: str,
    certificate_number: str,
    period_start: date,
    period_end: date,
) -> WithholdingTaxCertificate:
    """
    Generates and persists a certificate for this vendor/period.
    Raises CertificateGenerationError if there's nothing to certify
    (no withholding tax was recorded for this vendor in this period) --
    issuing an empty 2307 would be a data-quality error, not a valid
    document.
    """
    preview = preview_certificate(
        db, business_id=business_id, vendor_id=vendor_id, period_start=period_start, period_end=period_end
    )
    if preview.total_tax_withheld <= 0:
        raise CertificateGenerationError(
            "No withholding tax was recorded for this vendor in this period; nothing to certify."
        )

    certificate = WithholdingTaxCertificate(
        business_id=business_id,
        vendor_id=vendor_id,
        certificate_number=certificate_number,
        period_start=period_start,
        period_end=period_end,
        total_income_payment=preview.total_income_payment,
        total_tax_withheld=preview.total_tax_withheld,
        status="Issued",
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate
