from sqlalchemy import Column, String, Integer, Float, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)  # emoji or icon name
    is_active = Column(Boolean, default=True, nullable=False)

    products = relationship("Product", back_populates="category", lazy="selectin")

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    name = Column(String(200), nullable=False)
    sku = Column(String(50), unique=True, nullable=False, index=True)
    barcode = Column(String(100), unique=True, nullable=True, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    cost_price = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Inventory
    stock_quantity = Column(Integer, default=0, nullable=False)
    low_stock_threshold = Column(Integer, default=10, nullable=False)

    category = relationship("Category", back_populates="products")
    inventory_logs = relationship("InventoryLog", back_populates="product", lazy="selectin")

    def __repr__(self):
        return f"<Product(id={self.id}, sku='{self.sku}', name='{self.name}')>"


class InventoryLog(TimestampMixin, Base):
    __tablename__ = "inventory_logs"

    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    change_quantity = Column(Integer, nullable=False)  # positive=in, negative=out
    reason = Column(String(200), nullable=False)  # sale, restock, adjustment, return
    reference_id = Column(String(100), nullable=True)  # order_id, etc.

    product = relationship("Product", back_populates="inventory_logs")
