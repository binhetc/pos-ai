from datetime import datetime
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    sku: str = Field(..., min_length=1, max_length=50)
    barcode: str | None = Field(None, max_length=50)
    price: float = Field(..., gt=0)
    cost_price: float | None = Field(None, ge=0)
    unit: str = Field("cái", max_length=20)
    category_id: str | None = None
    in_stock: int = Field(0, ge=0)
    min_stock: int = Field(0, ge=0)


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    sku: str | None = Field(None, min_length=1, max_length=50)
    barcode: str | None = Field(None, max_length=50)
    price: float | None = Field(None, gt=0)
    cost_price: float | None = Field(None, ge=0)
    unit: str | None = Field(None, max_length=20)
    category_id: str | None = None
    is_active: bool | None = None
    min_stock: int | None = Field(None, ge=0)


class ProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    sku: str
    barcode: str | None
    price: float
    cost_price: float | None
    unit: str
    image_url: str | None
    in_stock: int
    min_stock: int
    is_active: bool
    category_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
