"""Inventory management endpoints with RBAC enforcement."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.auth import CurrentUser
from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
    InventoryAdjustment,
    InventoryResponse,
    InventoryListResponse,
    LowStockResponse,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_model=InventoryListResponse)
async def list_inventory(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    low_stock_only: bool = False,
    search: str | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List inventory items with pagination and optional filters."""
    offset = (page - 1) * size

    # Base query - filter by store, join with product for search
    query = (
        select(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.store_id == current_user.store_id)
    )

    # Apply filters
    if low_stock_only:
        query = query.where(Inventory.quantity <= Inventory.low_stock_threshold)
    
    if search:
        query = query.where(
            (Product.name.ilike(f"%{search}%"))
            | (Product.sku.ilike(f"%{search}%"))
            | (Product.barcode.ilike(f"%{search}%"))
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated items
    query = query.offset(offset).limit(size).order_by(Inventory.updated_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return InventoryListResponse(
        items=[InventoryResponse.model_validate(inv) for inv in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/low-stock", response_model=LowStockResponse)
async def get_low_stock_items(
    threshold: int | None = None,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all low stock items for alert purposes."""
    query = (
        select(Inventory)
        .join(Product, Inventory.product_id == Product.id)
        .where(Inventory.store_id == current_user.store_id)
    )
    
    if threshold is not None:
        query = query.where(Inventory.quantity <= threshold)
    else:
        query = query.where(Inventory.quantity <= Inventory.low_stock_threshold)
    
    query = query.order_by(Inventory.quantity.asc())
    result = await db.execute(query)
    items = result.scalars().all()

    return LowStockResponse(
        items=[InventoryResponse.model_validate(inv) for inv in items],
        count=len(items),
    )


@router.get("/{inventory_id}", response_model=InventoryResponse)
async def get_inventory(
    inventory_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single inventory record by ID."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.store_id == current_user.store_id,
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )

    return InventoryResponse.model_validate(inventory)


@router.get("/product/{product_id}", response_model=InventoryResponse)
async def get_inventory_by_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get inventory for a specific product in current store."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.product_id == product_id,
            Inventory.store_id == current_user.store_id,
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found for this product",
        )

    return InventoryResponse.model_validate(inventory)


@router.post("", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
async def create_inventory(
    body: InventoryCreate,
    current_user: CurrentUser = Depends(require_permission("inventory:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new inventory record (requires inventory:create permission)."""
    # Check if inventory already exists for this product in this store
    existing = await db.execute(
        select(Inventory).where(
            Inventory.store_id == current_user.store_id,
            Inventory.product_id == body.product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inventory record already exists for this product",
        )

    # Verify product exists
    product_check = await db.execute(
        select(Product).where(Product.id == body.product_id)
    )
    if not product_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    inventory = Inventory(
        **body.model_dump(),
        store_id=current_user.store_id,
    )
    db.add(inventory)
    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse.model_validate(inventory)


@router.patch("/{inventory_id}", response_model=InventoryResponse)
async def update_inventory(
    inventory_id: UUID,
    body: InventoryUpdate,
    current_user: CurrentUser = Depends(require_permission("inventory:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update inventory settings (thresholds, reorder qty) - requires inventory:update permission."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.store_id == current_user.store_id,
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(inventory, field, value)

    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse.model_validate(inventory)


@router.post("/{inventory_id}/adjust", response_model=InventoryResponse)
async def adjust_inventory(
    inventory_id: UUID,
    adjustment: InventoryAdjustment,
    current_user: CurrentUser = Depends(require_permission("inventory:adjust")),
    db: AsyncSession = Depends(get_db),
):
    """
    Adjust inventory quantity (stock in/out) - requires inventory:adjust permission.
    
    Use positive quantity_delta for stock in, negative for stock out.
    Reason: 'purchase', 'sale', 'adjustment', 'damage', 'return', 'transfer'
    """
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.store_id == current_user.store_id,
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )

    # Calculate new quantity
    new_quantity = inventory.quantity + adjustment.quantity_delta
    
    if new_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Current: {inventory.quantity}, requested: {abs(adjustment.quantity_delta)}",
        )

    inventory.quantity = new_quantity
    
    # TODO: Log adjustment to inventory_history table when implemented
    # For now, just update the quantity
    
    await db.commit()
    await db.refresh(inventory)

    return InventoryResponse.model_validate(inventory)


@router.delete("/{inventory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory(
    inventory_id: UUID,
    current_user: CurrentUser = Depends(require_permission("inventory:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete an inventory record (requires inventory:delete permission)."""
    result = await db.execute(
        select(Inventory).where(
            Inventory.id == inventory_id,
            Inventory.store_id == current_user.store_id,
        )
    )
    inventory = result.scalar_one_or_none()

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory record not found",
        )

    await db.delete(inventory)
    await db.commit()
