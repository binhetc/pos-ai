"""
Unit tests for Receipt API endpoints.

Đặc biệt kiểm tra fix bug lazy-load trong async SQLAlchemy:
- Order.customer phải được selectinload trước khi truy cập
- OrderItem.product phải được selectinload trước khi truy cập
Không selectinload → MissingGreenlet / DetachedInstanceError trong async context.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch, call
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_order(
    *,
    store_id=None,
    customer=None,
    status=OrderStatus.COMPLETED,
    payment_method=PaymentMethod.CASH,
):
    """Tạo mock Order object cho testing."""
    order = MagicMock(spec=Order)
    order.id = uuid.uuid4()
    order.store_id = store_id or uuid.uuid4()
    order.order_number = "ORD-20260225120000"
    order.status = status
    order.payment_method = payment_method
    order.customer = customer
    order.subtotal = Decimal("100.00")
    order.tax_amount = Decimal("10.00")
    order.discount_amount = Decimal("0.00")
    order.total = Decimal("110.00")
    order.note = None

    from datetime import datetime
    order.created_at = datetime(2026, 2, 25, 12, 0, 0)
    return order


def _make_order_item(product_name="Test Product", price=Decimal("50.00"), qty=2):
    """Tạo mock OrderItem với product eagerly attached."""
    item = MagicMock(spec=OrderItem)
    item.quantity = qty
    item.unit_price = price
    item.subtotal = price * qty
    item.discount = Decimal("0.00")

    product = MagicMock()
    product.name = product_name
    item.product = product
    return item


def _make_store(name="Test Store"):
    """Tạo mock Store object."""
    store = MagicMock()
    store.name = name
    store.address = "123 Nguyen Hue, Q1, TP.HCM"
    store.phone = "0909123456"
    store.tax_id = "0123456789"
    return store


def _make_current_user(store_id=None):
    """Tạo mock CurrentUser."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.store_id = store_id or uuid.uuid4()
    user.full_name = "Nguyen Van A"
    return user


# ── Tests: eager loading (fix bug) ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_receipt_data_uses_selectinload_for_customer():
    """
    Đảm bảo query Order dùng selectinload(Order.customer).
    Thiếu selectinload → MissingGreenlet trong async SQLAlchemy.
    """
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    order_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    customer = MagicMock()
    customer.name = "Tran Thi B"
    customer.phone = "0908111222"

    order = _make_order(store_id=store_id, customer=customer)
    order.items = [_make_order_item()]

    store = _make_store()

    mock_db = AsyncMock()

    # Mock execute calls: 1st → Order query, 2nd → Store query
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order

    store_result = MagicMock()
    store_result.scalar_one.return_value = store

    mock_db.execute.side_effect = [order_result, store_result]

    result = await get_receipt_data(order_id, current_user, mock_db)

    # Verify relationships accessible (eager-loaded)
    assert result.customer_name == "Tran Thi B"
    assert result.customer_phone == "0908111222"
    assert result.store_name == "Test Store"
    assert len(result.items) == 1
    assert result.items[0].name == "Test Product"


@pytest.mark.asyncio
async def test_get_receipt_data_customer_none_does_not_raise():
    """Order không có customer → customer_name/phone trả về None, không raise."""
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    order_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    order = _make_order(store_id=store_id, customer=None)
    order.items = [_make_order_item()]
    store = _make_store()

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    store_result = MagicMock()
    store_result.scalar_one.return_value = store
    mock_db.execute.side_effect = [order_result, store_result]

    result = await get_receipt_data(order_id, current_user, mock_db)

    assert result.customer_name is None
    assert result.customer_phone is None


@pytest.mark.asyncio
async def test_get_receipt_data_multiple_items_all_loaded():
    """Nhiều items → tất cả product.name phải accessible (eager-loaded)."""
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    order_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    items = [
        _make_order_item("Coca Cola", Decimal("15000.00"), 3),
        _make_order_item("Banh mi", Decimal("25000.00"), 2),
        _make_order_item("Ca phe sua", Decimal("35000.00"), 1),
    ]
    order = _make_order(store_id=store_id, customer=None)
    order.items = items
    store = _make_store()

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    store_result = MagicMock()
    store_result.scalar_one.return_value = store
    mock_db.execute.side_effect = [order_result, store_result]

    result = await get_receipt_data(order_id, current_user, mock_db)

    assert len(result.items) == 3
    names = [i.name for i in result.items]
    assert "Coca Cola" in names
    assert "Banh mi" in names
    assert "Ca phe sua" in names


# ── Tests: error cases ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_receipt_data_order_not_found_raises_404():
    """Order không tồn tại → HTTPException 404."""
    from app.api.receipts import get_receipt_data

    current_user = _make_current_user()

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = order_result

    with pytest.raises(HTTPException) as exc_info:
        await get_receipt_data(uuid.uuid4(), current_user, mock_db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_receipt_data_voided_order_raises_400():
    """Order bị VOIDED → không thể in receipt → HTTPException 400."""
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    order = _make_order(store_id=store_id, status=OrderStatus.VOIDED)

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    mock_db.execute.return_value = order_result

    with pytest.raises(HTTPException) as exc_info:
        await get_receipt_data(uuid.uuid4(), current_user, mock_db)

    assert exc_info.value.status_code == 400
    assert "VOIDED" in exc_info.value.detail or "voided" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_receipt_data_payment_method_none_returns_na():
    """Order chưa có payment method → trả 'N/A' thay vì raise."""
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    order = _make_order(store_id=store_id, payment_method=None)
    order.items = [_make_order_item()]
    store = _make_store()

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    store_result = MagicMock()
    store_result.scalar_one.return_value = store
    mock_db.execute.side_effect = [order_result, store_result]

    result = await get_receipt_data(uuid.uuid4(), current_user, mock_db)

    assert result.payment_method == "N/A"


# ── Tests: receipt content ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_receipt_data_returns_correct_totals():
    """Totals phải match với Order data."""
    from app.api.receipts import get_receipt_data

    store_id = uuid.uuid4()
    current_user = _make_current_user(store_id=store_id)

    order = _make_order(store_id=store_id)
    order.subtotal = Decimal("200.00")
    order.tax_amount = Decimal("20.00")
    order.discount_amount = Decimal("10.00")
    order.total = Decimal("210.00")
    order.items = [_make_order_item("Product A", Decimal("100.00"), 2)]
    store = _make_store("TPPlaza Store")

    mock_db = AsyncMock()
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    store_result = MagicMock()
    store_result.scalar_one.return_value = store
    mock_db.execute.side_effect = [order_result, store_result]

    result = await get_receipt_data(uuid.uuid4(), current_user, mock_db)

    assert result.subtotal == Decimal("200.00")
    assert result.tax_amount == Decimal("20.00")
    assert result.discount_amount == Decimal("10.00")
    assert result.total == Decimal("210.00")
    assert result.store_name == "TPPlaza Store"
    assert result.cashier_name == "Nguyen Van A"
