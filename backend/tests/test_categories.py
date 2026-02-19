"""Unit tests for Category Management API."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from fastapi import HTTPException

from app.models.category import Category


@pytest.mark.asyncio
async def test_create_category_duplicate_name():
    """Creating category with existing name should fail."""
    from app.api.categories import create_category
    from app.schemas.category import CategoryCreate
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    # Mock existing category
    existing_category = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_category
    mock_db.execute.return_value = mock_result
    
    category_data = CategoryCreate(
        name="Electronics",
        description="Electronic products",
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await create_category(category_data, mock_user, mock_db)
    
    assert exc_info.value.status_code == 409
    assert "already exists" in str(exc_info.value.detail).lower()


@pytest.mark.asyncio
async def test_list_categories_filters_by_store():
    """List categories should only return items for current user's store."""
    from app.api.categories import list_categories
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    category = MagicMock()
    category.store_id = mock_user.store_id
    category.name = "Test Category"
    
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [category]
    mock_db.execute.return_value = mock_result
    
    result = await list_categories(
        current_user=mock_user,
        db=mock_db
    )
    
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_category_not_found():
    """Getting non-existent category should return 404."""
    from app.api.categories import get_category
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result
    
    fake_category_id = uuid.uuid4()
    
    with pytest.raises(HTTPException) as exc_info:
        await get_category(
            category_id=fake_category_id,
            current_user=mock_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_category():
    """Deleting category should work when exists."""
    from app.api.categories import delete_category
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.store_id = uuid.uuid4()
    
    mock_db = AsyncMock()
    
    category = MagicMock()
    category.id = uuid.uuid4()
    category.store_id = mock_user.store_id
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = category
    mock_db.execute.return_value = mock_result
    
    # Should not raise exception
    await delete_category(
        category_id=category.id,
        current_user=mock_user,
        db=mock_db
    )
    
    # Verify delete was called
    mock_db.delete.assert_called_once_with(category)
