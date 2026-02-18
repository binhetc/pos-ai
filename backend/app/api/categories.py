from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    is_active: bool | None = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(Category).order_by(Category.sort_order, Category.name)
    if is_active is not None:
        query = query.where(Category.is_active == is_active)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(data: CategoryCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Category).where(Category.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Category '{data.name}' already exists")

    category = Category(**data.model_dump())
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(404, "Category not found")
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: str, data: CategoryUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(404, "Category not found")

    update_data = data.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != category.name:
        existing = await db.execute(select(Category).where(Category.name == update_data["name"]))
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Category '{update_data['name']}' already exists")

    for key, value in update_data.items():
        setattr(category, key, value)

    await db.flush()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(404, "Category not found")
    await db.delete(category)
    await db.flush()
