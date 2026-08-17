"""
Domain-layer tests for Phase 10: Balance Sheet, Income Statement, and
budget variance -- all pure read-side aggregations over data posted
by earlier phases.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.models.account import Account
from app.models.budget import Budget, BudgetLine
from app.models.business import Business, BusinessSettings
from app.models.customer import Customer
from app.models.period import AccountingPeriod, FiscalYear
from app.reports.financial.budget_variance import get_budget_variance
from app.reports.financial.statements import get_balance_sheet, get_income_statement
from app.services.sales import InvoiceLineInput, create_draft_invoice
from app.services.sales import post_invoice as post_sales_invoice


@pytest.fixture()
def statements_fixture(db_session):
    business = Business(registered_name="Statements Test Co")
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
    db_session.add(
        AccountingPeriod(
            business_id=business.id,
            fiscal_year_id=fiscal_year.id,
            name="2026-07",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
    )

    cash = Account(business_id=business.id, code="1000", name="Cash", account_type="Asset")
    ar = Account(business_id=business.id, code="1200", name="Accounts Receivable", account_type="Asset")
    equity = Account(business_id=business.id, code="3000", name="Owner's Capital", account_type="Equity")
    revenue = Account(business_id=business.id, code="4000", name="Sales Revenue", account_type="Revenue")
    expense = Account(business_id=business.id, code="6000", name="Rent Expense", account_type="Expense")
    db_session.add_all([cash, ar, equity, revenue, expense])
    db_session.flush()

    settings = BusinessSettings(business_id=business.id, ar_account_id=ar.id)
    db_session.add(settings)

    customer = Customer(business_id=business.id, name="Juan Dela Cruz")
    db_session.add(customer)
    db_session.commit()

    return {
        "business": business,
        "fiscal_year": fiscal_year,
        "cash": cash,
        "ar": ar,
        "equity": equity,
        "revenue": revenue,
        "expense": expense,
        "customer": customer,
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
            )
        ],
    )
    return post_sales_invoice(db_session, invoice=invoice)


def _post_manual_entry(db_session, fx, entry_date, debit_account, credit_account, amount):
    from app.accounting.engine.posting import LineInput, post_journal_entry

    return post_journal_entry(
        db_session,
        business_id=fx["business"].id,
        entry_date=entry_date,
        lines=[
            LineInput(account_id=debit_account.id, debit=amount),
            LineInput(account_id=credit_account.id, credit=amount),
        ],
        memo="Test entry",
    )


def test_balance_sheet_balances_with_net_income_folded_into_equity(db_session, statements_fixture):
    fx = statements_fixture

    # Owner contributes 5000 cash.
    _post_manual_entry(db_session, fx, date(2026, 8, 1), fx["cash"], fx["equity"], Decimal("5000.00"))
    # A 1000 sale on credit (AR).
    _post_invoice(db_session, fx, Decimal("1000.00"), date(2026, 8, 5))

    bs = get_balance_sheet(db_session, business_id=fx["business"].id, as_of_date=date(2026, 8, 31))

    assert bs.net_income_to_date == Decimal("1000.00")  # revenue only, no expense posted yet
    assert bs.total_assets == Decimal("6000.00")  # 5000 cash + 1000 AR
    assert bs.total_equity == Decimal("6000.00")  # 5000 capital + 1000 net income
    assert bs.total_liabilities_and_equity == Decimal("6000.00")
    assert bs.is_balanced is True


def test_income_statement_only_includes_period_activity(db_session, statements_fixture):
    fx = statements_fixture

    _post_invoice(db_session, fx, Decimal("1000.00"), date(2026, 7, 15))  # prior period
    _post_invoice(db_session, fx, Decimal("500.00"), date(2026, 8, 5))  # current period
    _post_manual_entry(db_session, fx, date(2026, 8, 10), fx["expense"], fx["cash"], Decimal("200.00"))

    income_statement = get_income_statement(
        db_session, business_id=fx["business"].id, period_start=date(2026, 8, 1), period_end=date(2026, 8, 31)
    )

    assert income_statement.total_revenue == Decimal("500.00")  # only August's invoice
    assert income_statement.total_expenses == Decimal("200.00")
    assert income_statement.net_income == Decimal("300.00")


def test_budget_variance_compares_actual_to_budgeted(db_session, statements_fixture):
    fx = statements_fixture

    _post_invoice(db_session, fx, Decimal("800.00"), date(2026, 8, 5))

    budget = Budget(business_id=fx["business"].id, fiscal_year_id=fx["fiscal_year"].id, name="FY2026 Budget")
    db_session.add(budget)
    db_session.flush()
    db_session.add(BudgetLine(budget_id=budget.id, account_id=fx["revenue"].id, budgeted_amount=Decimal("1000.00")))
    db_session.commit()

    report = get_budget_variance(db_session, business_id=fx["business"].id, budget_id=budget.id)

    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.budgeted_amount == Decimal("1000.00")
    assert row.actual_amount == Decimal("800.00")
    assert row.variance == Decimal("-200.00")  # under budget by 200
    assert row.variance_percent == Decimal("-20.00")
