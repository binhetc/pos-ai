"""Product schemas for API request/response."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    cost: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    image_url: str | None = Field(None, max_length=500)
    is_active: bool = True


class ProductCreate(ProductBase):
    category_id: UUID


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    sku: str | None = Field(None, min_length=1, max_length=100)
    barcode: str | None = Field(None, max_length=100)
    price: Decimal | None = Field(None, ge=0, decimal_places=2)
    cost: Decimal | None = Field(None, ge=0, decimal_places=2)
    description: str | None = None
    image_url: str | None = Field(None, max_length=500)
    category_id: UUID | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category_id: UUID
    store_id: UUID
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    size: int
