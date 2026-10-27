from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services import catalog
from app.infrastructure.database import get_db_session
from app.infrastructure.models.outlet import OutletChannel
from app.schemas.catalog import OutletCreate, OutletResponse, OutletUpdate

router = APIRouter(prefix="/outlets", tags=["outlets"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=OutletResponse, status_code=status.HTTP_201_CREATED)
async def create_outlet(data: OutletCreate, session: DatabaseSession) -> OutletResponse:
    """Create an outlet owned by an active retailer organization."""
    return OutletResponse.model_validate(await catalog.create_outlet(session, data))


@router.get("", response_model=list[OutletResponse])
async def list_outlets(
    session: DatabaseSession,
    retailer_id: UUID | None = None,
    code: Annotated[str | None, Query(max_length=100)] = None,
    channel: OutletChannel | None = None,
    city: Annotated[str | None, Query(max_length=100)] = None,
    state_name: Annotated[str | None, Query(alias="state", max_length=100)] = None,
    is_active: bool | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OutletResponse]:
    """List outlets using optional location and catalog filters."""
    outlets = await catalog.list_outlets(
        session,
        retailer_id=retailer_id,
        code=code,
        channel=channel,
        city=city,
        state=state_name,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return [OutletResponse.model_validate(outlet) for outlet in outlets]


@router.get("/{outlet_id}", response_model=OutletResponse)
async def get_outlet(outlet_id: UUID, session: DatabaseSession) -> OutletResponse:
    """Retrieve one outlet by its UUID."""
    return OutletResponse.model_validate(await catalog.get_outlet(session, outlet_id))


@router.patch("/{outlet_id}", response_model=OutletResponse)
async def update_outlet(
    outlet_id: UUID,
    data: OutletUpdate,
    session: DatabaseSession,
) -> OutletResponse:
    """Update only the outlet fields supplied in the request."""
    outlet = await catalog.update_outlet(session, outlet_id, data)
    return OutletResponse.model_validate(outlet)


@router.delete("/{outlet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outlet(outlet_id: UUID, session: DatabaseSession) -> Response:
    """Soft-delete an outlet by marking it inactive."""
    await catalog.deactivate_outlet(session, outlet_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
