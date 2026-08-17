"""
Phase 10 API endpoints: financial statements (Balance Sheet, Income
Statement) and budgeting/variance. All read-only except budget
creation, which persists a comparison target and never touches the
general ledger.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.budget import Budget, BudgetLine
from app.models.business import Business
from app.models.user import User, UserBusinessRole
from app.reports.financial.budget_variance import BudgetVarianceError, get_budget_variance
from app.reports.financial.statements import get_balance_sheet, get_income_statement
from app.schemas.reports import (
    BalanceSheetRead,
    BudgetCreate,
    BudgetRead,
    BudgetVarianceReportRead,
    IncomeStatementRead,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["reports"])


def _get_authorized_business(business_id: str, db: Session, current_user: User) -> Business:
    access = (
        db.query(UserBusinessRole)
        .filter(
            UserBusinessRole.user_id == current_user.id,
            UserBusinessRole.business_id == business_id,
        )
        .first()
    )
    if not access:
        raise HTTPException(status_code=404, detail="Business not found")
    business = db.get(Business, business_id)
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.get("/reports/balance-sheet", response_model=BalanceSheetRead)
def balance_sheet(
    business_id: str,
    as_of_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_balance_sheet(db, business_id=business_id, as_of_date=as_of_date)


@router.get("/reports/income-statement", response_model=IncomeStatementRead)
def income_statement(
    business_id: str,
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_income_statement(db, business_id=business_id, period_start=period_start, period_end=period_end)


@router.post("/budgets", response_model=BudgetRead, status_code=201)
def create_budget(
    business_id: str,
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    budget = Budget(business_id=business_id, fiscal_year_id=payload.fiscal_year_id, name=payload.name)
    db.add(budget)
    db.flush()

    for line in payload.lines:
        db.add(BudgetLine(budget_id=budget.id, account_id=line.account_id, budgeted_amount=line.budgeted_amount))

    db.commit()
    db.refresh(budget)
    return budget


@router.get("/budgets", response_model=list[BudgetRead])
def list_budgets(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return db.query(Budget).filter(Budget.business_id == business_id).all()


@router.get("/budgets/{budget_id}/variance", response_model=BudgetVarianceReportRead)
def budget_variance(
    business_id: str,
    budget_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    try:
        return get_budget_variance(db, business_id=business_id, budget_id=budget_id)
    except BudgetVarianceError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
