"""
RefreshToken model.

Stores a hash of each issued refresh token (never the raw token) so a
compromised database dump can't be used to mint new access tokens.
Refresh tokens are single-use and rotated on every /auth/refresh call
(app/api/v1/auth.py): using one marks it revoked and issues a new one,
so replaying an old refresh token after it's been exchanged fails --
this limits the blast radius of a stolen refresh token to a single
use rather than indefinite access.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class RefreshToken(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
