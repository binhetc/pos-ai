"""Unit tests for Product Management API."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi import HTTPException

from app.models.product import Product


@pytest.mark.asyncio
async def test_create_product_duplicate_sku():
    """Creating product with existing SKU should fail."""
    from app.api.products import create_product
    from app.schemas.product import ProductCreate
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock existing product with same SKU
    existing_product = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_product
    mock_db.execute.return_value = mock_result
    
    product_data = ProductCreate(
        name="Test Product",
        sku="SKU-001",
        price=99.99,
        category_id=uuid.uuid4(),
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_product(product_data, mock_user, mock_db)
    
    assert exc_info.value.status_code == 409
    assert "sku" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_list_products_filters_by_store():
    """List products should only return items for current user's store."""
    from app.api.products import list_products
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock products
    product = MagicMock()
    product.store_id = mock_user.store_id
    product.name = "Test Product"
    
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 1
    
    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = [product]
    
    mock_db.execute.side_effect = [mock_count_result, mock_items_result]
    
    result = await list_products(
        page=1,
        size=50,
        search=None,
        category_id=None,
        current_user=mock_user,
        db=mock_db
    )
    
    assert result.total == 1
    assert result.page == 1


@pytest.mark.asyncio
async def test_get_product_not_found():
    """Getting non-existent product should return 404."""
    from app.api.products import get_product
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    fake_product_id = uuid.uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await get_product(
            product_id=fake_product_id,
            current_user=mock_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_update_product_sku_conflict():
    """Updating product with existing SKU should fail."""
    from app.api.products import update_product
    from app.schemas.product import ProductUpdate
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock current product
    current_product = MagicMock()
    current_product.id = uuid.uuid4()
    current_product.store_id = mock_user.store_id
    current_product.sku = "OLD-SKU"
    
    # Mock another product with the SKU we want to use
    conflicting_product = MagicMock()
    
    mock_result1 = MagicMock()
    mock_result1.scalar_one_or_none.return_value = current_product
    
    mock_result2 = MagicMock()
    mock_result2.scalar_one_or_none.return_value = conflicting_product
    
    mock_db.execute.side_effect = [mock_result1, mock_result2]
    
    update_data = ProductUpdate(sku="EXISTING-SKU")
    
    with pytest.raises(HTTPException) as exc_info:
        await update_product(
            product_id=current_product.id,
            body=update_data,
            current_user=mock_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 409


def test_product_permissions_in_rbac():
    """Verify product permissions are defined in RBAC."""
    from app.models.role import PermissionAction
    
    assert PermissionAction.PRODUCT_CREATE == "product:create"
    assert PermissionAction.PRODUCT_READ == "product:read"
    assert PermissionAction.PRODUCT_UPDATE == "product:update"
    assert PermissionAction.PRODUCT_DELETE == "product:delete"
