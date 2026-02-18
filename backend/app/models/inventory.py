import uuid
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime, func, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InventoryAdjustment(Base):
    __tablename__ = "inventory_adjustments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"), nullable=False, index=True)
    quantity_change: Mapped[int] = mapped_column(Integer, nullable=False)  # positive = in, negative = out
    reason: Mapped[str] = mapped_column(String(50), nullable=False)  # purchase, sale, adjustment, damage, return
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship("Product", back_populates="inventory_adjustments")  # noqa: F821
