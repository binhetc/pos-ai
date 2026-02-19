"""Role & Permission models - RBAC system."""

import enum

from sqlalchemy import String, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin, TimestampMixin


class PermissionAction(str, enum.Enum):
    """All permission actions in the POS system."""
    # Products
    PRODUCT_CREATE = "product:create"
    PRODUCT_READ = "product:read"
    PRODUCT_UPDATE = "product:update"
    PRODUCT_DELETE = "product:delete"
    # Orders
    ORDER_CREATE = "order:create"
    ORDER_READ = "order:read"
    ORDER_VOID = "order:void"
    ORDER_REFUND = "order:refund"
    # Inventory
    INVENTORY_READ = "inventory:read"
    INVENTORY_ADJUST = "inventory:adjust"
    # Reports
    REPORT_SALES = "report:sales"
    REPORT_INVENTORY = "report:inventory"
    REPORT_FINANCIAL = "report:financial"
    # Users
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    # Customers
    CUSTOMER_CREATE = "customer:create"
    CUSTOMER_READ = "customer:read"
    CUSTOMER_UPDATE = "customer:update"
    # Store settings
    STORE_SETTINGS = "store:settings"
    # AI features
    AI_RECOMMENDATIONS = "ai:recommendations"
    AI_FORECASTING = "ai:forecasting"
    AI_VISION = "ai:vision"


class RoleType(str, enum.Enum):
    OWNER = "owner"
    MANAGER = "manager"
    CASHIER = "cashier"


class Permission(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "permissions"

    action: Mapped[str] = mapped_column(
        Enum(PermissionAction), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(255))

    roles = relationship("RolePermission", back_populates="permission", lazy="selectin")


class Role(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        Enum(RoleType), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(String(255))

    users = relationship("User", back_populates="role", lazy="selectin")
    permissions = relationship("RolePermission", back_populates="role", lazy="selectin")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped["uuid.UUID"] = mapped_column(
        UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")
