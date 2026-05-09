import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPrimaryKeyMixin, Base


class LicenseCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "license_codes"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    current_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unused")
    batch_id: Mapped[str | None] = mapped_column(String(64))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    activations: Mapped[list["LicenseActivation"]] = relationship(back_populates="license", cascade="all, delete-orphan")


class LicenseActivation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "license_activations"

    license_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("license_codes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    license: Mapped["LicenseCode"] = relationship(back_populates="activations")
