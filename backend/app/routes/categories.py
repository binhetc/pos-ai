from fastapi import APIRouter, HTTPException
from ..schemas.product import CategoryCreate, CategoryUpdate, CategoryResponse

router = APIRouter(prefix="/categories", tags=["Categories"])

# In-memory store (replace with DB session in production)
_categories: dict[int, dict] = {}
_cat_seq = 0


def _next_id():
    global _cat_seq
    _cat_seq += 1
    return _cat_seq


@router.get("/", response_model=list[CategoryResponse])
async def list_categories():
    from datetime import datetime
    return [
        CategoryResponse(
            id=c["id"], name=c["name"], description=c.get("description"),
            icon=c.get("icon"), is_active=c.get("is_active", True),
            created_at=c["created_at"], updated_at=c["updated_at"],
        )
        for c in _categories.values() if c.get("is_active", True)
    ]


@router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(payload: CategoryCreate):
    from datetime import datetime
    now = datetime.utcnow()
    cid = _next_id()
    cat = {"id": cid, **payload.model_dump(), "is_active": True, "created_at": now, "updated_at": now}
    _categories[cid] = cat
    return CategoryResponse(**cat)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: int):
    cat = _categories.get(category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    return CategoryResponse(**cat)


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(category_id: int, payload: CategoryUpdate):
    from datetime import datetime
    cat = _categories.get(category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        cat[k] = v
    cat["updated_at"] = datetime.utcnow()
    return CategoryResponse(**cat)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int):
    cat = _categories.get(category_id)
    if not cat:
        raise HTTPException(404, "Category not found")
    cat["is_active"] = False
