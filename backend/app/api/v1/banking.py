"""
Banking API endpoints: bank accounts, cash receipts, cash
disbursements, and bank reconciliation. Mirrors the Draft-then-Post
pattern from sales/purchases (app/api/v1/sales.py, purchases.py).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.bank import BankAccount
from app.models.bank_reconciliation import BankReconciliation
from app.models.business import Business
from app.models.cash_disbursement import CashDisbursement
from app.models.cash_receipt import CashReceipt
from app.models.user import User, UserBusinessRole
from app.schemas.banking import (
    BankAccountCreate,
    BankAccountRead,
    BankAccountUpdate,
    BankReconciliationRead,
    BankReconciliationRequest,
    CashDisbursementCreate,
    CashDisbursementRead,
    CashReceiptCreate,
    CashReceiptRead,
)
from app.services.banking import (
    AllocationInput,
    BankingPostingError,
    create_draft_disbursement,
    create_draft_receipt,
    post_disbursement,
    post_receipt,
)
from app.services.reconciliation import ReconciliationError, reconcile_bank_account

router = APIRouter(prefix="/businesses/{business_id}", tags=["banking"])


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


# ------------------------------------------------------------ bank accounts

@router.post("/bank-accounts", response_model=BankAccountRead, status_code=201)
def create_bank_account(
    business_id: str,
    payload: BankAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    account = BankAccount(business_id=business_id, **payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/bank-accounts", response_model=list[BankAccountRead])
def list_bank_accounts(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return db.query(BankAccount).filter(BankAccount.business_id == business_id).order_by(BankAccount.name).all()


@router.put("/bank-accounts/{bank_account_id}", response_model=BankAccountRead)
def update_bank_account(
    business_id: str,
    bank_account_id: str,
    payload: BankAccountUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    account = (
        db.query(BankAccount)
        .filter(BankAccount.id == bank_account_id, BankAccount.business_id == business_id)
        .first()
    )
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


# --------------------------------------------------------------- receipts

@router.post("/cash-receipts", response_model=CashReceiptRead, status_code=201)
def create_cash_receipt(
    business_id: str,
    payload: CashReceiptCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    allocations = [AllocationInput(document_id=a.document_id, amount_applied=a.amount_applied) for a in payload.allocations]

    try:
        receipt = create_draft_receipt(
            db,
            business_id=business_id,
            bank_account_id=payload.bank_account_id,
            customer_id=payload.customer_id,
            receipt_number=payload.receipt_number,
            receipt_date=payload.receipt_date,
            amount=payload.amount,
            allocations=allocations,
            memo=payload.memo,
        )
    except BankingPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return receipt


@router.get("/cash-receipts", response_model=list[CashReceiptRead])
def list_cash_receipts(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(CashReceipt)
        .filter(CashReceipt.business_id == business_id)
        .order_by(CashReceipt.receipt_date.desc())
        .all()
    )


@router.post("/cash-receipts/{receipt_id}/post", response_model=CashReceiptRead)
def post_cash_receipt(
    business_id: str,
    receipt_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    receipt = db.get(CashReceipt, receipt_id)
    if not receipt or receipt.business_id != business_id:
        raise HTTPException(status_code=404, detail="Cash receipt not found.")

    try:
        receipt = post_receipt(db, receipt=receipt, created_by_user_id=current_user.id)
    except BankingPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return receipt


# ----------------------------------------------------------- disbursements

@router.post("/cash-disbursements", response_model=CashDisbursementRead, status_code=201)
def create_cash_disbursement(
    business_id: str,
    payload: CashDisbursementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    allocations = [AllocationInput(document_id=a.document_id, amount_applied=a.amount_applied) for a in payload.allocations]

    try:
        disbursement = create_draft_disbursement(
            db,
            business_id=business_id,
            bank_account_id=payload.bank_account_id,
            vendor_id=payload.vendor_id,
            payment_number=payload.payment_number,
            payment_date=payload.payment_date,
            amount=payload.amount,
            allocations=allocations,
            memo=payload.memo,
        )
    except BankingPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return disbursement


@router.get("/cash-disbursements", response_model=list[CashDisbursementRead])
def list_cash_disbursements(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(CashDisbursement)
        .filter(CashDisbursement.business_id == business_id)
        .order_by(CashDisbursement.payment_date.desc())
        .all()
    )


@router.post("/cash-disbursements/{disbursement_id}/post", response_model=CashDisbursementRead)
def post_cash_disbursement(
    business_id: str,
    disbursement_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    disbursement = db.get(CashDisbursement, disbursement_id)
    if not disbursement or disbursement.business_id != business_id:
        raise HTTPException(status_code=404, detail="Cash disbursement not found.")

    try:
        disbursement = post_disbursement(db, disbursement=disbursement, created_by_user_id=current_user.id)
    except BankingPostingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return disbursement


# --------------------------------------------------------- reconciliation

@router.post("/bank-accounts/{bank_account_id}/reconcile", response_model=BankReconciliationRead)
def reconcile(
    business_id: str,
    bank_account_id: str,
    payload: BankReconciliationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    try:
        reconciliation = reconcile_bank_account(
            db,
            business_id=business_id,
            bank_account_id=bank_account_id,
            statement_date=payload.statement_date,
            statement_ending_balance=payload.statement_ending_balance,
            receipt_ids_to_clear=payload.receipt_ids_to_clear,
            disbursement_ids_to_clear=payload.disbursement_ids_to_clear,
        )
    except ReconciliationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return reconciliation


@router.get("/bank-accounts/{bank_account_id}/reconciliations", response_model=list[BankReconciliationRead])
def list_reconciliations(
    business_id: str,
    bank_account_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(BankReconciliation)
        .filter(
            BankReconciliation.business_id == business_id,
            BankReconciliation.bank_account_id == bank_account_id,
        )
        .order_by(BankReconciliation.statement_date.desc())
        .all()
    )
