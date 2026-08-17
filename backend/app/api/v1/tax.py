"""
Tax rule API endpoints.

Business-scoped CRUD for tax rules, plus a calculation endpoint. Rules
created here can be business-specific (normal case) -- global/system
default rules (business_id NULL) are seeded by an administrator
process, not exposed for a regular business user to create, since they
apply to every business on the platform.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business
from app.models.tax_rule import TaxRule
from app.models.user import User, UserBusinessRole
from app.schemas.tax import (
    TaxCalculationRequest,
    TaxCalculationResponse,
    TaxRuleCreate,
    TaxRuleRead,
    TaxRuleUpdate,
)
from app.tax.engine.calculator import calculate_tax
from app.tax.engine.rules import TaxRuleNotFoundError

router = APIRouter(prefix="/businesses/{business_id}/tax-rules", tags=["tax"])


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


@router.post("", response_model=TaxRuleRead, status_code=201)
def create_tax_rule(
    business_id: str,
    payload: TaxRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    rule = TaxRule(business_id=business_id, status="Active", **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=list[TaxRuleRead])
def list_tax_rules(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(TaxRule)
        .filter(TaxRule.business_id == business_id)
        .order_by(TaxRule.rule_code, TaxRule.effective_from)
        .all()
    )


@router.put("/{rule_id}", response_model=TaxRuleRead)
def update_tax_rule(
    business_id: str,
    rule_id: str,
    payload: TaxRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    rule = (
        db.query(TaxRule)
        .filter(TaxRule.id == rule_id, TaxRule.business_id == business_id)
        .first()
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Tax rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}/retire", response_model=TaxRuleRead)
def retire_tax_rule(
    business_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a rule Retired rather than deleting it -- the rule must
    remain available so transactions dated while it was active can
    still be looked up/audited correctly.
    """
    _get_authorized_business(business_id, db, current_user)
    rule = db.get(TaxRule, rule_id)
    if not rule or rule.business_id != business_id:
        raise HTTPException(status_code=404, detail="Tax rule not found.")
    rule.status = "Retired"
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/calculate", response_model=TaxCalculationResponse)
def calculate(
    business_id: str,
    payload: TaxCalculationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    try:
        result = calculate_tax(
            db,
            business_id=business_id,
            rule_code=payload.rule_code,
            taxable_amount=payload.taxable_amount,
            as_of_date=payload.as_of_date,
        )
    except TaxRuleNotFoundError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return result
