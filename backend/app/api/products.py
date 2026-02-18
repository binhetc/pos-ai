import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.product import Product
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])

UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: str | None = None,
    search: str | None = None,
    is_active: bool | None = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(Product)
    count_query = select(func.count(Product.id))

    if is_active is not None:
        query = query.where(Product.is_active == is_active)
        count_query = count_query.where(Product.is_active == is_active)
    if category_id:
        query = query.where(Product.category_id == category_id)
        count_query = count_query.where(Product.category_id == category_id)
    if search:
        like = f"%{search}%"
        filter_cond = Product.name.ilike(like) | Product.sku.ilike(like)
        query = query.where(filter_cond)
        count_query = count_query.where(filter_cond)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Product.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    return ProductListResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductResponse, status_code=201)
async def create_product(data: ProductCreate, db: AsyncSession = Depends(get_db)):
    # Check unique SKU
    existing = await db.execute(select(Product).where(Product.sku == data.sku))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"SKU '{data.sku}' already exists")

    if data.barcode:
        existing_bc = await db.execute(select(Product).where(Product.barcode == data.barcode))
        if existing_bc.scalar_one_or_none():
            raise HTTPException(400, f"Barcode '{data.barcode}' already exists")

    product = Product(**data.model_dump())
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@router.get("/barcode/{barcode}", response_model=ProductResponse)
async def get_product_by_barcode(barcode: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.barcode == barcode))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: str, data: ProductUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    update_data = data.model_dump(exclude_unset=True)

    if "sku" in update_data and update_data["sku"] != product.sku:
        existing = await db.execute(select(Product).where(Product.sku == update_data["sku"]))
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"SKU '{update_data['sku']}' already exists")

    if "barcode" in update_data and update_data["barcode"] != product.barcode:
        existing = await db.execute(select(Product).where(Product.barcode == update_data["barcode"]))
        if existing.scalar_one_or_none():
            raise HTTPException(400, f"Barcode '{update_data['barcode']}' already exists")

    for key, value in update_data.items():
        setattr(product, key, value)

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")
    await db.delete(product)


@router.post("/{product_id}/image", response_model=ProductResponse)
async def upload_product_image(
    product_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Product not found")

    # Validate file type
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(400, f"File type not allowed. Use: {', '.join(allowed)}")

    # Save file
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    filename = f"{product_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = UPLOAD_DIR / filename

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(400, "File too large. Max 5MB")

    with open(filepath, "wb") as f:
        f.write(content)

    # Delete old image if exists
    if product.image_url:
        old_path = Path(product.image_url)
        if old_path.exists():
            os.remove(old_path)

    product.image_url = str(filepath)
    await db.flush()
    await db.refresh(product)
    return product
