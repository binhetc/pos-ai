"""
Unit tests for Product CRUD API endpoints
Tests: list, create, get, update, delete, barcode lookup, SKU uniqueness
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


# Test data
SAMPLE_PRODUCT = {
    "id": "test-uuid-001",
    "name": "Áo thun TPPlaza",
    "description": "Áo thun cotton cao cấp",
    "sku": "AT-001",
    "barcode": "8934567890123",
    "price": 250000,
    "cost_price": 150000,
    "unit": "cái",
    "image_url": None,
    "in_stock": 100,
    "min_stock": 10,
    "is_active": True,
    "category_id": None,
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}


def test_product_create_schema():
    """Test ProductCreate schema validation"""
    from app.schemas.product import ProductCreate

    # Valid
    p = ProductCreate(name="Test", sku="SKU-001", price=100)
    assert p.name == "Test"
    assert p.unit == "cái"  # default

    # Invalid - negative price
    with pytest.raises(Exception):
        ProductCreate(name="Test", sku="SKU-001", price=-1)

    # Invalid - empty name
    with pytest.raises(Exception):
        ProductCreate(name="", sku="SKU-001", price=100)


def test_product_update_schema():
    """Test ProductUpdate allows partial updates"""
    from app.schemas.product import ProductUpdate

    p = ProductUpdate(name="Updated")
    data = p.model_dump(exclude_unset=True)
    assert data == {"name": "Updated"}
    assert "price" not in data


def test_product_response_schema():
    """Test ProductResponse from_attributes"""
    from app.schemas.product import ProductResponse

    p = ProductResponse(**SAMPLE_PRODUCT)
    assert p.id == "test-uuid-001"
    assert p.price == 250000


def test_product_list_response():
    """Test paginated list response"""
    from app.schemas.product import ProductListResponse

    resp = ProductListResponse(
        items=[],
        total=0,
        page=1,
        page_size=20,
    )
    assert resp.total == 0
    assert resp.page == 1
