from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AuthorizedUserDevice(Base):
    __tablename__ = "authorized_user_devices"
    __table_args__ = (
        UniqueConstraint("authorized_user_id", "device_id", name="uq_authorized_user_device"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    authorized_user_id: Mapped[int] = mapped_column(
        ForeignKey("authorized_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    authorized_user = relationship("AuthorizedUser", back_populates="authorized_user_devices")
    device = relationship("Device", back_populates="authorized_user_devices")