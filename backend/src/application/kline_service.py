"""K线应用服务

用例编排：
- 采集 K 线（采集时一并计算技术指标 — 方案 A）
- 查询 K 线
- 删除 K 线
- 单只股票指标重算

应用层不包含业务逻辑，业务逻辑在领域层。
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.kline import (
    KlineCollectRequest,
    KlineCollectResponse,
    KlineDeleteRequest,
    KlineDeleteResponse,
    KlineItemResponse,
    KlineListResponse,
    KlineQueryRequest,
    KlineStatsResponse,
)
from application.exceptions import CollectionError, KlineNotFoundError
from domain.kline.entity import Kline
from domain.kline.repository import KlineRepository
from domain.kline.value_objects import StockCode
from domain.stock_info.repository import StockInfoRepository
from domain.stock_info.entity import StockInfo
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.indicators import IndicatorCalculator
from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl


# 指标最大窗口：MA60 / BOLL20 / KDJ9 → 取 60 天作安全边界
INDICATOR_WINDOW = 60


class KlineAppService:
    """K线应用服务

    方案 A 实施要点：
    - K 线采集后立即调用 IndicatorCalculator 计算指标
    - 指标与 K 线一同 UPSERT 到 daily_klines（一次写入）
    - 提供 recalculate(symbol) 用于每日增量重算最近 N 天
    """

    def __init__(
        self,
        session: AsyncSession,
        indicator_calc: Optional[IndicatorCalculator] = None,
    ):
        self._session = session
        self._repo: KlineRepository = KlineRepoImpl(session)
        self._stock_repo: StockInfoRepository = StockRepoImpl(session)
        self._calc = indicator_calc or IndicatorCalculator()

    # ── 采集用例 ────────────────────────────────────────────

    async def collect(
        self,
        request: KlineCollectRequest,
        fetcher: FetcherProtocol,
    ) -> KlineCollectResponse:
        """采集 K 线 + 自动算指标"""
        try:
            params = CollectParams(
                symbol=request.symbol,
                days=request.days,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            raw_data = await asyncio.to_thread(fetcher.fetch, params)

            if not raw_data:
                return KlineCollectResponse(
                    symbol=request.symbol,
                    name="",
                    saved_count=0,
                    total_count=0,
                    message="未获取到数据（代码无效或无交易记录）",
                )

            klines: list[Kline] = []
            name = ""
            for data in raw_data:
                kline = data.to_entity()
                klines.append(kline)
                if not name:
                    name = kline.name

            # ── 核心：采集后立即计算指标（CPU密集，放入线程池避免阻塞事件循环）
            await asyncio.to_thread(self._enrich_with_indicators, request.symbol, klines)

            # 批量 UPSERT（含指标）
            saved_count = await self._repo.save_batch(klines)

            # 同步股票基本信息
            if name:
                await self._upsert_stock_info(request.symbol, name)

            return KlineCollectResponse(
                symbol=request.symbol,
                name=name,
                saved_count=saved_count,
                total_count=len(klines),
                message=f"成功采集 {saved_count} 条新数据（共获取 {len(klines)} 条）",
            )
        except Exception as e:
            raise CollectionError(request.symbol, str(e))

    async def collect_batch(
        self,
        symbols: list[str],
        days: int,
        fetcher: FetcherProtocol,
    ) -> dict[str, KlineCollectResponse]:
        """批量采集多只股票（每只的 K 线 + 指标一并入库）"""
        results: dict[str, KlineCollectResponse] = {}
        for symbol in symbols:
            try:
                request = KlineCollectRequest(symbol=symbol, days=days)
                response = await self.collect(request, fetcher)
                results[symbol] = response
            except Exception as e:
                results[symbol] = KlineCollectResponse(
                    symbol=symbol,
                    name="",
                    saved_count=-1,
                    total_count=0,
                    message=str(e),
                )
        return results

    async def _upsert_stock_info(self, symbol: str, name: str) -> None:
        """新增或更新股票基本信息"""
        existing = await self._stock_repo.find_by_symbol(symbol)
        stock = StockInfo.create(
            symbol=symbol,
            name=name,
            industry=existing.industry.name if existing and existing.industry else None,
            market=existing.market.name if existing and existing.market else None,
            area=existing.area if existing else None,
            exchange=existing.exchange if existing else None,
            list_date=existing.list_date if existing else None,
            delist_date=existing.delist_date if existing else None,
            list_status=existing.list_status if existing else None,
            is_hs=existing.is_hs if existing else None,
            total_shares=existing.total_shares if existing else None,
            ts_code=existing.ts_code if existing else None,
        )
        await self._stock_repo.upsert(stock)

    # ── 指标计算核心方法 ────────────────────────────────

    def _enrich_with_indicators(self, symbol: str, klines: list[Kline]) -> None:
        """给 K 线列表补齐指标字段

        步骤：
        1. 取出窗口数据：最近 INDICATOR_WINDOW + 拉取天数 天的 K 线（保证 MA60 窗口充足）
        2. 计算 DataFrame 上所有指标
        3. 按日期映射回 Kline 对象

        注意：K 线必须按日期升序（构造 DataFrame 前会排序）。
        """
        if not klines:
            return

        # 按日期升序（必要）
        klines.sort(key=lambda k: k.trade_date.date)

        df = pd.DataFrame([{
            "date":  k.trade_date.date,
            "close": k.close,
            "high":  k.high,
            "low":   k.low,
        } for k in klines])

        indicators = self._calc.calculate_all(df)

        # 按 date 索引 Kline 对象的快速 dict
        kline_by_date = {k.trade_date.date: k for k in klines}

        for idx, row in indicators.iterrows():
            d = row_idx_to_date(df, idx)
            if d is None or d not in kline_by_date:
                continue
            k = kline_by_date[d]
            k.ma5   = _safe_float(row.get("ma5"))
            k.ma10  = _safe_float(row.get("ma10"))
            k.ma20  = _safe_float(row.get("ma20"))
            k.ma60  = _safe_float(row.get("ma60"))
            k.ema12 = _safe_float(row.get("ema12"))
            k.ema26 = _safe_float(row.get("ema26"))
            k.macd_dif = _safe_float(row.get("macd_dif"))
            k.macd_dea = _safe_float(row.get("macd_dea"))
            k.macd_bar = _safe_float(row.get("macd_bar"))
            k.rsi6  = _safe_float(row.get("rsi6"))
            k.rsi12 = _safe_float(row.get("rsi12"))
            k.rsi24 = _safe_float(row.get("rsi24"))
            k.kdj_k = _safe_float(row.get("kdj_k"))
            k.kdj_d = _safe_float(row.get("kdj_d"))
            k.kdj_j = _safe_float(row.get("kdj_j"))
            k.boll_up  = _safe_float(row.get("boll_up"))
            k.boll_mid = _safe_float(row.get("boll_mid"))
            k.boll_dn  = _safe_float(row.get("boll_dn"))

    async def recalculate(
        self,
        symbol: str,
        days: int = INDICATOR_WINDOW,
    ) -> int:
        """增量重算最近 N 天指标

        用于：
        - 每日 15:10 定时任务（重算当天及之前 60 天）
        - 修复历史数据（管理员手动触发）

        返回受影响行数（UPSERT 后 rowcount）。
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days + INDICATOR_WINDOW)

        # 取窗口数据
        full_klines = await self._repo.find_by_symbol(
            symbol=StockCode(symbol),
            start_date=start_date,
            end_date=end_date,
            limit=days + INDICATOR_WINDOW + 30,
            order_desc=False,
        )

        if len(full_klines) < 2:
            return 0

        await asyncio.to_thread(self._enrich_with_indicators, symbol, full_klines)
        return await self._repo.save_batch(full_klines)

    async def recalculate_pool(
        self,
        symbols: list[str],
        days: int = INDICATOR_WINDOW,
    ) -> dict[str, int]:
        """批量重算池内股票指标（同步, < 10s 完成）

        取消原来的 indicator_calc 异步任务：单只重算 < 50ms,
        200 只股票 < 10s, 没必要走异步。
        """
        results: dict[str, int] = {}
        for sym in symbols:
            try:
                results[sym] = await self.recalculate(sym, days=days)
            except Exception as e:
                results[sym] = -1
        return results

    # ── 查询用例 ────────────────────────────────────────────

    async def get_klines(self, request: KlineQueryRequest) -> KlineListResponse:
        """查询K线用例（含指标字段）"""
        stock_code = StockCode(request.symbol)
        klines = await self._repo.find_by_symbol(
            symbol=stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            order_desc=request.order_desc,
        )

        items = [self._kline_to_item(k) for k in klines]

        return KlineListResponse(total=len(items), items=items)

    async def get_kline_by_date(
        self, symbol: str, trade_date: date
    ) -> KlineItemResponse:
        """查询单条K线"""
        stock_code = StockCode(symbol)
        kline = await self._repo.find_by_symbol_date(stock_code, trade_date)

        if not kline:
            raise KlineNotFoundError(symbol, str(trade_date))

        return self._kline_to_item(kline)

    async def get_stats(self, symbol: str) -> KlineStatsResponse:
        """获取 K 线统计"""
        stock_code = StockCode(symbol)
        count = await self._repo.count_by_symbol(stock_code)

        if count == 0:
            return KlineStatsResponse(symbol=symbol, name="", count=0)

        klines = await self._repo.find_by_symbol(
            symbol=stock_code,
            limit=1,
            order_desc=True,
        )

        if not klines:
            return KlineStatsResponse(symbol=symbol, name="", count=count)

        latest = klines[0]
        all_klines = await self._repo.find_by_symbol(
            symbol=stock_code,
            limit=count,
            order_desc=False,
        )
        if all_klines:
            start_date = all_klines[0].trade_date.date
            end_date = all_klines[-1].trade_date.date
        else:
            start_date = end_date = None

        return KlineStatsResponse(
            symbol=symbol,
            name=latest.name,
            count=count,
            start_date=start_date,
            end_date=end_date,
            latest_close=latest.close,
            latest_volume=latest.volume,
        )

    # ── 删除用例 ────────────────────────────────────────────

    async def delete(self, request: KlineDeleteRequest) -> KlineDeleteResponse:
        """删除 K 线用例"""
        stock_code = StockCode(request.symbol)

        if request.trade_date:
            deleted = await self._repo.delete_one(stock_code, request.trade_date)
            message = f"成功删除 {deleted} 条K线"
        else:
            deleted = await self._repo.delete_by_symbol(stock_code)
            message = f"成功删除股票 {request.symbol} 的全部 {deleted} 条K线"

        return KlineDeleteResponse(
            symbol=request.symbol,
            deleted_count=deleted,
            message=message,
        )

    # ── 内部：Kline → KlineItemResponse ──────────────────

    @staticmethod
    def _kline_to_item(k: Kline) -> KlineItemResponse:
        return KlineItemResponse(
            symbol=k.symbol.code,
            name=k.name,
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


# ── 工具函数 ──────────────────────────────────────────────

def _safe_float(v) -> Optional[float]:
    """Pandas NaN → None，规避 JSON 序列化失败"""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def row_idx_to_date(df: pd.DataFrame, idx) -> Optional[date]:
    """从 DataFrame 行索引拿到 date 列"""
    try:
        d = df.iloc[idx]["date"]
    except Exception:
        return None
    if isinstance(d, pd.Timestamp):
        return d.date()
    return d