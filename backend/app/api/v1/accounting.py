"""
Accounting API endpoints.

Every business-scoped route re-checks the requesting user's access via
_get_authorized_business (mirrors app/api/v1/business.py) -- no route
here trusts a bare business_id path param.

Posting goes through app.accounting.engine.posting exclusively; this
router never constructs a JournalEntry/JournalLine directly (Section 9).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.accounting.engine.posting import LineInput, PostingError, post_journal_entry, reverse_entry
from app.accounting.ledger.queries import get_account_ledger, get_trial_balance
from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.account import Account
from app.models.business import Business
from app.models.journal import JournalEntry
from app.models.period import AccountingPeriod, FiscalYear
from app.models.user import User, UserBusinessRole
from app.schemas.accounting import (
    AccountCreate,
    AccountingPeriodCreate,
    AccountingPeriodRead,
    AccountLedgerRead,
    AccountRead,
    AccountUpdate,
    FiscalYearCreate,
    FiscalYearRead,
    JournalEntryCreate,
    JournalEntryRead,
    TrialBalanceRowRead,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["accounting"])


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


# ---------------------------------------------------------------- accounts

@router.post("/accounts", response_model=AccountRead, status_code=201)
def create_account(
    business_id: str,
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)

    existing = (
        db.query(Account)
        .filter(Account.business_id == business_id, Account.code == payload.code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Account code '{payload.code}' already exists.")

    account = Account(business_id=business_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(Account)
        .filter(Account.business_id == business_id)
        .order_by(Account.code)
        .all()
    )


@router.put("/accounts/{account_id}", response_model=AccountRead)
def update_account(
    business_id: str,
    account_id: str,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.business_id == business_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


# ----------------------------------------------------------------- periods

@router.post("/fiscal-years", response_model=FiscalYearRead, status_code=201)
def create_fiscal_year(
    business_id: str,
    payload: FiscalYearCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    fiscal_year = FiscalYear(business_id=business_id, **payload.model_dump())
    db.add(fiscal_year)
    db.commit()
    db.refresh(fiscal_year)
    return fiscal_year


@router.get("/fiscal-years", response_model=list[FiscalYearRead])
def list_fiscal_years(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return db.query(FiscalYear).filter(FiscalYear.business_id == business_id).all()


@router.post("/periods", response_model=AccountingPeriodRead, status_code=201)
def create_period(
    business_id: str,
    payload: AccountingPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    fiscal_year = db.get(FiscalYear, payload.fiscal_year_id)
    if not fiscal_year or fiscal_year.business_id != business_id:
        raise HTTPException(status_code=400, detail="Fiscal year not found for this business.")

    period = AccountingPeriod(business_id=business_id, **payload.model_dump())
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.get("/periods", response_model=list[AccountingPeriodRead])
def list_periods(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(AccountingPeriod)
        .filter(AccountingPeriod.business_id == business_id)
        .order_by(AccountingPeriod.start_date)
        .all()
    )


@router.patch("/periods/{period_id}/close", response_model=AccountingPeriodRead)
def close_period(
    business_id: str,
    period_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    period = db.get(AccountingPeriod, period_id)
    if not period or period.business_id != business_id:
        raise HTTPException(status_code=404, detail="Period not found.")
    period.status = "Closed"
    db.commit()
    db.refresh(period)
    return period


# ------------------------------------------------------------- journal entries

@router.post("/journal-entries", response_model=JournalEntryRead, status_code=201)
def create_journal_entry(
    business_id: str,
    payload: JournalEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)

    lines = [
        LineInput(account_id=l.account_id, debit=l.debit, credit=l.credit, description=l.description)
        for l in payload.lines
    ]

    try:
        entry = post_journal_entry(
            db,
            business_id=business_id,
            entry_date=payload.entry_date,
            lines=lines,
            reference=payload.reference,
            memo=payload.memo,
            source="Manual",
            created_by_user_id=current_user.id,
        )
    except PostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return entry


@router.get("/journal-entries", response_model=list[JournalEntryRead])
def list_journal_entries(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(JournalEntry)
        .filter(JournalEntry.business_id == business_id)
        .order_by(JournalEntry.entry_date.desc())
        .all()
    )


@router.post("/journal-entries/{entry_id}/reverse", response_model=JournalEntryRead)
def reverse_journal_entry(
    business_id: str,
    entry_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    original = db.get(JournalEntry, entry_id)
    if not original or original.business_id != business_id:
        raise HTTPException(status_code=404, detail="Journal entry not found.")

    try:
        reversal = reverse_entry(
            db,
            original_entry=original,
            reversal_date=original.entry_date,
            created_by_user_id=current_user.id,
        )
    except PostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return reversal


# ----------------------------------------------------------------- reports

@router.get("/accounts/{account_id}/ledger", response_model=AccountLedgerRead)
def account_ledger(
    business_id: str,
    account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    try:
        return get_account_ledger(db, business_id=business_id, account_id=account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/reports/trial-balance", response_model=list[TrialBalanceRowRead])
def trial_balance(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_trial_balance(db, business_id=business_id)
