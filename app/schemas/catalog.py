from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.infrastructure.models.outlet import OutletChannel
from app.infrastructure.models.product import UnitOfMeasure

Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PackSize = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]


class CatalogSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ProductCreate(CatalogSchema):
    manufacturer_id: UUID
    manufacturer_sku: str = Field(min_length=1, max_length=100)
    gtin: str | None = None
    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    variant: str | None = Field(default=None, max_length=100)
    pack_size: PackSize
    unit_of_measure: UnitOfMeasure
    mrp: Money
    is_active: bool = True

    @field_validator("manufacturer_sku", mode="after")
    @classmethod
    def normalize_manufacturer_sku(cls, value: str) -> str:
        return value.upper()

    @field_validator("gtin")
    @classmethod
    def validate_gtin(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit() or len(value) not in {8, 12, 13, 14}:
            raise ValueError("GTIN must contain 8, 12, 13, or 14 digits")
        return value


class ProductUpdate(CatalogSchema):
    manufacturer_sku: str | None = Field(default=None, min_length=1, max_length=100)
    gtin: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    brand: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    variant: str | None = Field(default=None, max_length=100)
    pack_size: PackSize | None = None
    unit_of_measure: UnitOfMeasure | None = None
    mrp: Money | None = None
    is_active: bool | None = None

    @field_validator("manufacturer_sku")
    @classmethod
    def normalize_manufacturer_sku(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @field_validator("gtin")
    @classmethod
    def validate_gtin(cls, value: str | None) -> str | None:
        if value is not None and (not value.isdigit() or len(value) not in {8, 12, 13, 14}):
            raise ValueError("GTIN must contain 8, 12, 13, or 14 digits")
        return value

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        nullable_fields = {"gtin", "subcategory", "variant"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductResponse(CatalogSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    manufacturer_id: UUID
    manufacturer_sku: str
    gtin: str | None
    name: str
    brand: str
    category: str
    subcategory: str | None
    variant: str | None
    pack_size: Decimal
    unit_of_measure: UnitOfMeasure
    mrp: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OutletCreate(CatalogSchema):
    retailer_id: UUID
    code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    channel: OutletChannel
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()


class OutletUpdate(CatalogSchema):
    code: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    channel: OutletChannel | None = None
    city: str | None = Field(default=None, max_length=100)
    district: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        nullable_fields = {"city", "district", "state", "country"}
        for field_name in self.model_fields_set - nullable_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class OutletResponse(CatalogSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    retailer_id: UUID
    code: str
    name: str
    channel: OutletChannel
    city: str | None
    district: str | None
    state: str | None
    country: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RetailerProductMappingCreate(CatalogSchema):
    retailer_id: UUID
    retailer_sku: str = Field(min_length=1, max_length=100)
    product_id: UUID
    is_active: bool = True

    @field_validator("retailer_sku")
    @classmethod
    def normalize_retailer_sku(cls, value: str) -> str:
        return value.upper()


class RetailerProductMappingUpdate(CatalogSchema):
    retailer_sku: str | None = Field(default=None, min_length=1, max_length=100)
    product_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("retailer_sku")
    @classmethod
    def normalize_retailer_sku(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None

    @model_validator(mode="after")
    def reject_null_fields(self) -> Self:
        for field_name in self.model_fields_set:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class RetailerProductMappingResponse(CatalogSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    retailer_id: UUID
    retailer_sku: str
    product_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
