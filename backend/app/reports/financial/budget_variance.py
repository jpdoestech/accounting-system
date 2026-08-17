"""
Budget variance report.

Compares a Budget's per-account amounts against actual activity for
the same fiscal year (read via get_period_activity, same function the
Income Statement uses) -- read-only, no posting, no effect on the
accounting engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.accounting.ledger.queries import get_period_activity
from app.models.account import Account
from app.models.budget import Budget
from app.models.period import FiscalYear
from app.utils.money import to_money, zero


class BudgetVarianceError(Exception):
    pass


@dataclass
class BudgetVarianceRow:
    account_id: str
    account_code: str
    account_name: str
    budgeted_amount: Decimal
    actual_amount: Decimal
    variance: Decimal  # actual - budgeted
    variance_percent: Decimal | None  # None if budgeted_amount is zero


@dataclass
class BudgetVarianceReport:
    budget_id: str
    budget_name: str
    fiscal_year_name: str
    rows: list[BudgetVarianceRow] = field(default_factory=list)


def get_budget_variance(db: Session, *, business_id: str, budget_id: str) -> BudgetVarianceReport:
    budget = db.get(Budget, budget_id)
    if not budget or budget.business_id != business_id:
        raise BudgetVarianceError("Budget not found for this business.")

    fiscal_year = db.get(FiscalYear, budget.fiscal_year_id)
    if not fiscal_year:
        raise BudgetVarianceError("Fiscal year not found for this budget.")

    activity_rows = get_period_activity(
        db, business_id=business_id, date_from=fiscal_year.start_date, date_to=fiscal_year.end_date
    )
    actual_by_account = {row.account_id: (row.debit - row.credit) for row in activity_rows}
    # Note: actual_by_account holds the raw debit-credit net; budget
    # lines are compared to this net directly, so a business should
    # budget expense accounts as positive amounts (their natural debit
    # balance) and revenue accounts as positive amounts too, understanding
    # revenue's net will show as negative here since it's naturally a
    # credit balance -- see BudgetVarianceRow docs in the API schema
    # for how the frontend is expected to present this.

    rows: list[BudgetVarianceRow] = []
    for line in budget.lines:
        account = db.get(Account, line.account_id)
        if not account:
            continue

        raw_actual = actual_by_account.get(line.account_id, zero())
        # Present actual on the account's natural side, same convention
        # as the trial balance / financial statements.
        if account.account_type in ("Asset", "Cost of Sales", "Expense", "Other Expense"):
            actual = raw_actual
        else:
            actual = -raw_actual

        actual = to_money(actual)
        variance = to_money(actual - line.budgeted_amount)
        variance_percent = (
            to_money((variance / line.budgeted_amount) * 100) if line.budgeted_amount != 0 else None
        )

        rows.append(
            BudgetVarianceRow(
                account_id=account.id,
                account_code=account.code,
                account_name=account.name,
                budgeted_amount=line.budgeted_amount,
                actual_amount=actual,
                variance=variance,
                variance_percent=variance_percent,
            )
        )

    rows.sort(key=lambda r: r.account_code)

    return BudgetVarianceReport(
        budget_id=budget.id, budget_name=budget.name, fiscal_year_name=fiscal_year.name, rows=rows
    )
