"""
User, Role, and business-access models.

Spec Section 12/section on multi-user access: users can be granted
access to one or more businesses; role determines permissions within
that business context.
"""
from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class User(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    business_roles: Mapped[list["UserBusinessRole"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Role(UUIDPKMixin, TimestampMixin, Base):
    """A configurable role (e.g. Admin, Accountant, Viewer)."""

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    is_system_role: Mapped[bool] = mapped_column(Boolean, default=False)


class UserBusinessRole(UUIDPKMixin, TimestampMixin, Base):
    """Grants a user a role within a specific business (Section 12)."""

    __tablename__ = "user_business_roles"
    __table_args__ = (UniqueConstraint("user_id", "business_id", name="uq_user_business"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    business_id: Mapped[str] = mapped_column(ForeignKey("businesses.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="business_roles")
