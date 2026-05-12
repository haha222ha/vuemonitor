import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import UUIDPrimaryKeyMixin, Base


class LicenseCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "license_codes"

    # NOTE: Schema discrepancy - existing model maintains both code (VARCHAR(64)) and license_key (VARCHAR(19))
    # for API compatibility. New schema would use license_key as primary identifier instead of code.
    # Also uses max_devices instead of separate max_activations/current_activations fields.
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    max_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    current_activations: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unused")
    batch_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    revoke_reason: Mapped[str | None] = mapped_column(Text)
    license_key: Mapped[str | None] = mapped_column(String(19), unique=True, nullable=True)
    max_devices: Mapped[int | None] = mapped_column(Integer, default=1, nullable=True)
    bound_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    bound_device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    activations: Mapped[list["LicenseActivation"]] = relationship(back_populates="license", cascade="all, delete-orphan")
    change_logs: Mapped[list["LicenseChangeLog"]] = relationship(back_populates="license", cascade="all, delete-orphan")


class LicenseActivation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "license_activations"

    license_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("license_codes.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255))
    device_name: Mapped[str | None] = mapped_column(String(128))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    license: Mapped["LicenseCode"] = relationship(back_populates="activations")


class LicenseChangeLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "license_change_logs"

    license_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("license_codes.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    operator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    license: Mapped["LicenseCode"] = relationship(back_populates="change_logs")
