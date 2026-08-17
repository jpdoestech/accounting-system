"""
BIR compliance API endpoints: books of accounts, VAT summary, and
withholding tax certificates (BIR Form 2307). Entirely read/report
endpoints except certificate issuance, which persists a
WithholdingTaxCertificate record but never touches the general
ledger -- no new posting logic anywhere in this router.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.bir.books.queries import (
    get_cash_disbursements_book,
    get_cash_receipts_book,
    get_general_journal,
    get_purchase_book,
    get_sales_book,
)
from app.bir.books.vat_summary import get_vat_summary
from app.bir.books.withholding import CertificateGenerationError, issue_certificate, preview_certificate
from app.db.base import get_db
from app.models.business import Business
from app.models.user import User, UserBusinessRole
from app.models.withholding_certificate import WithholdingTaxCertificate
from app.schemas.bir import (
    CashDisbursementBookRow,
    CashReceiptBookRow,
    CertificateIssueRequest,
    CertificatePreviewRead,
    GeneralJournalEntryRead,
    VatSummaryRead,
    WithholdingTaxCertificateRead,
)
from app.schemas.purchases import PurchaseBillRead
from app.schemas.sales import SalesInvoiceRead

router = APIRouter(prefix="/businesses/{business_id}/bir", tags=["bir"])


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


# ------------------------------------------------------------ books

@router.get("/books/general-journal", response_model=list[GeneralJournalEntryRead])
def general_journal(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_general_journal(db, business_id=business_id, date_from=date_from, date_to=date_to)


@router.get("/books/sales-book", response_model=list[SalesInvoiceRead])
def sales_book(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_sales_book(db, business_id=business_id, date_from=date_from, date_to=date_to)


@router.get("/books/purchase-book", response_model=list[PurchaseBillRead])
def purchase_book(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_purchase_book(db, business_id=business_id, date_from=date_from, date_to=date_to)


@router.get("/books/cash-receipts-book", response_model=list[CashReceiptBookRow])
def cash_receipts_book(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_cash_receipts_book(db, business_id=business_id, date_from=date_from, date_to=date_to)


@router.get("/books/cash-disbursements-book", response_model=list[CashDisbursementBookRow])
def cash_disbursements_book(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_cash_disbursements_book(db, business_id=business_id, date_from=date_from, date_to=date_to)


# --------------------------------------------------------------- vat

@router.get("/vat-summary", response_model=VatSummaryRead)
def vat_summary(
    business_id: str,
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return get_vat_summary(db, business_id=business_id, date_from=date_from, date_to=date_to)


# --------------------------------------------------- withholding certificates

@router.get("/withholding-certificates/preview", response_model=CertificatePreviewRead)
def preview_withholding_certificate(
    business_id: str,
    vendor_id: str = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return preview_certificate(
        db, business_id=business_id, vendor_id=vendor_id, period_start=period_start, period_end=period_end
    )


@router.post("/withholding-certificates", response_model=WithholdingTaxCertificateRead, status_code=201)
def issue_withholding_certificate(
    business_id: str,
    payload: CertificateIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    try:
        certificate = issue_certificate(
            db,
            business_id=business_id,
            vendor_id=payload.vendor_id,
            certificate_number=payload.certificate_number,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
    except CertificateGenerationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return certificate


@router.get("/withholding-certificates", response_model=list[WithholdingTaxCertificateRead])
def list_withholding_certificates(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(WithholdingTaxCertificate)
        .filter(WithholdingTaxCertificate.business_id == business_id)
        .order_by(WithholdingTaxCertificate.period_start.desc())
        .all()
    )
