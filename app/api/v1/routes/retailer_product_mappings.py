from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import catalog
from app.infrastructure.database import get_db_session
from app.schemas.catalog import (
    RetailerProductMappingCreate,
    RetailerProductMappingResponse,
    RetailerProductMappingUpdate,
)

router = APIRouter(prefix="/retailer-product-mappings", tags=["retailer product mappings"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=RetailerProductMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_mapping(
    data: RetailerProductMappingCreate,
    session: DatabaseSession,
) -> RetailerProductMappingResponse:
    """Map one retailer SKU to an active manufacturer product."""
    mapping = await catalog.create_retailer_product_mapping(session, data)
    return RetailerProductMappingResponse.model_validate(mapping)


@router.get("", response_model=list[RetailerProductMappingResponse])
async def list_mappings(
    session: DatabaseSession,
    retailer_id: UUID | None = None,
    product_id: UUID | None = None,
    retailer_sku: Annotated[str | None, Query(max_length=100)] = None,
    is_active: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[RetailerProductMappingResponse]:
    """List retailer SKU mappings using optional filters."""
    mappings = await catalog.list_retailer_product_mappings(
        session,
        retailer_id=retailer_id,
        product_id=product_id,
        retailer_sku=retailer_sku,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return [RetailerProductMappingResponse.model_validate(mapping) for mapping in mappings]


@router.get("/{mapping_id}", response_model=RetailerProductMappingResponse)
async def get_mapping(
    mapping_id: UUID,
    session: DatabaseSession,
) -> RetailerProductMappingResponse:
    """Retrieve one retailer SKU mapping by its UUID."""
    mapping = await catalog.get_retailer_product_mapping(session, mapping_id)
    return RetailerProductMappingResponse.model_validate(mapping)


@router.patch("/{mapping_id}", response_model=RetailerProductMappingResponse)
async def update_mapping(
    mapping_id: UUID,
    data: RetailerProductMappingUpdate,
    session: DatabaseSession,
) -> RetailerProductMappingResponse:
    """Update only the retailer SKU mapping fields supplied in the request."""
    mapping = await catalog.update_retailer_product_mapping(session, mapping_id, data)
    return RetailerProductMappingResponse.model_validate(mapping)


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: UUID, session: DatabaseSession) -> Response:
    """Soft-delete a retailer SKU mapping by marking it inactive."""
    await catalog.deactivate_retailer_product_mapping(session, mapping_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
