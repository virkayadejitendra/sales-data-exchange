from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.application.exceptions import (
    ApplicationError,
    BusinessRuleError,
    ResourceConflictError,
    ResourceNotFoundError,
)


async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
    """Translate expected application errors into stable HTTP responses."""
    status_code = status.HTTP_400_BAD_REQUEST
    if isinstance(error, ResourceNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ResourceConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(error, BusinessRuleError):
        status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    return JSONResponse(status_code=status_code, content={"detail": error.message})


def register_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(ApplicationError, application_error_handler)
