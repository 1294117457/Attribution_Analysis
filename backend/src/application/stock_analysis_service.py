"""股票归因分析服务

聚合「股票档案」供前端图表 + 后续 AI Agent 一次性消费：
- 股票基本信息（StockInfo）
- K 线 + 17 个指标列（daily_klines）
- 技术形态摘要（SignalDetector 算好金叉/超买/突破等）
- 所在操作池列表

对应路由：GET /stocks/{symbol}/analysis?days=365
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.stock_analysis import (
    KlineWithIndicatorVO,
    PoolMembershipVO,
    StockAnalysisResponse,
    StockInfoVO,
    TechnicalSummaryVO,
)
from application.exceptions import StockNotFoundError, KlineDataError
from application.signals import SignalDetector
from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode
from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.pool_repository import StockPoolRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl


class StockAnalysisService:
    """AI 归因分析入口服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._stock_repo = StockRepoImpl(session)
        self._kline_repo = KlineRepoImpl(session)
        self._pool_repo = StockPoolRepoImpl(session)
        self._signal = SignalDetector()

    async def build(self, symbol: str, days: int = 365) -> StockAnalysisResponse:
        """组装完整的股票分析数据"""

        # 1) 股票基本信息
        stock_entity = await self._stock_repo.find_by_symbol(symbol)
        if stock_entity is None:
            raise StockNotFoundError(symbol)

        stock_info = StockInfoVO(
            symbol=stock_entity.symbol,
            name=stock_entity.name,
            industry=stock_entity.industry.name if stock_entity.industry else None,
            market=stock_entity.market.name if stock_entity.market else None,
        )

        # 2) K 线 + 指标（按日期升序，方便算信号）
        end = date.today()
        start = end - timedelta(days=days)
        klines = await self._kline_repo.find_by_symbol(
            StockCode(symbol),
            start_date=start,
            end_date=end,
            limit=days + 30,           # 多取一些防边界
            order_desc=False,           # 升序, SignalDetector 需要
        )
        if not klines:
            raise KlineDataError(symbol, f"暂无 K 线数据, 请先采集（days={days}）")

        # 3) 技术形态摘要
        summary_entity = self._signal.summarize(klines)
        summary = TechnicalSummaryVO(
            latest_close=summary_entity.latest_close,
            pct_change_1d=summary_entity.pct_change_1d,
            pct_change_30d=summary_entity.pct_change_30d,
            ma_alignment=summary_entity.ma_alignment,
            ma5=summary_entity.ma5,
            ma10=summary_entity.ma10,
            ma20=summary_entity.ma20,
            ma60=summary_entity.ma60,
            ma5_above_ma20=summary_entity.ma5_above_ma20,
            golden_cross_recent=summary_entity.golden_cross_recent,
            macd_status=summary_entity.macd_status,
            macd_dif=summary_entity.macd_dif,
            macd_dea=summary_entity.macd_dea,
            macd_bar=summary_entity.macd_bar,
            rsi6=summary_entity.rsi6,
            rsi_status=summary_entity.rsi_status,
            kdj_k=summary_entity.kdj_k,
            kdj_d=summary_entity.kdj_d,
            kdj_j=summary_entity.kdj_j,
            kdj_status=summary_entity.kdj_status,
            boll_up=summary_entity.boll_up,
            boll_mid=summary_entity.boll_mid,
            boll_dn=summary_entity.boll_dn,
            boll_position=summary_entity.boll_position,
            signals=summary_entity.signals,
        )

        # 4) 所在池（按 symbol 反查）
        pool_entities = await self._pool_repo.find_pools_by_symbol(symbol)
        pools = [
            PoolMembershipVO(
                pool_id=p.id,
                pool_name=p.name,
                joined_at=None,  # joined_at 需要查 StockPoolMemberDB; 暂留 None, 前端不强依赖
            )
            for p in pool_entities
        ]

        # 5) K 线 VO 列表
        kline_vos = [self._kline_to_vo(k) for k in klines]

        return StockAnalysisResponse(
            stock=stock_info,
            summary=summary,
            klines=kline_vos,
            pools=pools,
        )

    @staticmethod
    def _kline_to_vo(k: Kline) -> KlineWithIndicatorVO:
        return KlineWithIndicatorVO(
            date=k.trade_date.date,
            open=k.open,
            high=k.high,
            low=k.low,
            close=k.close,
            volume=k.volume,
            amount=k.amount,
            change_pct=k.change_pct,
            ma5=k.ma5,
            ma10=k.ma10,
            ma20=k.ma20,
            ma60=k.ma60,
            ema12=k.ema12,
            ema26=k.ema26,
            macd_dif=k.macd_dif,
            macd_dea=k.macd_dea,
            macd_bar=k.macd_bar,
            rsi6=k.rsi6,
            rsi12=k.rsi12,
            rsi24=k.rsi24,
            kdj_k=k.kdj_k,
            kdj_d=k.kdj_d,
            kdj_j=k.kdj_j,
            boll_up=k.boll_up,
            boll_mid=k.boll_mid,
            boll_dn=k.boll_dn,
        )