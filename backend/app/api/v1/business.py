"""
Business profile and settings endpoints.

Spec Section 11/12/13: business setup and configurable settings, with
access enforced per authenticated user (business isolation).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business, BusinessSettings
from app.models.user import User, UserBusinessRole
from app.schemas.business import (
    BusinessCreate,
    BusinessRead,
    BusinessSettingsRead,
    BusinessSettingsUpdate,
)

router = APIRouter(prefix="/businesses", tags=["business"])


@router.post("", response_model=BusinessRead, status_code=201)
def create_business(
    payload: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    business = Business(**payload.model_dump())
    db.add(business)
    db.flush()

    settings = BusinessSettings(business_id=business.id)
    db.add(settings)

    # Grant the creating user access to this new business.
    from app.models.user import Role

    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if admin_role is None:
        admin_role = Role(name="Admin", description="Full business access", is_system_role=True)
        db.add(admin_role)
        db.flush()

    db.add(UserBusinessRole(user_id=current_user.id, business_id=business.id, role_id=admin_role.id))

    db.commit()
    db.refresh(business)
    return business


@router.get("", response_model=list[BusinessRead])
def list_my_businesses(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    business_ids = [
        r.business_id
        for r in db.query(UserBusinessRole).filter(UserBusinessRole.user_id == current_user.id)
    ]
    if not business_ids:
        return []
    return db.query(Business).filter(Business.id.in_(business_ids)).all()


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


@router.get("/{business_id}", response_model=BusinessRead)
def get_business(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_authorized_business(business_id, db, current_user)


@router.get("/{business_id}/settings", response_model=BusinessSettingsRead)
def get_business_settings(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return settings


@router.patch("/{business_id}/settings", response_model=BusinessSettingsRead)
def update_business_settings(
    business_id: str,
    payload: BusinessSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    settings = db.query(BusinessSettings).filter(BusinessSettings.business_id == business_id).first()
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    db.commit()
    db.refresh(settings)
    return settings
