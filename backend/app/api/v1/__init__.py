"""API v1 路由"""

from fastapi import APIRouter

router = APIRouter()

from app.api.v1 import klines, news, analyze, symbols

router.include_router(klines.router, prefix="/klines", tags=["K线数据"])
router.include_router(news.router, prefix="/news", tags=["新闻数据"])
router.include_router(analyze.router, prefix="/analyze", tags=["分析服务"])
router.include_router(symbols.router, prefix="/symbols", tags=["股票列表"])
