from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class UnitOfMeasure(StrEnum):
    EACH = "EACH"
    GRAM = "GRAM"
    KILOGRAM = "KILOGRAM"
    MILLILITRE = "MILLILITRE"
    LITRE = "LITRE"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint(
            "manufacturer_id",
            "manufacturer_sku",
            name="uq_products_manufacturer_sku",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    manufacturer_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    manufacturer_sku: Mapped[str] = mapped_column(String(100))
    gtin: Mapped[str | None] = mapped_column(String(14), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    subcategory: Mapped[str | None] = mapped_column(String(100), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pack_size: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    unit_of_measure: Mapped[UnitOfMeasure] = mapped_column(
        Enum(
            UnitOfMeasure,
            name="unit_of_measure",
            native_enum=False,
            create_constraint=True,
            length=20,
        )
    )
    mrp: Mapped[Decimal] = mapped_column(Numeric(12, 2))
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
