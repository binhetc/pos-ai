"""Unit tests for Inventory schemas"""

import pytest


def test_inventory_adjust_schema():
    from app.schemas.inventory import InventoryAdjustRequest

    adj = InventoryAdjustRequest(quantity_change=10, reason="purchase", note="Nhập kho")
    assert adj.quantity_change == 10

    with pytest.raises(Exception):
        InventoryAdjustRequest(quantity_change=5, reason="invalid_reason")


def test_inventory_response():
    from app.schemas.inventory import InventoryAdjustmentResponse
    from datetime import datetime

    resp = InventoryAdjustmentResponse(
        id="inv-001", product_id="prod-001",
        quantity_change=-5, reason="sale", note=None,
        stock_after=95, created_at=datetime.now(),
    )
    assert resp.stock_after == 95
