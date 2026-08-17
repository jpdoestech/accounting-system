"""
Domain-layer tests for the sales posting service -- confirms it
correctly composes the accounting engine (Phase 2) and tax engine
(Phase 3) without reimplementing either.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.business import Business, BusinessSettings
from app.models.customer import Customer
from app.models.period import AccountingPeriod, FiscalYear
from app.models.tax_rule import TaxRule
from app.services.sales import InvoiceLineInput, SalesPostingError, create_draft_invoice, post_invoice


@pytest.fixture()
def sales_fixture(db_session):
    business = Business(registered_name="Sales Test Co")
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

    ar = Account(business_id=business.id, code="1200", name="Accounts Receivable", account_type="Asset")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    output_vat = Account(business_id=business.id, code="2200", name="Output VAT Payable", account_type="Liability")
    db_session.add_all([ar, revenue, output_vat])
    db_session.flush()

    settings = BusinessSettings(
        business_id=business.id, ar_account_id=ar.id, output_vat_account_id=output_vat.id
    )
    db_session.add(settings)

    customer = Customer(business_id=business.id, name="Juan Dela Cruz")
    db_session.add(customer)

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

    return {
        "business": business,
        "period": period,
        "ar": ar,
        "revenue": revenue,
        "output_vat": output_vat,
        "customer": customer,
    }


def test_draft_invoice_computes_tax_and_totals(db_session, sales_fixture):
    invoice = create_draft_invoice(
        db_session,
        business_id=sales_fixture["business"].id,
        customer_id=sales_fixture["customer"].id,
        invoice_number="INV-0001",
        invoice_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=sales_fixture["revenue"].id,
                description="Consulting services",
                quantity=Decimal("1"),
                unit_price=Decimal("1000.00"),
                tax_rule_code="VAT_STANDARD",
            )
        ],
    )

    assert invoice.status == "Draft"
    assert invoice.subtotal == Decimal("1000.00")
    assert invoice.tax_total == Decimal("120.00")
    assert invoice.grand_total == Decimal("1120.00")


def test_posting_invoice_creates_balanced_journal_entry(db_session, sales_fixture):
    invoice = create_draft_invoice(
        db_session,
        business_id=sales_fixture["business"].id,
        customer_id=sales_fixture["customer"].id,
        invoice_number="INV-0002",
        invoice_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=sales_fixture["revenue"].id,
                description="Goods sold",
                quantity=Decimal("2"),
                unit_price=Decimal("500.00"),
                tax_rule_code="VAT_STANDARD",
            )
        ],
    )

    posted = post_invoice(db_session, invoice=invoice)

    assert posted.status == "Posted"
    assert posted.journal_entry_id is not None

    tb = get_trial_balance(db_session, business_id=sales_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}

    assert by_code["1200"].debit == Decimal("1120.00")  # AR
    assert by_code["4000"].credit == Decimal("1000.00")  # Revenue
    assert by_code["2200"].credit == Decimal("120.00")  # Output VAT

    total_debit = sum((r.debit for r in tb), Decimal("0.00"))
    total_credit = sum((r.credit for r in tb), Decimal("0.00"))
    assert total_debit == total_credit == Decimal("1120.00")


def test_cannot_post_the_same_invoice_twice(db_session, sales_fixture):
    invoice = create_draft_invoice(
        db_session,
        business_id=sales_fixture["business"].id,
        customer_id=sales_fixture["customer"].id,
        invoice_number="INV-0003",
        invoice_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=sales_fixture["revenue"].id,
                description="Goods sold",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
            )
        ],
    )
    post_invoice(db_session, invoice=invoice)

    with pytest.raises(SalesPostingError, match="only a Draft invoice can be posted"):
        post_invoice(db_session, invoice=invoice)


def test_posting_without_ar_account_configured_fails_clearly(db_session, sales_fixture):
    sales_fixture["business"].settings.ar_account_id = None
    db_session.commit()

    invoice = create_draft_invoice(
        db_session,
        business_id=sales_fixture["business"].id,
        customer_id=sales_fixture["customer"].id,
        invoice_number="INV-0004",
        invoice_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=sales_fixture["revenue"].id,
                description="Goods sold",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
            )
        ],
    )

    with pytest.raises(SalesPostingError, match="Accounts Receivable control account"):
        post_invoice(db_session, invoice=invoice)


def test_invoice_with_no_tax_rule_has_zero_tax(db_session, sales_fixture):
    invoice = create_draft_invoice(
        db_session,
        business_id=sales_fixture["business"].id,
        customer_id=sales_fixture["customer"].id,
        invoice_number="INV-0005",
        invoice_date=date(2026, 8, 11),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=sales_fixture["revenue"].id,
                description="Zero-rated export sale",
                quantity=Decimal("1"),
                unit_price=Decimal("500.00"),
                tax_rule_code=None,
            )
        ],
    )
    assert invoice.tax_total == Decimal("0.00")
    assert invoice.grand_total == Decimal("500.00")
