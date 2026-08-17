"""
Domain-layer tests for the purchase posting service -- mirrors
test_sales_posting.py, with added coverage for withholding tax, which
is the one thing purchases need that sales didn't.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.business import Business, BusinessSettings
from app.models.period import AccountingPeriod, FiscalYear
from app.models.tax_rule import TaxRule
from app.models.vendor import Vendor
from app.services.purchases import BillLineInput, PurchasePostingError, create_draft_bill, post_bill


@pytest.fixture()
def purchase_fixture(db_session):
    business = Business(registered_name="Purchase Test Co")
    db_session.add(business)
    db_session.flush()

    fiscal_year = FiscalYear(
        business_id=business.id, name="FY2026", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31)
    )
    db_session.add(fiscal_year)
    db_session.flush()

    period = AccountingPeriod(
        business_id=business.id,
        fiscal_year_id=fiscal_year.id,
        name="2026-08",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 31),
    )
    db_session.add(period)

    ap = Account(business_id=business.id, code="2000", name="Accounts Payable", account_type="Liability")
    expense = Account(business_id=business.id, code="6000", name="Professional Fees", account_type="Expense")
    input_vat = Account(business_id=business.id, code="1400", name="Input VAT", account_type="Asset")
    wt_payable = Account(
        business_id=business.id, code="2300", name="Withholding Tax Payable", account_type="Liability"
    )
    db_session.add_all([ap, expense, input_vat, wt_payable])
    db_session.flush()

    settings = BusinessSettings(
        business_id=business.id,
        ap_account_id=ap.id,
        input_vat_account_id=input_vat.id,
        withholding_tax_payable_account_id=wt_payable.id,
    )
    db_session.add(settings)

    vendor = Vendor(business_id=business.id, name="ABC Consulting Services")
    db_session.add(vendor)

    db_session.add_all(
        [
            TaxRule(
                business_id=None,
                rule_code="VAT_STANDARD",
                name="Standard VAT",
                tax_type="VAT",
                rate_percent=Decimal("12.0000"),
                effective_from=date(2020, 1, 1),
                status="Active",
            ),
            TaxRule(
                business_id=None,
                rule_code="WT_EWT_PROF_FEES",
                name="EWT - Professional Fees",
                tax_type="Withholding",
                atc_code="WC010",
                rate_percent=Decimal("10.0000"),
                effective_from=date(2020, 1, 1),
                status="Active",
            ),
        ]
    )
    db_session.commit()

    return {
        "business": business,
        "period": period,
        "ap": ap,
        "expense": expense,
        "input_vat": input_vat,
        "wt_payable": wt_payable,
        "vendor": vendor,
    }


def test_draft_bill_computes_vat_and_withholding(db_session, purchase_fixture):
    bill = create_draft_bill(
        db_session,
        business_id=purchase_fixture["business"].id,
        vendor_id=purchase_fixture["vendor"].id,
        bill_number="OR-1001",
        bill_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=purchase_fixture["expense"].id,
                description="Consulting fee",
                quantity=Decimal("1"),
                unit_price=Decimal("1000.00"),
                tax_rule_code="VAT_STANDARD",
                withholding_tax_rule_code="WT_EWT_PROF_FEES",
            )
        ],
    )

    assert bill.status == "Draft"
    assert bill.subtotal == Decimal("1000.00")
    assert bill.input_vat_total == Decimal("120.00")
    assert bill.withholding_tax_total == Decimal("100.00")
    assert bill.grand_total == Decimal("1120.00")
    # Amount actually paid to the vendor is grand total minus what's withheld.
    assert bill.amount_due_to_vendor == Decimal("1020.00")


def test_posting_bill_creates_balanced_entry_with_withholding(db_session, purchase_fixture):
    bill = create_draft_bill(
        db_session,
        business_id=purchase_fixture["business"].id,
        vendor_id=purchase_fixture["vendor"].id,
        bill_number="OR-1002",
        bill_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=purchase_fixture["expense"].id,
                description="Consulting fee",
                quantity=Decimal("1"),
                unit_price=Decimal("1000.00"),
                tax_rule_code="VAT_STANDARD",
                withholding_tax_rule_code="WT_EWT_PROF_FEES",
            )
        ],
    )

    posted = post_bill(db_session, bill=bill)
    assert posted.status == "Posted"
    assert posted.journal_entry_id is not None

    tb = get_trial_balance(db_session, business_id=purchase_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}

    assert by_code["6000"].debit == Decimal("1000.00")  # Expense
    assert by_code["1400"].debit == Decimal("120.00")  # Input VAT
    assert by_code["2000"].credit == Decimal("1020.00")  # AP (net of withholding)
    assert by_code["2300"].credit == Decimal("100.00")  # Withholding Tax Payable

    total_debit = sum((r.debit for r in tb), Decimal("0.00"))
    total_credit = sum((r.credit for r in tb), Decimal("0.00"))
    assert total_debit == total_credit == Decimal("1120.00")


def test_bill_without_withholding_has_ap_equal_to_grand_total(db_session, purchase_fixture):
    bill = create_draft_bill(
        db_session,
        business_id=purchase_fixture["business"].id,
        vendor_id=purchase_fixture["vendor"].id,
        bill_number="OR-1003",
        bill_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=purchase_fixture["expense"].id,
                description="Office supplies",
                quantity=Decimal("1"),
                unit_price=Decimal("500.00"),
                tax_rule_code="VAT_STANDARD",
            )
        ],
    )
    assert bill.withholding_tax_total == Decimal("0.00")
    assert bill.amount_due_to_vendor == bill.grand_total == Decimal("560.00")


def test_cannot_post_bill_twice(db_session, purchase_fixture):
    bill = create_draft_bill(
        db_session,
        business_id=purchase_fixture["business"].id,
        vendor_id=purchase_fixture["vendor"].id,
        bill_number="OR-1004",
        bill_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=purchase_fixture["expense"].id,
                description="Office supplies",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
            )
        ],
    )
    post_bill(db_session, bill=bill)

    with pytest.raises(PurchasePostingError, match="only a Draft bill can be posted"):
        post_bill(db_session, bill=bill)


def test_posting_without_withholding_account_configured_fails_clearly(db_session, purchase_fixture):
    purchase_fixture["business"].settings.withholding_tax_payable_account_id = None
    db_session.commit()

    bill = create_draft_bill(
        db_session,
        business_id=purchase_fixture["business"].id,
        vendor_id=purchase_fixture["vendor"].id,
        bill_number="OR-1005",
        bill_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=purchase_fixture["expense"].id,
                description="Consulting fee",
                quantity=Decimal("1"),
                unit_price=Decimal("1000.00"),
                withholding_tax_rule_code="WT_EWT_PROF_FEES",
            )
        ],
    )

    with pytest.raises(PurchasePostingError, match="Withholding Tax Payable"):
        post_bill(db_session, bill=bill)
