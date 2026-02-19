from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.products import router as products_router
from app.api.categories import router as categories_router
from app.api.orders import router as orders_router

app = FastAPI(
    title="POS AI API",
    description="Hệ thống bán hàng thông minh tích hợp AI - TPPlaza",
    version="0.1.0",
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
