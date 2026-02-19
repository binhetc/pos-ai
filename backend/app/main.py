from fastapi import FastAPI

from app.api.auth import router as auth_router

app = FastAPI(
    title="POS AI API",
    description="Hệ thống bán hàng thông minh tích hợp AI - TPPlaza",
    version="0.1.0",
)

app.include_router(auth_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
