"""股票归因分析 API

GET /stocks/{symbol}/analysis?days=365
→ 返回 stock + summary + klines（含指标） + pools
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.stock_analysis_service import StockAnalysisService
from infrastructure.database.connection import get_db
from route.schemas import response as R

router = APIRouter(prefix="/stocks", tags=["AI 归因"])


def get_analysis_service(
    db: AsyncSession = Depends(get_db),
) -> StockAnalysisService:
    return StockAnalysisService(session=db)


@router.get(
    "/{symbol}/analysis",
    summary="股票归因分析（AI 入口）",
)
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=30, le=1825, description="回溯天数"),
    service: StockAnalysisService = Depends(get_analysis_service),
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