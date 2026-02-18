from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.product import Product
from app.models.inventory import InventoryAdjustment
from app.schemas.inventory import (
    InventoryAdjustRequest, InventoryAdjustmentResponse, InventoryHistoryResponse,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.post("/{product_id}/adjust", response_model=InventoryAdjustmentResponse, status_code=201)
async def adjust_inventory(
    product_id: str,
    data: InventoryAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    new_stock = product.in_stock + data.quantity_change
    if new_stock < 0:
        raise HTTPException(400, f"Insufficient stock. Current: {product.in_stock}, change: {data.quantity_change}")

    product.in_stock = new_stock

    adjustment = InventoryAdjustment(
        product_id=product_id,
        quantity_change=data.quantity_change,
        reason=data.reason,
        note=data.note,
        stock_after=new_stock,
    )
    db.add(adjustment)
    await db.flush()
    await db.refresh(adjustment)
    return adjustment


@router.get("/{product_id}/history", response_model=InventoryHistoryResponse)
async def get_inventory_history(
    product_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    query = (
        select(InventoryAdjustment)
        .where(InventoryAdjustment.product_id == product_id)
        .order_by(InventoryAdjustment.created_at.desc())
        .limit(limit)
    )
    adjustments = (await db.execute(query)).scalars().all()

    return InventoryHistoryResponse(
        items=adjustments,
        current_stock=product.in_stock,
        product_id=product_id,
    )
