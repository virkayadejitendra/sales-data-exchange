from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import catalog
from app.infrastructure.database import get_db_session
from app.schemas.catalog import ProductCreate, ProductResponse, ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductCreate, session: DatabaseSession) -> ProductResponse:
    """Create a product owned by an active manufacturer organization."""
    return ProductResponse.model_validate(await catalog.create_product(session, data))


@router.get("", response_model=list[ProductResponse])
async def list_products(
    session: DatabaseSession,
    manufacturer_id: UUID | None = None,
    manufacturer_sku: Annotated[str | None, Query(max_length=100)] = None,
    brand: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=100)] = None,
    gtin: Annotated[str | None, Query(max_length=14)] = None,
    is_active: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ProductResponse]:
    """List products using optional catalog filters and bounded offset pagination."""
    products = await catalog.list_products(
        session,
        manufacturer_id=manufacturer_id,
        manufacturer_sku=manufacturer_sku,
        brand=brand,
        category=category,
        gtin=gtin,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return [ProductResponse.model_validate(product) for product in products]


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: UUID, session: DatabaseSession) -> ProductResponse:
    """Retrieve one product by its UUID."""
    return ProductResponse.model_validate(await catalog.get_product(session, product_id))


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    session: DatabaseSession,
) -> ProductResponse:
    """Update only the product fields supplied in the request."""
    product = await catalog.update_product(session, product_id, data)
    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: UUID, session: DatabaseSession) -> Response:
    """Soft-delete a product by marking it inactive."""
    await catalog.deactivate_product(session, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
