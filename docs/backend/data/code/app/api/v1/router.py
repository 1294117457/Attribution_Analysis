"""API v1 路由"""

from fastapi import APIRouter
from app.api.v1 import health, stocks

router = APIRouter()
router.include_router(health.router)
router.include_router(stocks.router)
