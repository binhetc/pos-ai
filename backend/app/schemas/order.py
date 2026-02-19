"""Order schemas for API request/response."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.order import OrderStatus, PaymentMethod


class OrderItemBase(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0, decimal_places=2)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    subtotal: Decimal = Field(..., ge=0, decimal_places=2)


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(..., gt=0)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class OrderItemResponse(OrderItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID


class OrderBase(BaseModel):
    subtotal: Decimal = Field(..., ge=0, decimal_places=2)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    total: Decimal = Field(..., ge=0, decimal_places=2)
    payment_method: PaymentMethod | None = None
    note: str | None = None


class OrderCreate(BaseModel):
    customer_id: UUID | None = None
    items: list[OrderItemCreate] = Field(..., min_length=1)
    tax_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    payment_method: PaymentMethod | None = None
    note: str | None = None


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    payment_method: PaymentMethod | None = None
    note: str | None = None


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    status: OrderStatus
    store_id: UUID
    cashier_id: UUID
    customer_id: UUID | None
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    size: int
