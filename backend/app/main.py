from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import products, categories, inventory

app = FastAPI(
    title="POS AI API",
    description="Hệ thống bán hàng thông minh tích hợp AI - TPPlaza",
    version="0.1.0",
)

# CORS - restrict in production via env
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict to actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(inventory.router)

# Serve uploaded images
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
