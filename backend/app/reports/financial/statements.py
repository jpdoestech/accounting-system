"""
Financial statements: Balance Sheet and Income Statement.

Both are pure read-side reports built entirely from the trial balance
/ period activity the accounting engine has been producing since
Phase 2 -- no new posting logic anywhere in this module.

Because this system has no period-close step (revenue/expense
accounts are never zeroed out and swept into Retained Earnings), an
"as of date" Balance Sheet must explicitly include cumulative net
income as part of Equity for Assets to equal Liabilities + Equity --
see the docstring on get_balance_sheet for the reasoning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.ledger.queries import get_period_activity, get_trial_balance
from app.utils.money import to_money, zero

# Trial balance rows are debit/credit; these helpers translate a row's
# balance into a signed "natural" amount for the account's type, so
# a business/report reader sees "1500.00" for an asset with a debit
# balance rather than having to know which column means positive.
ASSET_LIKE = ("Asset", "Cost of Sales", "Expense", "Other Expense")
CREDIT_LIKE = ("Liability", "Equity", "Revenue", "Other Income")


def _natural_amount(row) -> Decimal:
    if row.account_type in ASSET_LIKE:
        return row.debit - row.credit
    return row.credit - row.debit


@dataclass
class StatementLine:
    account_id: str
    account_code: str
    account_name: str
    amount: Decimal


@dataclass
class BalanceSheet:
    as_of_date: date
    assets: list[StatementLine] = field(default_factory=list)
    liabilities: list[StatementLine] = field(default_factory=list)
    equity: list[StatementLine] = field(default_factory=list)
    net_income_to_date: Decimal = zero()
    total_assets: Decimal = zero()
    total_liabilities: Decimal = zero()
    total_equity: Decimal = zero()  # includes net_income_to_date
    total_liabilities_and_equity: Decimal = zero()
    is_balanced: bool = True


@dataclass
class IncomeStatement:
    period_start: date
    period_end: date
    revenue: list[StatementLine] = field(default_factory=list)
    cost_of_sales: list[StatementLine] = field(default_factory=list)
    expenses: list[StatementLine] = field(default_factory=list)
    other_income: list[StatementLine] = field(default_factory=list)
    other_expenses: list[StatementLine] = field(default_factory=list)
    total_revenue: Decimal = zero()
    total_cost_of_sales: Decimal = zero()
    gross_profit: Decimal = zero()
    total_expenses: Decimal = zero()
    operating_income: Decimal = zero()
    total_other_income: Decimal = zero()
    total_other_expenses: Decimal = zero()
    net_income: Decimal = zero()


def get_balance_sheet(db: Session, *, business_id: str, as_of_date: date) -> BalanceSheet:
    """
    Assets, Liabilities, and Equity as of a date. Since there is no
    period-close step, cumulative net income (all Revenue/Other Income
    minus all Cost of Sales/Expense/Other Expense, from inception
    through as_of_date) is folded into Equity as a single
    "Net Income (Current)" line -- this is what interim (non-year-end)
    balance sheets do in practice, and it's what makes
    Assets == Liabilities + Equity hold true here.
    """
    rows = get_trial_balance(db, business_id=business_id, as_of_date=as_of_date)

    assets: list[StatementLine] = []
    liabilities: list[StatementLine] = []
    equity: list[StatementLine] = []
    net_income = zero()

    for row in rows:
        amount = to_money(_natural_amount(row))
        line = StatementLine(account_id=row.account_id, account_code=row.account_code, account_name=row.account_name, amount=amount)

        if row.account_type == "Asset":
            assets.append(line)
        elif row.account_type == "Liability":
            liabilities.append(line)
        elif row.account_type == "Equity":
            equity.append(line)
        elif row.account_type in ("Revenue", "Other Income"):
            net_income += amount
        elif row.account_type in ("Cost of Sales", "Expense", "Other Expense"):
            net_income -= amount

    net_income = to_money(net_income)
    total_assets = to_money(sum((l.amount for l in assets), zero()))
    total_liabilities = to_money(sum((l.amount for l in liabilities), zero()))
    total_equity_excl_ni = sum((l.amount for l in equity), zero())
    total_equity = to_money(total_equity_excl_ni + net_income)
    total_liabilities_and_equity = to_money(total_liabilities + total_equity)

    return BalanceSheet(
        as_of_date=as_of_date,
        assets=assets,
        liabilities=liabilities,
        equity=equity,
        net_income_to_date=net_income,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_and_equity=total_liabilities_and_equity,
        is_balanced=(total_assets == total_liabilities_and_equity),
    )


def get_income_statement(db: Session, *, business_id: str, period_start: date, period_end: date) -> IncomeStatement:
    """
    Revenue and expenses for a specific period only (not cumulative --
    see get_period_activity's docstring for why that distinction
    matters here).
    """
    rows = get_period_activity(db, business_id=business_id, date_from=period_start, date_to=period_end)

    revenue: list[StatementLine] = []
    cost_of_sales: list[StatementLine] = []
    expenses: list[StatementLine] = []
    other_income: list[StatementLine] = []
    other_expenses: list[StatementLine] = []

    for row in rows:
        amount = to_money(_natural_amount(row))
        line = StatementLine(account_id=row.account_id, account_code=row.account_code, account_name=row.account_name, amount=amount)

        if row.account_type == "Revenue":
            revenue.append(line)
        elif row.account_type == "Cost of Sales":
            cost_of_sales.append(line)
        elif row.account_type == "Expense":
            expenses.append(line)
        elif row.account_type == "Other Income":
            other_income.append(line)
        elif row.account_type == "Other Expense":
            other_expenses.append(line)

    total_revenue = to_money(sum((l.amount for l in revenue), zero()))
    total_cost_of_sales = to_money(sum((l.amount for l in cost_of_sales), zero()))
    gross_profit = to_money(total_revenue - total_cost_of_sales)
    total_expenses = to_money(sum((l.amount for l in expenses), zero()))
    operating_income = to_money(gross_profit - total_expenses)
    total_other_income = to_money(sum((l.amount for l in other_income), zero()))
    total_other_expenses = to_money(sum((l.amount for l in other_expenses), zero()))
    net_income = to_money(operating_income + total_other_income - total_other_expenses)

    return IncomeStatement(
        period_start=period_start,
        period_end=period_end,
        revenue=revenue,
        cost_of_sales=cost_of_sales,
        expenses=expenses,
        other_income=other_income,
        other_expenses=other_expenses,
        total_revenue=total_revenue,
        total_cost_of_sales=total_cost_of_sales,
        gross_profit=gross_profit,
        total_expenses=total_expenses,
        operating_income=operating_income,
        total_other_income=total_other_income,
        total_other_expenses=total_other_expenses,
        net_income=net_income,
    )
