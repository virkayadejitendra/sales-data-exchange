from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class RetailerProductMapping(Base):
    __tablename__ = "retailer_product_mappings"
    __table_args__ = (
        UniqueConstraint(
            "retailer_id",
            "retailer_sku",
            name="uq_retailer_product_mappings_retailer_sku",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    retailer_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    retailer_sku: Mapped[str] = mapped_column(String(100))
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
    )
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
