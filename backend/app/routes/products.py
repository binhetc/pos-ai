from fastapi import APIRouter, HTTPException, Query
from ..schemas.product import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductListResponse, InventoryAdjust,
)

router = APIRouter(prefix="/products", tags=["Products"])

_products: dict[int, dict] = {}
_prod_seq = 0


def _next_id():
    global _prod_seq
    _prod_seq += 1
    return _prod_seq


@router.get("/", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    search: str | None = None,
    barcode: str | None = None,
):
    from datetime import datetime
    items = [p for p in _products.values() if p.get("is_active", True)]
    if category_id:
        items = [p for p in items if p.get("category_id") == category_id]
    if search:
        q = search.lower()
        items = [p for p in items if q in p["name"].lower() or q in p.get("sku", "").lower()]
    if barcode:
        items = [p for p in items if p.get("barcode") == barcode]
    total = len(items)
    start = (page - 1) * page_size
    page_items = items[start:start + page_size]
    return ProductListResponse(
        items=[ProductResponse(**p, category=None) for p in page_items],
        total=total, page=page, page_size=page_size,
    )


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(payload: ProductCreate):
    from datetime import datetime
    # Check unique SKU
    for p in _products.values():
        if p["sku"] == payload.sku:
            raise HTTPException(409, f"SKU '{payload.sku}' already exists")
        if payload.barcode and p.get("barcode") == payload.barcode:
            raise HTTPException(409, f"Barcode '{payload.barcode}' already exists")
    now = datetime.utcnow()
    pid = _next_id()
    prod = {"id": pid, **payload.model_dump(), "is_active": True, "created_at": now, "updated_at": now}
    _products[pid] = prod
    return ProductResponse(**prod, category=None)


@router.get("/lookup/{barcode}", response_model=ProductResponse)
async def lookup_by_barcode(barcode: str):
    for p in _products.values():
        if p.get("barcode") == barcode and p.get("is_active", True):
            return ProductResponse(**p, category=None)
    raise HTTPException(404, "Product not found with this barcode")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    prod = _products.get(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    return ProductResponse(**prod, category=None)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(product_id: int, payload: ProductUpdate):
    from datetime import datetime
    prod = _products.get(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        prod[k] = v
    prod["updated_at"] = datetime.utcnow()
    return ProductResponse(**prod, category=None)


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: int):
    prod = _products.get(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    prod["is_active"] = False


@router.post("/{product_id}/inventory", response_model=ProductResponse)
async def adjust_inventory(product_id: int, payload: InventoryAdjust):
    from datetime import datetime
    prod = _products.get(product_id)
    if not prod:
        raise HTTPException(404, "Product not found")
    prod["stock_quantity"] = max(0, prod["stock_quantity"] + payload.change_quantity)
    prod["updated_at"] = datetime.utcnow()
    return ProductResponse(**prod, category=None)
