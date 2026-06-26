"""
FastAPI 应用入口。
"""

from fastapi import FastAPI
from app.api.v1 import klines

app = FastAPI(title="Attribution Analysis API")

# 注册路由
app.include_router(klines.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "Attribution Analysis API", "docs": "/docs"}
