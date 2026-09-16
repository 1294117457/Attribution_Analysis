"""API 路由聚合"""

from fastapi import APIRouter

from route.api.v1.kline import router as kline_router
from route.api.v1.stock import router as stock_router
from route.api.v1.stock_analysis import router as stock_analysis_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(kline_router)
api_router.include_router(stock_router)
api_router.include_router(stock_analysis_router)