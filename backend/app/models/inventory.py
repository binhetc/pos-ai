"""Inventory model."""

from sqlalchemy import Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class Inventory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("store_id", "product_id", name="uq_inventory_store_product"),
    )

    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reorder_quantity: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Foreign keys
    store_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Relationships
    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.low_stock_threshold

    def __repr__(self) -> str:
        return f"<Inventory store={self.store_id} product={self.product_id} qty={self.quantity}>"
