"""Product CRUD endpoints with RBAC enforcement."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.product import Product
from app.schemas.auth import CurrentUser
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
)

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    search: str | None = None,
    category_id: UUID | None = None,
    barcode: str | None = Query(None, description="Filter by exact barcode. Returns at most 1 matching product."),
    sku: str | None = Query(None, description="Filter by exact SKU. Returns at most 1 matching product."),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List products with pagination and optional search/filter.

    Use ``barcode`` or ``sku`` for exact-match barcode-scanner lookups.
    Use ``search`` for fuzzy name/SKU/barcode search.
    """
    offset = (page - 1) * size

    # Base query - filter by store
    query = select(Product).where(Product.store_id == current_user.store_id)

    # Exact-match filters (barcode scanner use-case)
    if barcode:
        query = query.where(Product.barcode == barcode)
    elif sku:
        query = query.where(Product.sku == sku)
    elif search:
        # Apply filters
        query = query.where(
            (Product.name.ilike(f"%{search}%"))
            | (Product.sku.ilike(f"%{search}%"))
            | (Product.barcode.ilike(f"%{search}%"))
        )
    if category_id:
        query = query.where(Product.category_id == category_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Get paginated items
    query = query.offset(offset).limit(size).order_by(Product.created_at.desc())
    result = await db.execute(query)
    items = result.scalars().all()

    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single product by ID."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == current_user.store_id,
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    return ProductResponse.model_validate(product)


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreate,
    current_user: CurrentUser = Depends(require_permission("product:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new product (requires product:create permission)."""
    # Check SKU uniqueness within store
    existing = await db.execute(
        select(Product).where(
            Product.store_id == current_user.store_id,
            Product.sku == body.sku,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product with this SKU already exists",
        )

    product = Product(
        **body.model_dump(),
        store_id=current_user.store_id,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdate,
    current_user: CurrentUser = Depends(require_permission("product:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a product (requires product:update permission)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == current_user.store_id,
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check SKU uniqueness if updating SKU
    if body.sku and body.sku != product.sku:
        existing = await db.execute(
            select(Product).where(
                Product.store_id == current_user.store_id,
                Product.sku == body.sku,
                Product.id != product_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this SKU already exists",
            )

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission("product:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a product (requires product:delete permission)."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.store_id == current_user.store_id,
        )
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    await db.delete(product)
    await db.commit()
