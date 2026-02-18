"""Unit tests for Category schemas"""

import pytest
from datetime import datetime


def test_category_create_schema():
    from app.schemas.category import CategoryCreate

    c = CategoryCreate(name="Thời trang")
    assert c.name == "Thời trang"
    assert c.sort_order == 0

    with pytest.raises(Exception):
        CategoryCreate(name="")


def test_category_update_partial():
    from app.schemas.category import CategoryUpdate

    c = CategoryUpdate(name="Updated", color="#FF0000")
    data = c.model_dump(exclude_unset=True)
    assert "icon" not in data
    assert data["color"] == "#FF0000"


def test_category_response():
    from app.schemas.category import CategoryResponse

    c = CategoryResponse(
        id="cat-001", name="Đồ uống", description=None,
        icon="🥤", color="#00FF00", is_active=True, sort_order=1,
        created_at=datetime.now(), updated_at=datetime.now(),
    )
    assert c.icon == "🥤"
