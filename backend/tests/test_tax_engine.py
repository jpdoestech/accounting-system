"""
Unit tests for the tax engine -- exercised directly against the
domain layer, mirroring the posting engine test style.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.models.business import Business
from app.models.tax_rule import TaxRule
from app.tax.engine.calculator import calculate_tax, calculate_vat_exclusive_breakdown
from app.tax.engine.rules import TaxRuleNotFoundError, find_effective_rule


@pytest.fixture()
def business(db_session):
    b = Business(registered_name="Tax Test Co")
    db_session.add(b)
    db_session.commit()
    return b


def test_rule_versioning_uses_rate_in_force_at_transaction_date(db_session, business):
    # Old rate 10% until 2023-12-31, new rate 12% from 2024-01-01.
    db_session.add_all(
        [
            TaxRule(
                business_id=None,
                rule_code="VAT_STANDARD",
                name="Standard VAT (old)",
                tax_type="VAT",
                rate_percent=Decimal("10.0000"),
                effective_from=date(2020, 1, 1),
                effective_to=date(2023, 12, 31),
                status="Active",
            ),
            TaxRule(
                business_id=None,
                rule_code="VAT_STANDARD",
                name="Standard VAT",
                tax_type="VAT",
                rate_percent=Decimal("12.0000"),
                effective_from=date(2024, 1, 1),
                effective_to=None,
                status="Active",
            ),
        ]
    )
    db_session.commit()

    old_result = calculate_tax(
        db_session,
        business_id=business.id,
        rule_code="VAT_STANDARD",
        taxable_amount=Decimal("1000.00"),
        as_of_date=date(2023, 6, 1),
    )
    assert old_result.rate_percent == Decimal("10.0000")
    assert old_result.tax_amount == Decimal("100.00")

    new_result = calculate_tax(
        db_session,
        business_id=business.id,
        rule_code="VAT_STANDARD",
        taxable_amount=Decimal("1000.00"),
        as_of_date=date(2026, 8, 11),
    )
    assert new_result.rate_percent == Decimal("12.0000")
    assert new_result.tax_amount == Decimal("120.00")


def test_business_specific_rule_overrides_global_default(db_session, business):
    db_session.add_all(
        [
            TaxRule(
                business_id=None,
                rule_code="WT_EWT_PROF_FEES",
                name="EWT - Professional Fees (global default)",
                tax_type="Withholding",
                atc_code="WC010",
                rate_percent=Decimal("10.0000"),
                effective_from=date(2020, 1, 1),
                status="Active",
            ),
            TaxRule(
                business_id=business.id,
                rule_code="WT_EWT_PROF_FEES",
                name="EWT - Professional Fees (this business, negotiated rate)",
                tax_type="Withholding",
                atc_code="WC010",
                rate_percent=Decimal("15.0000"),
                effective_from=date(2020, 1, 1),
                status="Active",
            ),
        ]
    )
    db_session.commit()

    result = calculate_tax(
        db_session,
        business_id=business.id,
        rule_code="WT_EWT_PROF_FEES",
        taxable_amount=Decimal("2000.00"),
        as_of_date=date(2026, 1, 1),
    )
    assert result.rate_percent == Decimal("15.0000")
    assert result.tax_amount == Decimal("300.00")


def test_missing_rule_raises_clear_error(db_session, business):
    with pytest.raises(TaxRuleNotFoundError, match="No active tax rule"):
        find_effective_rule(
            db_session, business_id=business.id, rule_code="NONEXISTENT_RULE", as_of_date=date(2026, 1, 1)
        )


def test_retired_rule_is_not_used(db_session, business):
    db_session.add(
        TaxRule(
            business_id=business.id,
            rule_code="VAT_STANDARD",
            name="Standard VAT",
            tax_type="VAT",
            rate_percent=Decimal("12.0000"),
            effective_from=date(2020, 1, 1),
            status="Retired",
        )
    )
    db_session.commit()

    with pytest.raises(TaxRuleNotFoundError):
        find_effective_rule(
            db_session, business_id=business.id, rule_code="VAT_STANDARD", as_of_date=date(2026, 1, 1)
        )


def test_vat_inclusive_breakdown(db_session, business):
    db_session.add(
        TaxRule(
            business_id=None,
            rule_code="VAT_STANDARD",
            name="Standard VAT",
            tax_type="VAT",
            rate_percent=Decimal("12.0000"),
            effective_from=date(2020, 1, 1),
            status="Active",
        )
    )
    db_session.commit()

    breakdown = calculate_vat_exclusive_breakdown(
        db_session,
        business_id=business.id,
        rule_code="VAT_STANDARD",
        gross_amount=Decimal("1120.00"),
        as_of_date=date(2026, 1, 1),
    )
    assert breakdown["net_amount"] == Decimal("1000.00")
    assert breakdown["vat_amount"] == Decimal("120.00")
