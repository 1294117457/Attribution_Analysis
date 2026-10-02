"""股票归因分析 API

GET /stocks/{symbol}/analysis?days=365
→ 返回 stock + summary + klines（含指标） + pools
"""
from fastapi import APIRouter, Depends, Query

from application.service.stock_analysis_app_service import StockAnalysisAppService
from infrastructure.config.di import get_stock_analysis_app_service
from route.api import _response as R

router = APIRouter(prefix="/stocks", tags=["AI 归因"])


# ── 依赖注入工厂（来自 infrastructure.config.di） ──────────────────────────
get_analysis_service = get_stock_analysis_app_service


@router.get(
    "/{symbol}/analysis",
    summary="股票归因分析（AI 入口）",
)
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=30, le=1825, description="回溯天数"),
    service: StockAnalysisAppService = Depends(get_analysis_service),
):
    """给前端图表 + 后续 AI Agent 的统一入口。

    返回：
    - stock: 股票基本信息
    - summary: 技术形态摘要（后端算好金叉/超买/突破等）
    - klines: 每日 K 线 + 17 个指标列
    - pools: 所在操作池列表
    """
    result = await service.build(symbol=symbol, days=days)
    return R.ok(result.model_dump())