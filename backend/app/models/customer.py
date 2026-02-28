import uuid
"""Customer model."""

from sqlalchemy import String, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    address: Mapped[str | None] = mapped_column(Text)
    loyalty_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # AI: purchase behavior profile for recommendation engine
    ai_profile: Mapped[dict | None] = mapped_column(JSONB, default=None)

    # Relationships
    orders = relationship("Order", back_populates="customer", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"
