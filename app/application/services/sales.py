from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import (
    BusinessRuleError,
    ResourceNotFoundError,
    SalesValidationError,
)
from app.infrastructure.models.daily_sale import DailySale
from app.infrastructure.models.organization import Organization, OrganizationType
from app.infrastructure.models.outlet import Outlet
from app.infrastructure.models.product import Product
from app.infrastructure.models.retailer_product_mapping import RetailerProductMapping
from app.schemas.sales import SalesItemInput


@dataclass(frozen=True)
class SalesRow:
    row_number: int
    business_date: date
    item: SalesItemInput


@dataclass(frozen=True)
class PreparedSale:
    row: SalesRow
    outlet_id: UUID
    product_id: UUID
    existing_sale: DailySale | None


async def _require_active_retailer(session: AsyncSession, retailer_id: UUID) -> None:
    organization = await session.get(Organization, retailer_id)
    if organization is None:
        raise ResourceNotFoundError(f"Organization {retailer_id} was not found.")
    if organization.type != OrganizationType.RETAILER:
        raise BusinessRuleError(f"Organization {retailer_id} must be a retailer.")
    if not organization.is_active:
        raise BusinessRuleError(f"Organization {retailer_id} is inactive.")


async def _validate_rows(
    session: AsyncSession,
    retailer_id: UUID,
    rows: Sequence[SalesRow],
) -> list[PreparedSale]:
    await _require_active_retailer(session, retailer_id)
    errors: list[dict[str, object]] = []
    prepared: list[PreparedSale] = []
    seen_keys: set[tuple[str, str, date]] = set()

    for row in rows:
        item = row.item
        key = (item.outlet_code, item.retailer_sku, row.business_date)
        if key in seen_keys:
            errors.append(
                {
                    "row_number": row.row_number,
                    "message": "Duplicate outlet_code, retailer_sku, and business_date in request.",
                }
            )
            continue
        seen_keys.add(key)

        outlet = await session.scalar(
            select(Outlet).where(
                Outlet.retailer_id == retailer_id,
                Outlet.code == item.outlet_code,
                Outlet.is_active.is_(True),
            )
        )
        if outlet is None:
            errors.append(
                {
                    "row_number": row.row_number,
                    "message": f"No active outlet exists for code {item.outlet_code}.",
                }
            )
            continue

        mapping = await session.scalar(
            select(RetailerProductMapping).where(
                RetailerProductMapping.retailer_id == retailer_id,
                RetailerProductMapping.retailer_sku == item.retailer_sku,
                RetailerProductMapping.is_active.is_(True),
            )
        )
        if mapping is None:
            errors.append(
                {
                    "row_number": row.row_number,
                    "message": (
                        f"No active product mapping exists for retailer SKU {item.retailer_sku}."
                    ),
                }
            )
            continue

        product = await session.get(Product, mapping.product_id)
        if product is None or not product.is_active:
            errors.append(
                {
                    "row_number": row.row_number,
                    "message": f"Mapped product for retailer SKU {item.retailer_sku} is inactive.",
                }
            )
            continue

        existing_sale = await session.scalar(
            select(DailySale).where(
                DailySale.retailer_id == retailer_id,
                DailySale.outlet_id == outlet.id,
                DailySale.product_id == product.id,
                DailySale.business_date == row.business_date,
            )
        )
        prepared.append(
            PreparedSale(
                row=row,
                outlet_id=outlet.id,
                product_id=product.id,
                existing_sale=existing_sale,
            )
        )

    if errors:
        raise SalesValidationError("Sales validation failed.", errors)
    return prepared


async def import_sales(
    session: AsyncSession,
    retailer_id: UUID,
    rows: Sequence[SalesRow],
    *,
    dry_run: bool,
) -> tuple[int, int]:
    """Validate and atomically insert or update retailer daily sales rows."""
    prepared = await _validate_rows(session, retailer_id, rows)
    inserted_count = sum(item.existing_sale is None for item in prepared)
    updated_count = len(prepared) - inserted_count
    if dry_run:
        return inserted_count, updated_count

    try:
        for prepared_sale in prepared:
            row = prepared_sale.row
            item = row.item
            values = {
                "units_sold": item.units_sold,
                "units_returned": item.units_returned,
                "gross_amount": item.gross_amount,
                "discount_amount": item.discount_amount,
                "net_amount": item.net_amount,
                "closing_stock": item.closing_stock,
                "currency": item.currency,
                "source_reference": item.source_reference,
            }
            if prepared_sale.existing_sale is None:
                session.add(
                    DailySale(
                        retailer_id=retailer_id,
                        outlet_id=prepared_sale.outlet_id,
                        product_id=prepared_sale.product_id,
                        business_date=row.business_date,
                        **values,
                    )
                )
            else:
                for field_name, value in values.items():
                    setattr(prepared_sale.existing_sale, field_name, value)
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise BusinessRuleError("Sales import could not be completed. Please retry.") from error
    return inserted_count, updated_count
