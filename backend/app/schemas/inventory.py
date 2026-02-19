"""Inventory schemas for request/response."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class InventoryBase(BaseModel):
    """Base inventory schema with common fields."""
    quantity: int = Field(..., ge=0, description="Current stock quantity")
    low_stock_threshold: int = Field(10, ge=0, description="Alert when stock falls below this")
    reorder_quantity: int = Field(50, ge=1, description="Suggested reorder quantity")


class InventoryCreate(InventoryBase):
    """Schema for creating new inventory record."""
    product_id: UUID


class InventoryUpdate(BaseModel):
    """Schema for updating inventory settings (not quantity - use adjust for that)."""
    low_stock_threshold: int | None = Field(None, ge=0)
    reorder_quantity: int | None = Field(None, ge=1)


class InventoryAdjustment(BaseModel):
    """Schema for adjusting inventory quantity."""
    quantity_delta: int = Field(..., description="Change in quantity (positive=in, negative=out)")
    reason: str = Field(..., pattern="^(purchase|sale|adjustment|damage|return|transfer)$")
    note: str | None = Field(None, max_length=500)


class InventoryResponse(InventoryBase):
    """Schema for inventory response."""
    id: UUID
    product_id: UUID
    store_id: UUID
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryListResponse(BaseModel):
    """Paginated list of inventory items."""
    items: list[InventoryResponse]
    total: int
    page: int
    size: int


class LowStockResponse(BaseModel):
    """Response for low stock alerts."""
    items: list[InventoryResponse]
    count: int
