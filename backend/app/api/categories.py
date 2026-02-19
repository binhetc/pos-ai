"""Category CRUD endpoints with RBAC enforcement."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_permission
from app.db.base import get_db
from app.models.category import Category
from app.schemas.auth import CurrentUser
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all categories for the current store."""
    query = select(Category).where(
        Category.store_id == current_user.store_id
    ).order_by(Category.name)

    count_result = await db.execute(select(func.count()).select_from(Category).where(
        Category.store_id == current_user.store_id
    ))
    total = count_result.scalar_one()

    result = await db.execute(query)
    items = result.scalars().all()

    return CategoryListResponse(
        items=[CategoryResponse.model_validate(c) for c in items],
        total=total,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single category by ID."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.store_id == current_user.store_id,
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    return CategoryResponse.model_validate(category)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    current_user: CurrentUser = Depends(require_permission("product:create")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new category (requires product:create permission)."""
    # Check name uniqueness within store
    existing = await db.execute(
        select(Category).where(
            Category.store_id == current_user.store_id,
            Category.name == body.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists",
        )

    category = Category(
        **body.model_dump(),
        store_id=current_user.store_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)

    return CategoryResponse.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    current_user: CurrentUser = Depends(require_permission("product:update")),
    db: AsyncSession = Depends(get_db),
):
    """Update a category (requires product:update permission)."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.store_id == current_user.store_id,
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check name uniqueness if updating name
    if body.name and body.name != category.name:
        existing = await db.execute(
            select(Category).where(
                Category.store_id == current_user.store_id,
                Category.name == body.name,
                Category.id != category_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this name already exists",
            )

    # Update fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    return CategoryResponse.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current_user: CurrentUser = Depends(require_permission("product:delete")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a category (requires product:delete permission)."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.store_id == current_user.store_id,
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )

    # Check if category has products
    products_count = await db.execute(
        select(func.count()).select_from(category.products)
    )
    if products_count.scalar_one() > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete category with existing products",
        )

    await db.delete(category)
    await db.commit()
