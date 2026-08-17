from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class StatementLineRead(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    amount: Decimal


class BalanceSheetRead(BaseModel):
    as_of_date: date
    assets: list[StatementLineRead]
    liabilities: list[StatementLineRead]
    equity: list[StatementLineRead]
    net_income_to_date: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    is_balanced: bool


class IncomeStatementRead(BaseModel):
    period_start: date
    period_end: date
    revenue: list[StatementLineRead]
    cost_of_sales: list[StatementLineRead]
    expenses: list[StatementLineRead]
    other_income: list[StatementLineRead]
    other_expenses: list[StatementLineRead]
    total_revenue: Decimal
    total_cost_of_sales: Decimal
    gross_profit: Decimal
    total_expenses: Decimal
    operating_income: Decimal
    total_other_income: Decimal
    total_other_expenses: Decimal
    net_income: Decimal


class BudgetLineInput(BaseModel):
    account_id: str
    budgeted_amount: Decimal


class BudgetCreate(BaseModel):
    fiscal_year_id: str
    name: str
    lines: list[BudgetLineInput]


class BudgetLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    account_id: str
    budgeted_amount: Decimal


class BudgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    fiscal_year_id: str
    name: str
    status: str
    lines: list[BudgetLineRead]


class BudgetVarianceRowRead(BaseModel):
    account_id: str
    account_code: str
    account_name: str
    budgeted_amount: Decimal
    actual_amount: Decimal
    variance: Decimal
    variance_percent: Decimal | None = None


class BudgetVarianceReportRead(BaseModel):
    budget_id: str
    budget_name: str
    fiscal_year_name: str
    rows: list[BudgetVarianceRowRead]
