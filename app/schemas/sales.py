from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Money = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2)]


class SalesSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class SalesItemInput(SalesSchema):
    outlet_code: str = Field(min_length=1, max_length=100)
    retailer_sku: str = Field(min_length=1, max_length=100)
    units_sold: int = Field(ge=0)
    units_returned: int = Field(default=0, ge=0)
    gross_amount: Money
    discount_amount: Money = Decimal("0")
    net_amount: Money
    closing_stock: int | None = Field(default=None, ge=0)
    currency: str = Field(min_length=3, max_length=3)
    source_reference: str | None = Field(default=None, max_length=100)

    @field_validator("outlet_code", "retailer_sku", "currency")
    @classmethod
    def uppercase_identifiers(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_sales_totals(self) -> Self:
        if self.units_returned > self.units_sold:
            raise ValueError("units_returned cannot exceed units_sold")
        if self.discount_amount > self.gross_amount:
            raise ValueError("discount_amount cannot exceed gross_amount")
        if self.net_amount != self.gross_amount - self.discount_amount:
            raise ValueError("net_amount must equal gross_amount minus discount_amount")
        return self


class SalesBatchCreate(SalesSchema):
    retailer_id: UUID
    business_date: date
    items: list[SalesItemInput] = Field(min_length=1, max_length=1_000)

    @model_validator(mode="after")
    def no_duplicate_natural_keys(self) -> Self:
        keys = [(item.outlet_code, item.retailer_sku) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("A batch cannot contain duplicate outlet_code and retailer_sku pairs")
        return self


class CsvSalesRow(SalesItemInput):
    business_date: date


class DailySaleResponse(SalesSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    retailer_id: UUID
    outlet_id: UUID
    product_id: UUID
    business_date: date
    units_sold: int
    units_returned: int
    gross_amount: Decimal
    discount_amount: Decimal
    net_amount: Decimal
    closing_stock: int | None
    currency: str
    source_reference: str | None
    created_at: datetime
    updated_at: datetime


class SalesImportError(SalesSchema):
    row_number: int
    message: str


class SalesImportResponse(SalesSchema):
    dry_run: bool
    inserted_count: int
    updated_count: int
    error_count: int
    errors: list[SalesImportError] = []
