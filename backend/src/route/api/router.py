"""API 路由聚合"""

from fastapi import APIRouter

from route.api.v1.collect_task import router as collect_task_router
from route.api.v1.concept import router as concept_router
from route.api.v1.kline import router as kline_router
from route.api.v1.minute_kline import router as minute_kline_router
from route.api.v1.panel import router as panel_router
from route.api.v1.pool import router as pool_router
from route.api.v1.stock import router as stock_router
from route.api.v1.stock_analysis import router as stock_analysis_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(collect_task_router)
api_router.include_router(concept_router)
api_router.include_router(kline_router)
api_router.include_router(minute_kline_router)
api_router.include_router(panel_router)
api_router.include_router(pool_router)
api_router.include_router(stock_router)
api_router.include_router(stock_analysis_router)