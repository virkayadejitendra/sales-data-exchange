import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.infrastructure.database import check_database_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


async def verify_database_connection() -> None:
    """Raise a service-unavailable response when PostgreSQL cannot be reached."""
    try:
        await check_database_connection()
    except (SQLAlchemyError, OSError) as error:
        logger.warning("Database readiness check failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from error


DatabaseReady = Annotated[None, Depends(verify_database_connection)]


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report whether the API process is running."""
    return HealthResponse()


@router.get(
    "/ready",
    response_model=HealthResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database unavailable"}},
)
async def readiness(_: DatabaseReady) -> HealthResponse:
    """Report whether required infrastructure is reachable."""
    return HealthResponse()
