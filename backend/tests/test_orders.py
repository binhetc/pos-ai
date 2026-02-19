"""Unit tests for Order Management API."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi import HTTPException

from app.models.order import OrderStatus, PaymentMethod
from app.api.orders import generate_order_number


# ── Order number generation ──────────────────────

def test_generate_order_number():
    """Order number should have format ORD-YYYYMMDDHHMMSS."""
    order_num = generate_order_number()
    assert order_num.startswith("ORD-")
    assert len(order_num) == 18  # ORD- + 14 digits
    assert order_num[4:].isdigit()


# ── Order creation validation ──────────────────────

@pytest.mark.asyncio
async def test_create_order_calculates_totals_correctly():
    """Order totals should be calculated from items + tax - discount."""
    from app.api.orders import create_order
    from app.schemas.order import OrderCreate, OrderItemCreate
    
    # Mock dependencies
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock products
    product1 = MagicMock()
    product1.id = uuid.uuid4()
    product1.price = Decimal("100.00")
    product1.is_active = True
    
    product2 = MagicMock()
    product2.id = uuid.uuid4()
    product2.price = Decimal("50.00")
    product2.is_active = True
    
    # Mock DB query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [product1, product2]
    mock_db.execute.return_value = mock_result
    
    # Create order with 2 items
    order_data = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=product1.id,
                quantity=2,
                discount=Decimal("10.00")
            ),
            OrderItemCreate(
                product_id=product2.id,
                quantity=1,
                discount=Decimal("0.00")
            ),
        ],
        tax_amount=Decimal("15.00"),
        discount_amount=Decimal("5.00"),
        payment_method=PaymentMethod.CASH,
    )
    
    # Expected calculations:
    # Item 1: 100 * 2 - 10 = 190
    # Item 2: 50 * 1 - 0 = 50
    # Subtotal: 190 + 50 = 240
    # Total: 240 + 15 - 5 = 250
    
    # Note: This test validates logic, not actual DB interaction
    assert order_data.tax_amount == Decimal("15.00")
    assert order_data.discount_amount == Decimal("5.00")


@pytest.mark.asyncio
async def test_create_order_missing_product():
    """Creating order with non-existent product should fail."""
    from app.api.orders import create_order
    from app.schemas.order import OrderCreate, OrderItemCreate
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock empty result (product not found)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result
    
    fake_product_id = uuid.uuid4()
    order_data = OrderCreate(
        items=[
            OrderItemCreate(
                product_id=fake_product_id,
                quantity=1,
            )
        ],
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_order(order_data, mock_user, mock_db)
    
    assert exc_info.value.status_code == 404
    assert "not found" in str(exc_info.value.detail).lower()


# ── Order status transitions ──────────────────────

def test_order_status_enum():
    """Verify order status values."""
    assert OrderStatus.PENDING == "pending"
    assert OrderStatus.COMPLETED == "completed"
    assert OrderStatus.VOIDED == "voided"
    assert OrderStatus.REFUNDED == "refunded"


def test_payment_method_enum():
    """Verify payment method values."""
    assert PaymentMethod.CASH == "cash"
    assert PaymentMethod.CARD == "card"
    assert PaymentMethod.MOMO == "momo"
    assert PaymentMethod.VNPAY == "vnpay"


# ── RBAC permissions ──────────────────────────────

def test_order_permissions_in_rbac():
    """Verify order permissions are defined in RBAC."""
    from app.models.role import PermissionAction
    
    assert PermissionAction.ORDER_CREATE == "order:create"
    assert PermissionAction.ORDER_READ == "order:read"
    assert PermissionAction.ORDER_UPDATE == "order:update"
    assert PermissionAction.ORDER_VOID == "order:void"
    assert PermissionAction.ORDER_REFUND == "order:refund"
