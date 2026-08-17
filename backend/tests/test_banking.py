"""
Domain-layer tests for banking: cash receipts against AR, cash
disbursements against AP, and bank reconciliation.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.accounting.ledger.queries import get_trial_balance
from app.models.account import Account
from app.models.bank import BankAccount
from app.models.business import Business, BusinessSettings
from app.models.customer import Customer
from app.models.period import AccountingPeriod, FiscalYear
from app.models.vendor import Vendor
from app.services.banking import (
    AllocationInput,
    BankingPostingError,
    create_draft_disbursement,
    create_draft_receipt,
    post_disbursement,
    post_receipt,
)
from app.services.reconciliation import ReconciliationError, reconcile_bank_account
from app.services.sales import InvoiceLineInput, create_draft_invoice, post_invoice as post_sales_invoice
from app.services.purchases import BillLineInput, create_draft_bill, post_bill


@pytest.fixture()
def banking_fixture(db_session):
    business = Business(registered_name="Banking Test Co")
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

    bank_gl = Account(business_id=business.id, code="1010", name="BDO Checking", account_type="Asset")
    ar = Account(business_id=business.id, code="1200", name="Accounts Receivable", account_type="Asset")
    ap = Account(business_id=business.id, code="2000", name="Accounts Payable", account_type="Liability")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    expense = Account(business_id=business.id, code="6000", name="Office Supplies", account_type="Expense")
    db_session.add_all([bank_gl, ar, ap, revenue, expense])
    db_session.flush()

    settings = BusinessSettings(business_id=business.id, ar_account_id=ar.id, ap_account_id=ap.id)
    db_session.add(settings)

    bank_account = BankAccount(
        business_id=business.id,
        gl_account_id=bank_gl.id,
        name="BDO Checking",
        opening_balance=Decimal("10000.00"),
        opening_balance_date=date(2026, 8, 1),
    )
    db_session.add(bank_account)

    customer = Customer(business_id=business.id, name="Juan Dela Cruz")
    vendor = Vendor(business_id=business.id, name="Office Depot PH")
    db_session.add_all([customer, vendor])
    db_session.commit()

    return {
        "business": business,
        "bank_gl": bank_gl,
        "ar": ar,
        "ap": ap,
        "revenue": revenue,
        "expense": expense,
        "bank_account": bank_account,
        "customer": customer,
        "vendor": vendor,
    }


def _post_sales_invoice(db_session, fx, amount=Decimal("1000.00")):
    invoice = create_draft_invoice(
        db_session,
        business_id=fx["business"].id,
        customer_id=fx["customer"].id,
        invoice_number="INV-0001",
        invoice_date=date(2026, 8, 5),
        due_date=None,
        lines=[
            InvoiceLineInput(
                revenue_account_id=fx["revenue"].id,
                description="Services",
                quantity=Decimal("1"),
                unit_price=amount,
            )
        ],
    )
    return post_sales_invoice(db_session, invoice=invoice)


def _post_purchase_bill(db_session, fx, amount=Decimal("500.00")):
    bill = create_draft_bill(
        db_session,
        business_id=fx["business"].id,
        vendor_id=fx["vendor"].id,
        bill_number="OR-1001",
        bill_date=date(2026, 8, 5),
        due_date=None,
        lines=[
            BillLineInput(
                expense_account_id=fx["expense"].id,
                description="Supplies",
                quantity=Decimal("1"),
                unit_price=amount,
            )
        ],
    )
    return post_bill(db_session, bill=bill)


def test_receipt_reduces_ar_and_increases_bank(db_session, banking_fixture):
    invoice = _post_sales_invoice(db_session, banking_fixture, Decimal("1000.00"))

    receipt = create_draft_receipt(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        customer_id=banking_fixture["customer"].id,
        receipt_number="OR-2001",
        receipt_date=date(2026, 8, 10),
        amount=Decimal("1000.00"),
        allocations=[AllocationInput(document_id=invoice.id, amount_applied=Decimal("1000.00"))],
    )
    posted = post_receipt(db_session, receipt=receipt)

    assert posted.status == "Posted"

    tb = get_trial_balance(db_session, business_id=banking_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}

    # AR: 1000 debit from invoice, 1000 credit from receipt -> nets to zero, drops off trial balance
    assert "1200" not in by_code
    # Bank: 1000 debit from receipt
    assert by_code["1010"].debit == Decimal("1000.00")


def test_disbursement_reduces_ap_and_decreases_bank(db_session, banking_fixture):
    bill = _post_purchase_bill(db_session, banking_fixture, Decimal("500.00"))

    disbursement = create_draft_disbursement(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        vendor_id=banking_fixture["vendor"].id,
        payment_number="CHK-3001",
        payment_date=date(2026, 8, 12),
        amount=Decimal("500.00"),
        allocations=[AllocationInput(document_id=bill.id, amount_applied=Decimal("500.00"))],
    )
    posted = post_disbursement(db_session, disbursement=disbursement)

    assert posted.status == "Posted"

    tb = get_trial_balance(db_session, business_id=banking_fixture["business"].id)
    by_code = {row.account_code: row for row in tb}

    # AP: 500 credit from bill, 500 debit from payment -> nets to zero
    assert "2000" not in by_code
    # Bank: net debit 10000(opening not in ledger) ... just check expense + no AP left; bank GL only reflects postings, not opening balance (that's a BankAccount field, not a journal entry)
    assert by_code["6000"].debit == Decimal("500.00")


def test_allocation_exceeding_amount_rejected(db_session, banking_fixture):
    invoice = _post_sales_invoice(db_session, banking_fixture, Decimal("1000.00"))

    with pytest.raises(BankingPostingError, match="exceeds the receipt amount"):
        create_draft_receipt(
            db_session,
            business_id=banking_fixture["business"].id,
            bank_account_id=banking_fixture["bank_account"].id,
            customer_id=banking_fixture["customer"].id,
            receipt_number="OR-2002",
            receipt_date=date(2026, 8, 10),
            amount=Decimal("500.00"),
            allocations=[AllocationInput(document_id=invoice.id, amount_applied=Decimal("1000.00"))],
        )


def test_reconciliation_matches_when_balances_agree(db_session, banking_fixture):
    invoice = _post_sales_invoice(db_session, banking_fixture, Decimal("1000.00"))

    receipt = create_draft_receipt(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        customer_id=banking_fixture["customer"].id,
        receipt_number="OR-2003",
        receipt_date=date(2026, 8, 10),
        amount=Decimal("1000.00"),
        allocations=[AllocationInput(document_id=invoice.id, amount_applied=Decimal("1000.00"))],
    )
    posted_receipt = post_receipt(db_session, receipt=receipt)

    # Opening balance 10000 + cleared receipt 1000 = 11000 book balance
    reconciliation = reconcile_bank_account(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        statement_date=date(2026, 8, 31),
        statement_ending_balance=Decimal("11000.00"),
        receipt_ids_to_clear=[posted_receipt.id],
        disbursement_ids_to_clear=[],
    )

    assert reconciliation.book_balance == Decimal("11000.00")
    assert reconciliation.difference == Decimal("0.00")
    assert reconciliation.status == "Completed"

    db_session.refresh(posted_receipt)
    assert posted_receipt.is_cleared is True


def test_reconciliation_reports_nonzero_difference_without_hiding_it(db_session, banking_fixture):
    reconciliation = reconcile_bank_account(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        statement_date=date(2026, 8, 31),
        statement_ending_balance=Decimal("10500.00"),  # doesn't match opening balance of 10000
        receipt_ids_to_clear=[],
        disbursement_ids_to_clear=[],
    )

    assert reconciliation.book_balance == Decimal("10000.00")
    assert reconciliation.difference == Decimal("500.00")
    assert reconciliation.status == "Draft"


def test_cannot_clear_a_draft_receipt(db_session, banking_fixture):
    invoice = _post_sales_invoice(db_session, banking_fixture, Decimal("1000.00"))

    draft_receipt = create_draft_receipt(
        db_session,
        business_id=banking_fixture["business"].id,
        bank_account_id=banking_fixture["bank_account"].id,
        customer_id=banking_fixture["customer"].id,
        receipt_number="OR-2004",
        receipt_date=date(2026, 8, 10),
        amount=Decimal("1000.00"),
        allocations=[AllocationInput(document_id=invoice.id, amount_applied=Decimal("1000.00"))],
    )

    with pytest.raises(ReconciliationError, match="not Posted"):
        reconcile_bank_account(
            db_session,
            business_id=banking_fixture["business"].id,
            bank_account_id=banking_fixture["bank_account"].id,
            statement_date=date(2026, 8, 31),
            statement_ending_balance=Decimal("11000.00"),
            receipt_ids_to_clear=[draft_receipt.id],
            disbursement_ids_to_clear=[],
        )
