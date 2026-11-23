import csv
import io
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.exceptions import SalesValidationError
from app.application.services.sales import SalesRow, import_sales
from app.infrastructure.database import get_db_session
from app.schemas.sales import (
    CsvSalesRow,
    SalesBatchCreate,
    SalesImportError,
    SalesImportResponse,
    SalesItemInput,
)

router = APIRouter(prefix="/retailer/sales", tags=["retailer sales"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
REQUIRED_CSV_COLUMNS = {
    "business_date",
    "outlet_code",
    "source_reference",
    "currency",
    "retailer_sku",
    "units_sold",
    "units_returned",
    "gross_amount",
    "discount_amount",
    "net_amount",
    "closing_stock",
}


@router.post("/batch", response_model=SalesImportResponse, status_code=status.HTTP_201_CREATED)
async def import_sales_batch(
    data: SalesBatchCreate,
    session: DatabaseSession,
) -> SalesImportResponse:
    """Atomically import one retailer's sales items for a single business date."""
    rows = [
        SalesRow(row_number=index, business_date=data.business_date, item=item)
        for index, item in enumerate(data.items, start=1)
    ]
    inserted_count, updated_count = await import_sales(
        session,
        data.retailer_id,
        rows,
        dry_run=False,
    )
    return SalesImportResponse(
        dry_run=False,
        inserted_count=inserted_count,
        updated_count=updated_count,
        error_count=0,
    )


def _validation_errors(error: ValidationError, row_number: int) -> list[SalesImportError]:
    return [
        SalesImportError(row_number=row_number, message=entry["msg"]) for entry in error.errors()
    ]


@router.post("/import", response_model=SalesImportResponse)
async def import_sales_csv(
    retailer_id: Annotated[UUID, Query()],
    file: Annotated[UploadFile, File(description="UTF-8 daily sales CSV file")],
    session: DatabaseSession,
    dry_run: Annotated[bool, Query()] = False,
) -> SalesImportResponse:
    """Validate and import a retailer CSV; dry runs never write data."""
    try:
        raw_content = await file.read()
        content = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV file must use UTF-8 encoding.",
        ) from error

    reader = csv.DictReader(io.StringIO(content))
    headers = set(reader.fieldnames or [])
    if headers != REQUIRED_CSV_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV headers must exactly match the documented sales CSV columns.",
        )

    errors: list[SalesImportError] = []
    rows: list[SalesRow] = []
    for row_number, raw_row in enumerate(reader, start=2):
        try:
            csv_row = CsvSalesRow.model_validate(raw_row)
            item = SalesItemInput.model_validate(csv_row.model_dump(exclude={"business_date"}))
            rows.append(
                SalesRow(row_number=row_number, business_date=csv_row.business_date, item=item)
            )
        except ValidationError as error:
            errors.extend(_validation_errors(error, row_number))

    if not rows and not errors:
        errors.append(SalesImportError(row_number=1, message="CSV file contains no data rows."))

    if errors:
        if dry_run:
            return SalesImportResponse(
                dry_run=True,
                inserted_count=0,
                updated_count=0,
                error_count=len(errors),
                errors=errors,
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV validation failed. Use dry_run=true for row-level errors.",
        )

    try:
        inserted_count, updated_count = await import_sales(
            session,
            retailer_id,
            rows,
            dry_run=dry_run,
        )
    except SalesValidationError as error:
        if not dry_run:
            raise
        validation_errors = [SalesImportError.model_validate(item) for item in error.errors]
        return SalesImportResponse(
            dry_run=True,
            inserted_count=0,
            updated_count=0,
            error_count=len(validation_errors),
            errors=validation_errors,
        )

    return SalesImportResponse(
        dry_run=dry_run,
        inserted_count=inserted_count,
        updated_count=updated_count,
        error_count=0,
    )
