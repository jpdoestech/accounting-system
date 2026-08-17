"""
Tax calculation.

Pure calculation against an already-resolved TaxRule (see rules.py) --
this module never decides which rule applies and never posts journal
entries. Callers combine this with app.accounting.engine.posting to
turn a calculated tax amount into an actual journal line.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.tax.engine.rules import find_effective_rule
from app.utils.money import to_money


@dataclass
class TaxCalculationResult:
    rule_code: str
    rule_name: str
    tax_type: str
    rate_percent: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    rule_id: str
    atc_code: str | None = None


def calculate_tax(
    db: Session,
    *,
    business_id: str,
    rule_code: str,
    taxable_amount: Decimal | float | str,
    as_of_date: date,
) -> TaxCalculationResult:
    """
    Calculate tax on `taxable_amount` using the rule in force on
    `as_of_date`. Raises TaxRuleNotFoundError (from rules.py) if no
    rule covers that date -- callers should surface this as a clear
    error rather than silently falling back to a guessed rate.
    """
    rule = find_effective_rule(db, business_id=business_id, rule_code=rule_code, as_of_date=as_of_date)

    amount = to_money(taxable_amount)
    tax_amount = to_money(amount * rule.rate_percent / Decimal("100"))

    return TaxCalculationResult(
        rule_code=rule.rule_code,
        rule_name=rule.name,
        tax_type=rule.tax_type,
        rate_percent=rule.rate_percent,
        taxable_amount=amount,
        tax_amount=tax_amount,
        rule_id=rule.id,
        atc_code=rule.atc_code,
    )


def calculate_vat_exclusive_breakdown(
    db: Session,
    *,
    business_id: str,
    rule_code: str,
    gross_amount: Decimal | float | str,
    as_of_date: date,
) -> dict[str, Decimal]:
    """
    Given a VAT-inclusive gross amount, back out the VAT-exclusive
    (net) amount and the VAT component, using the rate in force on
    as_of_date. Common need for PH VAT-inclusive pricing.
    """
    rule = find_effective_rule(db, business_id=business_id, rule_code=rule_code, as_of_date=as_of_date)
    gross = to_money(gross_amount)

    divisor = Decimal("1") + (rule.rate_percent / Decimal("100"))
    net_amount = to_money(gross / divisor)
    vat_amount = to_money(gross - net_amount)

    return {
        "gross_amount": gross,
        "net_amount": net_amount,
        "vat_amount": vat_amount,
        "rate_percent": rule.rate_percent,
    }
