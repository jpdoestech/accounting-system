"""
Domain-layer tests for Phase 7: books of accounts, VAT summary, and
withholding tax certificate generation -- all read-side aggregations
over data posted by earlier phases.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.bir.books.queries import get_general_journal, get_purchase_book, get_sales_book
from app.bir.books.vat_summary import get_vat_summary
from app.bir.books.withholding import (
    CertificateGenerationError,
    issue_certificate,
    preview_certificate,
)
from app.models.account import Account
from app.models.business import Business, BusinessSettings
from app.models.customer import Customer
from app.models.period import AccountingPeriod, FiscalYear
from app.models.tax_rule import TaxRule
from app.models.vendor import Vendor
from app.services.purchases import BillLineInput, create_draft_bill, post_bill
from app.services.sales import InvoiceLineInput, create_draft_invoice
from app.services.sales import post_invoice as post_sales_invoice


@pytest.fixture()
def bir_fixture(db_session):
    business = Business(registered_name="BIR Test Co")
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
    ap = Account(business_id=business.id, code="2000", name="Accounts Payable", account_type="Liability")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    expense = Account(business_id=business.id, code="6000", name="Professional Fees", account_type="Expense")
    input_vat = Account(business_id=business.id, code="1400", name="Input VAT", account_type="Asset")
    output_vat = Account(business_id=business.id, code="2200", name="Output VAT Payable", account_type="Liability")
    wt_payable = Account(
        business_id=business.id, code="2300", name="Withholding Tax Payable", account_type="Liability"
    )
    db_session.add_all([ar, ap, revenue, expense, input_vat, output_vat, wt_payable])
    db_session.flush()

    settings = BusinessSettings(
        business_id=business.id,
        ar_account_id=ar.id,
        ap_account_id=ap.id,
        output_vat_account_id=output_vat.id,
        input_vat_account_id=input_vat.id,
        withholding_tax_payable_account_id=wt_payable.id,
    )
    db_session.add(settings)

    customer = Customer(business_id=business.id, name="Juan Dela Cruz")
    vendor = Vendor(business_id=business.id, name="ABC Consulting Services")
    db_session.add_all([customer, vendor])

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
        "revenue": revenue,
        "expense": expense,
        "customer": customer,
        "vendor": vendor,
    }


def _post_invoice(db_session, fx, amount, invoice_date):
    invoice = create_draft_invoice(
        db_session,
        business_id=fx["business"].id,
        customer_id=fx["customer"].id,
        invoice_number=f"INV-{invoice_date.isoformat()}",
        invoice_date=invoice_date,
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=fx["revenue"].id,
                description="Services",
                quantity=Decimal("1"),
                unit_price=amount,
                tax_rule_code="VAT_STANDARD",
            )
        ],
    )
    return post_sales_invoice(db_session, invoice=invoice)


def _post_bill(db_session, fx, amount, bill_date, with_withholding=True):
    bill = create_draft_bill(
        db_session,
        business_id=fx["business"].id,
        vendor_id=fx["vendor"].id,
        bill_number=f"OR-{bill_date.isoformat()}",
        bill_date=bill_date,
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=fx["expense"].id,
                description="Consulting",
                quantity=Decimal("1"),
                unit_price=amount,
                tax_rule_code="VAT_STANDARD",
                withholding_tax_rule_code="WT_EWT_PROF_FEES" if with_withholding else None,
            )
        ],
    )
    return post_bill(db_session, bill=bill)


def test_general_journal_includes_all_posted_entries_in_order(db_session, bir_fixture):
    _post_invoice(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5))
    _post_bill(db_session, bir_fixture, Decimal("500.00"), date(2026, 8, 10))

    journal = get_general_journal(db_session, business_id=bir_fixture["business"].id)

    assert len(journal) == 2
    assert journal[0].entry_date == date(2026, 8, 5)
    assert journal[0].source == "Sales Invoice"
    assert journal[1].entry_date == date(2026, 8, 10)
    assert journal[1].source == "Purchase Bill"


def test_sales_and_purchase_books_only_include_posted_documents(db_session, bir_fixture):
    _post_invoice(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5))
    _post_bill(db_session, bir_fixture, Decimal("500.00"), date(2026, 8, 10))

    # A draft invoice should NOT appear in the sales book.
    create_draft_invoice(
        db_session,
        business_id=bir_fixture["business"].id,
        customer_id=bir_fixture["customer"].id,
        invoice_number="INV-DRAFT",
        invoice_date=date(2026, 8, 20),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=bir_fixture["revenue"].id,
                description="Unposted",
                quantity=Decimal("1"),
                unit_price=Decimal("999.00"),
            )
        ],
    )

    sales_book = get_sales_book(db_session, business_id=bir_fixture["business"].id)
    purchase_book = get_purchase_book(db_session, business_id=bir_fixture["business"].id)

    assert len(sales_book) == 1
    assert sales_book[0].status == "Posted"
    assert len(purchase_book) == 1


def test_vat_summary_computes_net_payable(db_session, bir_fixture):
    _post_invoice(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5))  # output VAT 120
    _post_bill(db_session, bir_fixture, Decimal("500.00"), date(2026, 8, 10))  # input VAT 60

    summary = get_vat_summary(
        db_session, business_id=bir_fixture["business"].id, date_from=date(2026, 8, 1), date_to=date(2026, 8, 31)
    )

    assert summary.output_vat == Decimal("120.00")
    assert summary.input_vat == Decimal("60.00")
    assert summary.net_vat_payable == Decimal("60.00")


def test_withholding_certificate_aggregates_by_atc(db_session, bir_fixture):
    _post_bill(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5))  # WT 100
    _post_bill(db_session, bir_fixture, Decimal("2000.00"), date(2026, 8, 15))  # WT 200

    preview = preview_certificate(
        db_session,
        business_id=bir_fixture["business"].id,
        vendor_id=bir_fixture["vendor"].id,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
    )

    assert preview.total_income_payment == Decimal("3000.00")
    assert preview.total_tax_withheld == Decimal("300.00")
    assert len(preview.breakdown) == 1
    assert preview.breakdown[0].atc_code == "WC010"
    assert preview.breakdown[0].tax_withheld == Decimal("300.00")


def test_issuing_certificate_persists_it(db_session, bir_fixture):
    _post_bill(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5))

    certificate = issue_certificate(
        db_session,
        business_id=bir_fixture["business"].id,
        vendor_id=bir_fixture["vendor"].id,
        certificate_number="2307-2026-08-0001",
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
    )

    assert certificate.status == "Issued"
    assert certificate.total_tax_withheld == Decimal("100.00")


def test_cannot_issue_certificate_with_no_withholding(db_session, bir_fixture):
    _post_bill(db_session, bir_fixture, Decimal("1000.00"), date(2026, 8, 5), with_withholding=False)

    with pytest.raises(CertificateGenerationError, match="nothing to certify"):
        issue_certificate(
            db_session,
            business_id=bir_fixture["business"].id,
            vendor_id=bir_fixture["vendor"].id,
            certificate_number="2307-2026-08-0002",
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
        )
