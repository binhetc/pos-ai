from fastapi import FastAPI

app = FastAPI(
    title="POS AI API",
    description="Hệ thống bán hàng thông minh tích hợp AI - TPPlaza",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
