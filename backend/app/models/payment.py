import uuid
"""Payment & Transaction models."""

import enum
from decimal import Decimal

from sqlalchemy import String, Numeric, Enum, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class PaymentGateway(str, enum.Enum):
    CASH = "cash"
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    MOMO = "momo"
    VNPAY = "vnpay"
    ZALOPAY = "zalopay"


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order", "order_id"),
        Index("ix_payments_status_created", "status", "created_at"),
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gateway: Mapped[str] = mapped_column(Enum(PaymentGateway), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True
    )
    
    # Gateway transaction details
    transaction_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    gateway_response: Mapped[dict | None] = mapped_column(JSONB)
    
    # Additional info
    note: Mapped[str | None] = mapped_column(Text)
    reference: Mapped[str | None] = mapped_column(String(255))
    
    # Foreign keys
    order_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    store_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    processed_by: Mapped["uuid.UUID | None"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Relationships
    order = relationship("Order", back_populates="payments")
    store = relationship("Store", back_populates="payments")
    processor = relationship("User", back_populates="payments_processed")

    def __repr__(self) -> str:
        return f"<Payment {self.id} {self.gateway}={self.amount} status={self.status}>"
