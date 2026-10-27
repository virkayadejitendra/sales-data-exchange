from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class OutletChannel(StrEnum):
    SUPERMARKET = "SUPERMARKET"
    GENERAL_TRADE = "GENERAL_TRADE"
    CONVENIENCE = "CONVENIENCE"
    ONLINE = "ONLINE"
    OTHER = "OTHER"


class Outlet(Base):
    __tablename__ = "outlets"
    __table_args__ = (UniqueConstraint("retailer_id", "code", name="uq_outlets_retailer_code"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    retailer_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200))
    channel: Mapped[OutletChannel] = mapped_column(
        Enum(
            OutletChannel,
            name="outlet_channel",
            native_enum=False,
            create_constraint=True,
            length=30,
        ),
        index=True,
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
