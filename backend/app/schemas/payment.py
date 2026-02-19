"""Payment schemas for API request/response."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.payment import PaymentStatus, PaymentGateway


class PaymentBase(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    gateway: PaymentGateway
    note: str | None = None
    reference: str | None = Field(None, max_length=255)


class PaymentCreate(PaymentBase):
    order_id: UUID


class PaymentUpdate(BaseModel):
    status: PaymentStatus | None = None
    transaction_id: str | None = Field(None, max_length=255)
    gateway_response: dict | None = None
    note: str | None = None


class PaymentResponse(PaymentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    store_id: UUID
    status: PaymentStatus
    transaction_id: str | None
    gateway_response: dict | None
    processed_by: UUID | None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    page: int
    size: int


class MoMoPaymentRequest(BaseModel):
    """MoMo payment gateway request."""
    order_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    order_info: str = Field(..., max_length=255)
    redirect_url: str | None = None
    ipn_url: str | None = None


class VNPayPaymentRequest(BaseModel):
    """VNPay payment gateway request."""
    order_id: UUID
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    order_info: str = Field(..., max_length=255)
    return_url: str | None = None
    ipn_url: str | None = None


class PaymentWebhookData(BaseModel):
    """Generic webhook data from payment gateways."""
    transaction_id: str
    status: str
    amount: Decimal
    raw_data: dict
