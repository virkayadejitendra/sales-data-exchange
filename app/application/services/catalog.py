from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import (
    BusinessRuleError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.infrastructure.models.organization import Organization, OrganizationType
from app.infrastructure.models.outlet import Outlet, OutletChannel
from app.infrastructure.models.product import Product
from app.infrastructure.models.retailer_product_mapping import RetailerProductMapping
from app.schemas.catalog import (
    OutletCreate,
    OutletUpdate,
    ProductCreate,
    ProductUpdate,
    RetailerProductMappingCreate,
    RetailerProductMappingUpdate,
)


async def _require_organization(
    session: AsyncSession,
    organization_id: UUID,
    expected_type: OrganizationType,
) -> Organization:
    organization = await session.get(Organization, organization_id)
    if organization is None:
        raise ResourceNotFoundError(f"Organization {organization_id} was not found.")
    if organization.type != expected_type:
        label = expected_type.value.lower()
        raise BusinessRuleError(f"Organization {organization_id} must be a {label}.")
    if not organization.is_active:
        raise BusinessRuleError(f"Organization {organization_id} is inactive.")
    return organization


async def _commit(session: AsyncSession, conflict_message: str) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise ResourceConflictError(conflict_message) from error


async def _product_sku_exists(
    session: AsyncSession,
    manufacturer_id: UUID,
    manufacturer_sku: str,
    excluding_id: UUID | None = None,
) -> bool:
    statement = select(Product.id).where(
        Product.manufacturer_id == manufacturer_id,
        Product.manufacturer_sku == manufacturer_sku,
    )
    if excluding_id is not None:
        statement = statement.where(Product.id != excluding_id)
    return (await session.scalar(statement)) is not None


async def _gtin_exists(
    session: AsyncSession,
    gtin: str,
    excluding_id: UUID | None = None,
) -> bool:
    statement = select(Product.id).where(Product.gtin == gtin)
    if excluding_id is not None:
        statement = statement.where(Product.id != excluding_id)
    return (await session.scalar(statement)) is not None


async def create_product(session: AsyncSession, data: ProductCreate) -> Product:
    await _require_organization(session, data.manufacturer_id, OrganizationType.MANUFACTURER)
    if await _product_sku_exists(session, data.manufacturer_id, data.manufacturer_sku):
        raise ResourceConflictError(
            f"Manufacturer SKU {data.manufacturer_sku} already exists for this manufacturer."
        )
    if data.gtin is not None and await _gtin_exists(session, data.gtin):
        raise ResourceConflictError(f"GTIN {data.gtin} already exists.")

    product = Product(**data.model_dump())
    session.add(product)
    await _commit(session, "The manufacturer SKU or GTIN already exists.")
    await session.refresh(product)
    return product


async def get_product(session: AsyncSession, product_id: UUID) -> Product:
    product = await session.get(Product, product_id)
    if product is None:
        raise ResourceNotFoundError(f"Product {product_id} was not found.")
    return product


async def list_products(
    session: AsyncSession,
    *,
    manufacturer_id: UUID | None,
    manufacturer_sku: str | None,
    brand: str | None,
    category: str | None,
    gtin: str | None,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> Sequence[Product]:
    statement: Select[tuple[Product]] = select(Product)
    if manufacturer_id is not None:
        statement = statement.where(Product.manufacturer_id == manufacturer_id)
    if manufacturer_sku is not None:
        statement = statement.where(Product.manufacturer_sku == manufacturer_sku.upper())
    if brand is not None:
        statement = statement.where(Product.brand.ilike(f"%{brand}%"))
    if category is not None:
        statement = statement.where(Product.category.ilike(f"%{category}%"))
    if gtin is not None:
        statement = statement.where(Product.gtin == gtin)
    if is_active is not None:
        statement = statement.where(Product.is_active == is_active)
    statement = statement.order_by(Product.created_at, Product.id).offset(offset).limit(limit)
    return (await session.scalars(statement)).all()


async def update_product(
    session: AsyncSession,
    product_id: UUID,
    data: ProductUpdate,
) -> Product:
    product = await get_product(session, product_id)
    changes = data.model_dump(exclude_unset=True)

    new_sku = changes.get("manufacturer_sku")
    if new_sku is not None and await _product_sku_exists(
        session,
        product.manufacturer_id,
        new_sku,
        excluding_id=product.id,
    ):
        raise ResourceConflictError(
            f"Manufacturer SKU {new_sku} already exists for this manufacturer."
        )
    if (
        "gtin" in changes
        and changes["gtin"] is not None
        and await _gtin_exists(
            session,
            changes["gtin"],
            excluding_id=product.id,
        )
    ):
        raise ResourceConflictError(f"GTIN {changes['gtin']} already exists.")

    for field_name, value in changes.items():
        setattr(product, field_name, value)
    await _commit(session, "The manufacturer SKU or GTIN already exists.")
    await session.refresh(product)
    return product


async def deactivate_product(session: AsyncSession, product_id: UUID) -> None:
    product = await get_product(session, product_id)
    product.is_active = False
    await _commit(session, "The product could not be deactivated.")


async def _outlet_code_exists(
    session: AsyncSession,
    retailer_id: UUID,
    code: str,
    excluding_id: UUID | None = None,
) -> bool:
    statement = select(Outlet.id).where(
        Outlet.retailer_id == retailer_id,
        Outlet.code == code,
    )
    if excluding_id is not None:
        statement = statement.where(Outlet.id != excluding_id)
    return (await session.scalar(statement)) is not None


async def create_outlet(session: AsyncSession, data: OutletCreate) -> Outlet:
    await _require_organization(session, data.retailer_id, OrganizationType.RETAILER)
    if await _outlet_code_exists(session, data.retailer_id, data.code):
        raise ResourceConflictError(f"Outlet code {data.code} already exists for this retailer.")

    outlet = Outlet(**data.model_dump())
    session.add(outlet)
    await _commit(session, "The outlet code already exists for this retailer.")
    await session.refresh(outlet)
    return outlet


async def get_outlet(session: AsyncSession, outlet_id: UUID) -> Outlet:
    outlet = await session.get(Outlet, outlet_id)
    if outlet is None:
        raise ResourceNotFoundError(f"Outlet {outlet_id} was not found.")
    return outlet


async def list_outlets(
    session: AsyncSession,
    *,
    retailer_id: UUID | None,
    code: str | None,
    channel: OutletChannel | None,
    city: str | None,
    state: str | None,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> Sequence[Outlet]:
    statement: Select[tuple[Outlet]] = select(Outlet)
    if retailer_id is not None:
        statement = statement.where(Outlet.retailer_id == retailer_id)
    if code is not None:
        statement = statement.where(Outlet.code == code.upper())
    if channel is not None:
        statement = statement.where(Outlet.channel == channel)
    if city is not None:
        statement = statement.where(Outlet.city.ilike(f"%{city}%"))
    if state is not None:
        statement = statement.where(Outlet.state.ilike(f"%{state}%"))
    if is_active is not None:
        statement = statement.where(Outlet.is_active == is_active)
    statement = statement.order_by(Outlet.created_at, Outlet.id).offset(offset).limit(limit)
    return (await session.scalars(statement)).all()


async def update_outlet(
    session: AsyncSession,
    outlet_id: UUID,
    data: OutletUpdate,
) -> Outlet:
    outlet = await get_outlet(session, outlet_id)
    changes = data.model_dump(exclude_unset=True)
    new_code = changes.get("code")
    if new_code is not None and await _outlet_code_exists(
        session,
        outlet.retailer_id,
        new_code,
        excluding_id=outlet.id,
    ):
        raise ResourceConflictError(f"Outlet code {new_code} already exists for this retailer.")

    for field_name, value in changes.items():
        setattr(outlet, field_name, value)
    await _commit(session, "The outlet code already exists for this retailer.")
    await session.refresh(outlet)
    return outlet


async def deactivate_outlet(session: AsyncSession, outlet_id: UUID) -> None:
    outlet = await get_outlet(session, outlet_id)
    outlet.is_active = False
    await _commit(session, "The outlet could not be deactivated.")


async def _retailer_sku_exists(
    session: AsyncSession,
    retailer_id: UUID,
    retailer_sku: str,
    excluding_id: UUID | None = None,
) -> bool:
    statement = select(RetailerProductMapping.id).where(
        RetailerProductMapping.retailer_id == retailer_id,
        RetailerProductMapping.retailer_sku == retailer_sku,
    )
    if excluding_id is not None:
        statement = statement.where(RetailerProductMapping.id != excluding_id)
    return (await session.scalar(statement)) is not None


async def _require_active_product(session: AsyncSession, product_id: UUID) -> Product:
    product = await get_product(session, product_id)
    if not product.is_active:
        raise BusinessRuleError(f"Product {product_id} is inactive.")
    await _require_organization(
        session,
        product.manufacturer_id,
        OrganizationType.MANUFACTURER,
    )
    return product


async def create_retailer_product_mapping(
    session: AsyncSession,
    data: RetailerProductMappingCreate,
) -> RetailerProductMapping:
    await _require_organization(session, data.retailer_id, OrganizationType.RETAILER)
    await _require_active_product(session, data.product_id)
    if await _retailer_sku_exists(session, data.retailer_id, data.retailer_sku):
        raise ResourceConflictError(
            f"Retailer SKU {data.retailer_sku} already exists for this retailer."
        )

    mapping = RetailerProductMapping(**data.model_dump())
    session.add(mapping)
    await _commit(session, "The retailer SKU already exists for this retailer.")
    await session.refresh(mapping)
    return mapping


async def get_retailer_product_mapping(
    session: AsyncSession,
    mapping_id: UUID,
) -> RetailerProductMapping:
    mapping = await session.get(RetailerProductMapping, mapping_id)
    if mapping is None:
        raise ResourceNotFoundError(f"Retailer product mapping {mapping_id} was not found.")
    return mapping


async def list_retailer_product_mappings(
    session: AsyncSession,
    *,
    retailer_id: UUID | None,
    product_id: UUID | None,
    retailer_sku: str | None,
    is_active: bool | None,
    offset: int,
    limit: int,
) -> Sequence[RetailerProductMapping]:
    statement: Select[tuple[RetailerProductMapping]] = select(RetailerProductMapping)
    if retailer_id is not None:
        statement = statement.where(RetailerProductMapping.retailer_id == retailer_id)
    if product_id is not None:
        statement = statement.where(RetailerProductMapping.product_id == product_id)
    if retailer_sku is not None:
        statement = statement.where(RetailerProductMapping.retailer_sku == retailer_sku.upper())
    if is_active is not None:
        statement = statement.where(RetailerProductMapping.is_active == is_active)
    statement = (
        statement.order_by(
            RetailerProductMapping.created_at,
            RetailerProductMapping.id,
        )
        .offset(offset)
        .limit(limit)
    )
    return (await session.scalars(statement)).all()


async def update_retailer_product_mapping(
    session: AsyncSession,
    mapping_id: UUID,
    data: RetailerProductMappingUpdate,
) -> RetailerProductMapping:
    mapping = await get_retailer_product_mapping(session, mapping_id)
    changes = data.model_dump(exclude_unset=True)

    new_sku = changes.get("retailer_sku")
    if new_sku is not None and await _retailer_sku_exists(
        session,
        mapping.retailer_id,
        new_sku,
        excluding_id=mapping.id,
    ):
        raise ResourceConflictError(f"Retailer SKU {new_sku} already exists for this retailer.")
    if "product_id" in changes:
        await _require_active_product(session, changes["product_id"])

    for field_name, value in changes.items():
        setattr(mapping, field_name, value)
    await _commit(session, "The retailer SKU already exists for this retailer.")
    await session.refresh(mapping)
    return mapping


async def deactivate_retailer_product_mapping(
    session: AsyncSession,
    mapping_id: UUID,
) -> None:
    mapping = await get_retailer_product_mapping(session, mapping_id)
    mapping.is_active = False
    await _commit(session, "The retailer product mapping could not be deactivated.")
