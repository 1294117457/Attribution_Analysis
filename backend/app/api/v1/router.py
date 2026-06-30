"""API v1 路由汇总"""

from fastapi import APIRouter
from app.api.v1 import health, stocks

router = APIRouter()

router.include_router(health.router, tags=["健康检查"])
router.include_router(stocks.router, tags=["股票数据"])
