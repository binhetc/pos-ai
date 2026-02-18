from datetime import datetime
from pydantic import BaseModel, Field


class InventoryAdjustRequest(BaseModel):
    quantity_change: int = Field(..., description="Positive = stock in, negative = stock out")
    reason: str = Field(..., pattern="^(purchase|sale|adjustment|damage|return)$")
    note: str | None = None


class InventoryAdjustmentResponse(BaseModel):
    id: str
    product_id: str
    quantity_change: int
    reason: str
    note: str | None
    stock_after: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryHistoryResponse(BaseModel):
    items: list[InventoryAdjustmentResponse]
    current_stock: int
    product_id: str
