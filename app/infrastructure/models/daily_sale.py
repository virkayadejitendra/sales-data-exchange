from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class DailySale(Base):
    __tablename__ = "daily_sales"
    __table_args__ = (
        UniqueConstraint(
            "retailer_id",
            "outlet_id",
            "product_id",
            "business_date",
            name="uq_daily_sales_retailer_outlet_product_date",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    retailer_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    outlet_id: Mapped[UUID] = mapped_column(
        ForeignKey("outlets.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    business_date: Mapped[date] = mapped_column(Date, index=True)
    units_sold: Mapped[int] = mapped_column(Integer)
    units_returned: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0, server_default="0")
    net_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    closing_stock: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3))
    source_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
