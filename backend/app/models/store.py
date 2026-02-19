"""Store model."""

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class Store(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(20))
    tax_id: Mapped[str | None] = mapped_column(String(50), comment="Mã số thuế")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    users = relationship("User", back_populates="store", lazy="selectin")
    products = relationship("Product", back_populates="store", lazy="selectin")
    orders = relationship("Order", back_populates="store", lazy="selectin")
    inventory = relationship("Inventory", back_populates="store", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Store {self.code}: {self.name}>"
