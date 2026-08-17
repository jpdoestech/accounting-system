"""
Fixed assets API endpoints: asset register, depreciation schedule
preview, and posting monthly depreciation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.base import get_db
from app.models.business import Business
from app.models.depreciation_entry import DepreciationEntry
from app.models.fixed_asset import FixedAsset
from app.models.user import User, UserBusinessRole
from app.schemas.fixed_assets import (
    DepreciationEntryRead,
    DepreciationPostRequest,
    DepreciationScheduleRowRead,
    FixedAssetCreate,
    FixedAssetRead,
    FixedAssetUpdate,
)
from app.services.fixed_assets import (
    FixedAssetError,
    post_monthly_depreciation,
    preview_depreciation_schedule,
)

router = APIRouter(prefix="/businesses/{business_id}", tags=["fixed-assets"])


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


@router.post("/fixed-assets", response_model=FixedAssetRead, status_code=201)
def create_fixed_asset(
    business_id: str,
    payload: FixedAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    existing = (
        db.query(FixedAsset)
        .filter(FixedAsset.business_id == business_id, FixedAsset.asset_code == payload.asset_code)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Asset code '{payload.asset_code}' already exists.")

    asset = FixedAsset(business_id=business_id, **payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/fixed-assets", response_model=list[FixedAssetRead])
def list_fixed_assets(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    return (
        db.query(FixedAsset)
        .filter(FixedAsset.business_id == business_id)
        .order_by(FixedAsset.asset_code)
        .all()
    )


@router.put("/fixed-assets/{asset_id}", response_model=FixedAssetRead)
def update_fixed_asset(
    business_id: str,
    asset_id: str,
    payload: FixedAssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    asset = (
        db.query(FixedAsset)
        .filter(FixedAsset.id == asset_id, FixedAsset.business_id == business_id)
        .first()
    )
    if not asset:
        raise HTTPException(status_code=404, detail="Fixed asset not found")
    updates = payload.model_dump(exclude_unset=True)
    if "asset_code" in updates and updates["asset_code"] != asset.asset_code:
        clash = (
            db.query(FixedAsset)
            .filter(FixedAsset.business_id == business_id, FixedAsset.asset_code == updates["asset_code"])
            .first()
        )
        if clash:
            raise HTTPException(status_code=400, detail=f"Asset code '{updates['asset_code']}' already exists.")
    for field, value in updates.items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("/fixed-assets/{asset_id}/schedule", response_model=list[DepreciationScheduleRowRead])
def depreciation_schedule(
    business_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    asset = db.get(FixedAsset, asset_id)
    if not asset or asset.business_id != business_id:
        raise HTTPException(status_code=404, detail="Fixed asset not found.")
    return preview_depreciation_schedule(asset)


@router.post("/fixed-assets/{asset_id}/depreciate", response_model=DepreciationEntryRead)
def post_depreciation(
    business_id: str,
    asset_id: str,
    payload: DepreciationPostRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    asset = db.get(FixedAsset, asset_id)
    if not asset or asset.business_id != business_id:
        raise HTTPException(status_code=404, detail="Fixed asset not found.")

    try:
        entry = post_monthly_depreciation(
            db,
            asset=asset,
            period_year=payload.period_year,
            period_month=payload.period_month,
            entry_date=payload.entry_date,
            created_by_user_id=current_user.id,
        )
    except FixedAssetError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return entry


@router.get("/fixed-assets/{asset_id}/depreciation-entries", response_model=list[DepreciationEntryRead])
def list_depreciation_entries(
    business_id: str,
    asset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    asset = db.get(FixedAsset, asset_id)
    if not asset or asset.business_id != business_id:
        raise HTTPException(status_code=404, detail="Fixed asset not found.")
    return (
        db.query(DepreciationEntry)
        .filter(DepreciationEntry.asset_id == asset_id)
        .order_by(DepreciationEntry.period_year, DepreciationEntry.period_month)
        .all()
    )
