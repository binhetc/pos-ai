"""Unit tests for Inventory Management API."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi import HTTPException

from app.models.inventory import Inventory


# ── Inventory model properties ──────────────────────

def test_inventory_is_low_stock_property():
    """Inventory.is_low_stock should return True when quantity <= threshold."""
    inventory = Inventory(
        id=uuid.uuid4(),
        store_id=uuid.uuid4(),
        product_id=uuid.uuid4(),
        quantity=5,
        low_stock_threshold=10,
        reorder_quantity=50,
    )
    
    assert inventory.is_low_stock is True
    
    inventory.quantity = 15
    assert inventory.is_low_stock is False
    
    inventory.quantity = 10  # exactly at threshold
    assert inventory.is_low_stock is True


# ── Inventory list filtering ──────────────────────

@pytest.mark.asyncio
async def test_list_inventory_filters_by_store():
    """List inventory should only return items for current user's store."""
    from app.api.inventory import list_inventory
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock query results
    inv1 = MagicMock()
    inv1.store_id = mock_user.store_id
    inv1.quantity = 100
    
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1
    
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [inv1]
    
    mock_db.execute.side_effect = [mock_count_result, mock_items_result]
    
    result = await list_inventory(
        page=1,
        size=50,
        low_stock_only=False,
        search=None,
        current_user=mock_user,
        db=mock_db
    )
    
    assert result.total == 1
    assert result.page == 1


@pytest.mark.asyncio
async def test_list_inventory_low_stock_filter():
    """List inventory with low_stock_only=True should filter correctly."""
    from app.api.inventory import list_inventory
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock low stock item
    inv = MagicMock()
    inv.quantity = 5
    inv.low_stock_threshold = 10
    
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1
    
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [inv]
    
    mock_db.execute.side_effect = [mock_count_result, mock_items_result]
    
    result = await list_inventory(
        page=1,
        size=50,
        low_stock_only=True,
        search=None,
        current_user=mock_user,
        db=mock_db
    )
    
    assert result.total == 1


# ── Inventory adjustment ──────────────────────────

@pytest.mark.asyncio
async def test_adjust_inventory_stock_in():
    """Adjusting inventory with positive delta should increase quantity."""
    from app.api.inventory import adjust_inventory
    from app.schemas.inventory import InventoryAdjustment
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock inventory record
    inventory = MagicMock()
    inventory.id = uuid.uuid4()
    inventory.store_id = mock_user.store_id
    inventory.quantity = 50
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = inventory
    mock_db.execute.return_value = mock_result
    
    adjustment = InventoryAdjustment(
        quantity_delta=20,
        reason="purchase",
        note="Received new shipment"
    )
    
    result = await adjust_inventory(
        inventory_id=inventory.id,
        adjustment=adjustment,
        current_user=mock_user,
        db=mock_db
    )
    
    # Verify quantity increased
    assert inventory.quantity == 70  # 50 + 20


@pytest.mark.asyncio
async def test_adjust_inventory_stock_out():
    """Adjusting inventory with negative delta should decrease quantity."""
    from app.api.inventory import adjust_inventory
    from app.schemas.inventory import InventoryAdjustment
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    inventory = MagicMock()
    inventory.id = uuid.uuid4()
    inventory.store_id = mock_user.store_id
    inventory.quantity = 50
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = inventory
    mock_db.execute.return_value = mock_result
    
    adjustment = InventoryAdjustment(
        quantity_delta=-10,
        reason="sale",
        note="Sold 10 units"
    )
    
    result = await adjust_inventory(
        inventory_id=inventory.id,
        adjustment=adjustment,
        current_user=mock_user,
        db=mock_db
    )
    
    assert inventory.quantity == 40  # 50 - 10


@pytest.mark.asyncio
async def test_adjust_inventory_insufficient_stock():
    """Adjusting inventory below zero should raise error."""
    from app.api.inventory import adjust_inventory
    from app.schemas.inventory import InventoryAdjustment
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    inventory = MagicMock()
    inventory.id = uuid.uuid4()
    inventory.store_id = mock_user.store_id
    inventory.quantity = 5
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = inventory
    mock_db.execute.return_value = mock_result
    
    adjustment = InventoryAdjustment(
        quantity_delta=-10,  # More than available
        reason="sale",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await adjust_inventory(
            inventory_id=inventory.id,
            adjustment=adjustment,
            current_user=mock_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 400
    assert "insufficient stock" in str(exc_info.value.detail).lower()


# ── Create inventory ──────────────────────────────

@pytest.mark.asyncio
async def test_create_inventory_duplicate_product():
    """Creating inventory for existing product should fail."""
    from app.api.inventory import create_inventory
    from app.schemas.inventory import InventoryCreate
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock existing inventory
    existing_inv = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_inv
    mock_db.execute.return_value = mock_result
    
    inventory_data = InventoryCreate(
        product_id=uuid.uuid4(),
        quantity=100,
        low_stock_threshold=10,
        reorder_quantity=50,
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_inventory(inventory_data, mock_user, mock_db)
    
    assert exc_info.value.status_code == 409
    assert "already exists" in str(exc_info.value.detail).lower()


# ── Low stock alerts ──────────────────────────────

@pytest.mark.asyncio
async def test_get_low_stock_items():
    """Get low stock should return items below threshold."""
    from app.api.inventory import get_low_stock_items
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock low stock items
    inv1 = MagicMock()
    inv1.quantity = 3
    inv1.low_stock_threshold = 10
    
    inv2 = MagicMock()
    inv2.quantity = 1
    inv2.low_stock_threshold = 5
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [inv1, inv2]
    mock_db.execute.return_value = mock_result
    
    result = await get_low_stock_items(
        threshold=None,
        current_user=mock_user,
        db=mock_db
    )
    
    assert result.count == 2


# ── Inventory by product ──────────────────────────

@pytest.mark.asyncio
async def test_get_inventory_by_product_not_found():
    """Getting inventory for non-existent product should return 404."""
    from app.api.inventory import get_inventory_by_product
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    fake_product_id = uuid.uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await get_inventory_by_product(
            product_id=fake_product_id,
            current_user=mock_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 404


# ── RBAC permissions ──────────────────────────────

def test_inventory_permissions_in_rbac():
    """Verify inventory permissions are defined in RBAC."""
    from app.models.role import PermissionAction
    
    assert PermissionAction.INVENTORY_CREATE == "inventory:create"
    assert PermissionAction.INVENTORY_READ == "inventory:read"
    assert PermissionAction.INVENTORY_UPDATE == "inventory:update"
    assert PermissionAction.INVENTORY_ADJUST == "inventory:adjust"
    assert PermissionAction.INVENTORY_DELETE == "inventory:delete"
