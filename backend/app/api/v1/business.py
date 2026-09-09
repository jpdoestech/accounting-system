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
from app.models.user import Role, User, UserBusinessRole
from app.schemas.business import (
    BusinessCreate,
    BusinessMemberInvite,
    BusinessMemberRead,
    BusinessMemberRoleUpdate,
    BusinessRead,
    BusinessSettingsRead,
    BusinessSettingsUpdate,
    RoleRead,
)

# Every business gets these three roles available to assign, created
# lazily the first time they're needed rather than via a migration
# data-seed -- keeps the roles table simple and self-healing even for
# businesses created before this existed.
DEFAULT_ROLE_NAMES = ["Admin", "Accountant", "Viewer"]


def _get_or_create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).first()
    if role is None:
        role = Role(name=name, description=f"{name} access", is_system_role=True)
        db.add(role)
        db.flush()
    return role

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

    # Grant the creating user Admin access to this new business.
    admin_role = _get_or_create_role(db, "Admin")
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


def _require_admin(business_id: str, db: Session, current_user: User) -> UserBusinessRole:
    """
    Only an Admin on this specific business can invite/remove members or
    change roles -- everyone else with access can still use the business
    normally (this app doesn't yet enforce per-role restrictions on
    accounting actions themselves, only on managing who has access).
    """
    membership = (
        db.query(UserBusinessRole)
        .filter(UserBusinessRole.user_id == current_user.id, UserBusinessRole.business_id == business_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Business not found")
    role = db.get(Role, membership.role_id)
    if not role or role.name != "Admin":
        raise HTTPException(status_code=403, detail="Only an Admin on this business can manage team members.")
    return membership


def _admin_count(business_id: str, db: Session) -> int:
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if not admin_role:
        return 0
    return (
        db.query(UserBusinessRole)
        .filter(UserBusinessRole.business_id == business_id, UserBusinessRole.role_id == admin_role.id)
        .count()
    )


@router.get("/{business_id}/roles", response_model=list[RoleRead])
def list_roles(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    for name in DEFAULT_ROLE_NAMES:
        _get_or_create_role(db, name)
    db.commit()
    return db.query(Role).filter(Role.name.in_(DEFAULT_ROLE_NAMES)).order_by(Role.name).all()


@router.get("/{business_id}/users", response_model=list[BusinessMemberRead])
def list_business_members(
    business_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_authorized_business(business_id, db, current_user)
    rows = (
        db.query(UserBusinessRole, User, Role)
        .join(User, UserBusinessRole.user_id == User.id)
        .join(Role, UserBusinessRole.role_id == Role.id)
        .filter(UserBusinessRole.business_id == business_id)
        .order_by(User.email)
        .all()
    )
    return [
        BusinessMemberRead(
            id=ubr.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_name=role.name,
            is_self=(user.id == current_user.id),
        )
        for ubr, user, role in rows
    ]


@router.post("/{business_id}/users", response_model=BusinessMemberRead, status_code=201)
def invite_business_member(
    business_id: str,
    payload: BusinessMemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(business_id, db, current_user)

    if payload.role_name not in DEFAULT_ROLE_NAMES:
        raise HTTPException(status_code=400, detail=f"role_name must be one of {DEFAULT_ROLE_NAMES}")

    invited_user = db.query(User).filter(User.email == payload.email).first()
    if not invited_user:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No account exists yet for {payload.email}. There's no email-invite system --"
                " they need to register an account themselves first, then you can add them."
            ),
        )

    existing = (
        db.query(UserBusinessRole)
        .filter(UserBusinessRole.user_id == invited_user.id, UserBusinessRole.business_id == business_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"{payload.email} already has access to this business.")

    role = _get_or_create_role(db, payload.role_name)
    ubr = UserBusinessRole(user_id=invited_user.id, business_id=business_id, role_id=role.id)
    db.add(ubr)
    db.commit()
    db.refresh(ubr)

    return BusinessMemberRead(
        id=ubr.id, user_id=invited_user.id, email=invited_user.email,
        full_name=invited_user.full_name, role_name=role.name, is_self=False,
    )


@router.patch("/{business_id}/users/{membership_id}", response_model=BusinessMemberRead)
def update_business_member_role(
    business_id: str,
    membership_id: str,
    payload: BusinessMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(business_id, db, current_user)

    if payload.role_name not in DEFAULT_ROLE_NAMES:
        raise HTTPException(status_code=400, detail=f"role_name must be one of {DEFAULT_ROLE_NAMES}")

    ubr = db.get(UserBusinessRole, membership_id)
    if not ubr or ubr.business_id != business_id:
        raise HTTPException(status_code=404, detail="Membership not found")

    current_role = db.get(Role, ubr.role_id)
    if current_role.name == "Admin" and payload.role_name != "Admin" and _admin_count(business_id, db) <= 1:
        raise HTTPException(
            status_code=400,
            detail="This is the last Admin on this business -- promote someone else to Admin first.",
        )

    new_role = _get_or_create_role(db, payload.role_name)
    ubr.role_id = new_role.id
    db.commit()
    db.refresh(ubr)

    user = db.get(User, ubr.user_id)
    return BusinessMemberRead(
        id=ubr.id, user_id=user.id, email=user.email, full_name=user.full_name,
        role_name=new_role.name, is_self=(user.id == current_user.id),
    )


@router.delete("/{business_id}/users/{membership_id}", status_code=204)
def remove_business_member(
    business_id: str,
    membership_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(business_id, db, current_user)

    ubr = db.get(UserBusinessRole, membership_id)
    if not ubr or ubr.business_id != business_id:
        raise HTTPException(status_code=404, detail="Membership not found")

    role = db.get(Role, ubr.role_id)
    if role.name == "Admin" and _admin_count(business_id, db) <= 1:
        raise HTTPException(
            status_code=400,
            detail="Can't remove the last Admin on this business -- promote someone else to Admin first.",
        )

    db.delete(ubr)
    db.commit()
    return None
