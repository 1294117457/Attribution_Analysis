"""股票归因分析 API（业务模块：stock-info/）

GET /stocks/{symbol}/analysis?days=365
→ 返回 stock + summary + klines（含指标） + pools
"""
from fastapi import APIRouter, Depends, Query

from application.service import StockInfoService
from infrastructure.config.di import get_stock_info_service
from route.api import _response as R

router = APIRouter(prefix="/stocks", tags=["AI 归因"])


@router.get(
    "/{symbol}/analysis",
    summary="股票归因分析（AI 入口）",
)
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=30, le=1825, description="回溯天数"),
    service: StockInfoService = Depends(get_stock_info_service),
):
    """给前端图表 + 后续 AI Agent 的统一入口。

    返回：
    - stock: 股票基本信息
    - summary: 技术形态摘要（后端算好金叉/超买/突破等）
    - klines: 每日 K 线 + 17 个指标列
    - pools: 所在操作池列表
    """
    result = await service.build_analysis(symbol=symbol, days=days)
    return R.ok(result.model_dump())
