"""股票信息应用服务（业务模块：stock-info/）

合并原 4 个 service：
- StockAppService（stock_app_service）    → 股票 CRUD + 元数据
- KlineAppService（kline_app_service）    → K 线采集 + 查询 + 指标
- StockAnalysisAppService                → 归因分析聚合视图
- StockPanelAppService                   → 列表分页面板（stock-panel/）

统一为 StockInfoService，依赖全部通过构造注入（DDD.md §4）。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from application.port.collector_port import (
    CollectParams,
    KlineFetcher,
    StockBasicFetcher,
)
from domain.entitys.kline.entity import CollectionError, Kline, KlineDataError, KlineNotFoundError
from domain.entitys.kline.repository import KlineRepository
from domain.entitys.kline.vo import StockCode
from domain.entitys.stock_info.entity import StockInfo, StockNotFoundError
from domain.entitys.stock_info.repository import StockInfoRepository
from domain.entitys.stock_pool.repository import StockPoolRepository
from domain.service import IndicatorCalculator
from domain.service.signal_detector import SignalDetector
from route.dto.request.kline import (
    KlineCollectRequest,
    KlineDeleteRequest,
    KlineQueryRequest,
)
from route.dto.request.stock import (
    StockDeleteResponse,
    StockItemResponse,
    StockListItemResponse,
    StockListResponse,
    StockMetaResponse,
    StockUpdateRequest,
    SyncStockResponse,
)
from route.dto.response.kline import (
    KlineCollectResponse,
    KlineDeleteResponse,
    KlineItemResponse,
    KlineListResponse,
    KlineStatsResponse,
)
from route.dto.response.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from route.dto.response.pool import PoolMembershipVO
from route.dto.response.stock_analysis import (
    KlineWithIndicatorVO,
    PoolMembershipVO as AnalysisPoolMembershipVO,
    StockAnalysisResponse,
    StockInfoVO,
    TechnicalSummaryVO,
)
from domain.entitys.concept.repository import ConceptRepository
from domain.entitys.concept.vo import ConceptBriefVO, ConceptMainVO
from domain.entitys.panel.repository import StockPanelComposeRepository
from domain.entitys.panel.vo import StockPanelRow
from domain.service import ConceptBriefService
from application.port.realtime_query_port import RealtimeQueryPort

logger = logging.getLogger(__name__)

# 指标最大窗口：MA60 / BOLL20 / KDJ9 → 取 60 天作安全边界
INDICATOR_WINDOW = 60

# 列表行内"主概念"列展示上限
DEFAULT_MAIN_CONCEPT_TOP_K = 3


class StockInfoService:
    """股票信息应用服务（CRUD + K 线 + 归因 + 面板）

    依赖（构造注入）：
    - stock_repo:        股票信息仓储
    - kline_repo:        K 线仓储
    - pool_repo:         股票池仓储（归因分析时反查）
    - panel_repo:        面板组合仓储
    - concept_repo:      概念仓储（面板主概念）
    - brief_service:     概念摘要服务（domain）
    - signal:            技术信号检测器
    - indicator_calc:    指标计算器
    - realtime:          实时行情（可选）
    """

    def __init__(
        self,
        *,
        stock_repo: StockInfoRepository,
        kline_repo: KlineRepository,
        pool_repo: StockPoolRepository,
        panel_repo: StockPanelComposeRepository,
        concept_repo: ConceptRepository,
        brief_service: ConceptBriefService,
        signal: Optional[SignalDetector] = None,
        indicator_calc: Optional[IndicatorCalculator] = None,
        realtime: Optional[RealtimeQueryPort] = None,
        top_k: int = DEFAULT_MAIN_CONCEPT_TOP_K,
    ):
        self._stock_repo = stock_repo
        self._kline_repo = kline_repo
        self._pool_repo = pool_repo
        self._panel_repo = panel_repo
        self._concept_repo = concept_repo
        self._brief_service = brief_service
        self._signal = signal or SignalDetector()
        self._calc = indicator_calc or IndicatorCalculator()
        self._realtime = realtime
        self._top_k = top_k

    # ══════════════════════════════════════════════════════════════════════
    # 股票 CRUD（原 StockAppService）
    # ══════════════════════════════════════════════════════════════════════

    async def list_stocks(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockListResponse:
        """查询所有股票列表（含K线统计，兼容旧接口）"""
        rows = await self._stock_repo.list_with_kline_stats(
            industry=industry, market=market,
        )
        items = [StockListItemResponse(**row) for row in rows]
        return StockListResponse(
            total=len(items), page=1,
            page_size=len(items) or 1, items=items,
        )

    async def get_stock(self, symbol: str) -> StockItemResponse:
        stock = await self._stock_repo.find_by_symbol(symbol)
        if not stock:
            raise StockNotFoundError(symbol)
        return StockItemResponse(
            symbol=stock.symbol,
            name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.name if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )

    async def get_meta(self) -> StockMetaResponse:
        """获取筛选下拉枚举值"""
        meta = await self._stock_repo.distinct_meta()
        return StockMetaResponse(
            industries=meta.get("industries", []),
            markets=meta.get("markets", []),
            exchanges=meta.get("exchanges", []),
        )

    async def upsert_stock(
        self,
        symbol: str, name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockItemResponse:
        stock = StockInfo.create(
            symbol=symbol, name=name, industry=industry, market=market,
        )
        await self._stock_repo.upsert(stock)
        return StockItemResponse(
            symbol=stock.symbol, name=stock.name,
            industry=industry, market=market,
        )

    async def update_stock(
        self, symbol: str, request: StockUpdateRequest
    ) -> StockItemResponse:
        stock = await self._stock_repo.find_by_symbol(symbol)
        if not stock:
            raise StockNotFoundError(symbol)
        if request.name is not None:
            stock.update_name(request.name)
        if request.industry is not None:
            stock.update_industry(request.industry)
        await self._stock_repo.upsert(stock)
        return StockItemResponse(
            symbol=stock.symbol, name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.name if stock.market else None,
            list_date=stock.list_date, total_shares=stock.total_shares,
        )

    async def sync_stocks(
        self, fetcher: StockBasicFetcher, list_status: str = "L",
    ) -> SyncStockResponse:
        """全量同步 A股 股票元数据"""
        params = CollectParams(symbol=None, list_status=list_status)
        raw_data = await asyncio.to_thread(fetcher.fetch_stock_basic, params)
        if not raw_data:
            return SyncStockResponse(
                synced_count=0, inserted=0, updated=0,
                message="未获取到数据（可能是数据源未配置或无网络）",
            )
        stocks: list[StockInfo] = []
        for data in raw_data:
            try:
                stocks.append(data.to_entity())
            except Exception as e:
                logger.warning("跳过无效股票数据: %s", e)
        if not stocks:
            return SyncStockResponse(
                synced_count=0, inserted=0, updated=0, message="数据解析后为空",
            )
        synced = await self._stock_repo.bulk_upsert(stocks)
        return SyncStockResponse(
            synced_count=synced, inserted=synced, updated=0,
            message=f"成功同步 {synced} 只股票（list_status={list_status}）",
        )

    async def delete_stock(self, symbol: str) -> StockDeleteResponse:
        success = await self._stock_repo.delete(symbol)
        if not success:
            raise StockNotFoundError(symbol)
        return StockDeleteResponse(
            symbol=symbol, deleted_count=1, message=f"成功删除股票 {symbol}",
        )

    # ══════════════════════════════════════════════════════════════════════
    # K 线（原 KlineAppService）
    # ══════════════════════════════════════════════════════════════════════

    async def collect(
        self, request: KlineCollectRequest, fetcher: KlineFetcher,
    ) -> KlineCollectResponse:
        """采集 K 线 + 自动算指标"""
        try:
            prefetched_name = await self._lookup_name(request.symbol)
            params = CollectParams(
                symbol=request.symbol, name=prefetched_name,
                days=request.days,
                start_date=request.start_date, end_date=request.end_date,
            )
            raw_data = await asyncio.to_thread(fetcher.fetch, params)
            if not raw_data:
                return KlineCollectResponse(
                    symbol=request.symbol, name="", saved_count=0, total_count=0,
                    message="未获取到数据（代码无效或无交易记录）",
                )
            klines: list[Kline] = []
            name = ""
            for data in raw_data:
                kline = data.to_entity()
                klines.append(kline)
                if not name:
                    name = kline.name
            await asyncio.to_thread(self._enrich_with_indicators, request.symbol, klines)
            saved_count = await self._kline_repo.save_batch(klines)
            if name:
                await self._upsert_stock_info(request.symbol, name)
            return KlineCollectResponse(
                symbol=request.symbol, name=name,
                saved_count=saved_count, total_count=len(klines),
                message=f"成功采集 {saved_count} 条新数据（共获取 {len(klines)} 条）",
            )
        except Exception as e:
            raise CollectionError(request.symbol, str(e))

    async def collect_batch(
        self, symbols: list[str], days: int, fetcher: KlineFetcher,
    ) -> dict[str, KlineCollectResponse]:
        results: dict[str, KlineCollectResponse] = {}
        for symbol in symbols:
            try:
                request = KlineCollectRequest(symbol=symbol, days=days)
                results[symbol] = await self.collect(request, fetcher)
            except Exception as e:
                results[symbol] = KlineCollectResponse(
                    symbol=symbol, name="", saved_count=-1, total_count=0, message=str(e),
                )
        return results

    async def _lookup_name(self, symbol: str) -> str:
        try:
            existing = await self._stock_repo.find_by_symbol(symbol)
            return existing.name if existing and existing.name else ""
        except Exception:
            return ""

    async def _upsert_stock_info(self, symbol: str, name: str) -> None:
        existing = await self._stock_repo.find_by_symbol(symbol)
        stock = StockInfo.create(
            symbol=symbol, name=name,
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

    def _enrich_with_indicators(self, symbol: str, klines: list[Kline]) -> None:
        """给 K 线列表补齐指标字段"""
        if not klines:
            return
        klines.sort(key=lambda k: k.trade_date.date)
        df = pd.DataFrame([{
            "date":  k.trade_date.date,
            "close": k.close,
            "high":  k.high,
            "low":   k.low,
        } for k in klines])
        indicators = self._calc.calculate_all(df)
        kline_by_date = {k.trade_date.date: k for k in klines}
        for idx, row in indicators.iterrows():
            d = _row_idx_to_date(df, idx)
            if d is None or d not in kline_by_date:
                continue
            k = kline_by_date[d]
            k.ma5 = _safe_float(row.get("ma5"))
            k.ma10 = _safe_float(row.get("ma10"))
            k.ma20 = _safe_float(row.get("ma20"))
            k.ma60 = _safe_float(row.get("ma60"))
            k.ema12 = _safe_float(row.get("ema12"))
            k.ema26 = _safe_float(row.get("ema26"))
            k.macd_dif = _safe_float(row.get("macd_dif"))
            k.macd_dea = _safe_float(row.get("macd_dea"))
            k.macd_bar = _safe_float(row.get("macd_bar"))
            k.rsi6 = _safe_float(row.get("rsi6"))
            k.rsi12 = _safe_float(row.get("rsi12"))
            k.rsi24 = _safe_float(row.get("rsi24"))
            k.kdj_k = _safe_float(row.get("kdj_k"))
            k.kdj_d = _safe_float(row.get("kdj_d"))
            k.kdj_j = _safe_float(row.get("kdj_j"))
            k.boll_up = _safe_float(row.get("boll_up"))
            k.boll_mid = _safe_float(row.get("boll_mid"))
            k.boll_dn = _safe_float(row.get("boll_dn"))

    async def recalculate(self, symbol: str, days: int = INDICATOR_WINDOW) -> int:
        """增量重算最近 N 天指标"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days + INDICATOR_WINDOW)
        full_klines = await self._kline_repo.find_by_symbol(
            symbol=StockCode(symbol),
            start_date=start_date, end_date=end_date,
            limit=days + INDICATOR_WINDOW + 30, order_desc=False,
        )
        if len(full_klines) < 2:
            return 0
        await asyncio.to_thread(self._enrich_with_indicators, symbol, full_klines)
        return await self._kline_repo.save_batch(full_klines)

    async def recalculate_pool(
        self, symbols: list[str], days: int = INDICATOR_WINDOW,
    ) -> dict[str, int]:
        results: dict[str, int] = {}
        for sym in symbols:
            try:
                results[sym] = await self.recalculate(sym, days=days)
            except Exception:
                results[sym] = -1
        return results

    async def get_klines(self, request: KlineQueryRequest) -> KlineListResponse:
        stock_code = StockCode(request.symbol)
        klines = await self._kline_repo.find_by_symbol(
            symbol=stock_code,
            start_date=request.start_date, end_date=request.end_date,
            limit=request.limit, order_desc=request.order_desc,
        )
        items = [self._kline_to_item(k) for k in klines]
        return KlineListResponse(total=len(items), items=items)

    async def get_kline_by_date(
        self, symbol: str, trade_date: date,
    ) -> KlineItemResponse:
        stock_code = StockCode(symbol)
        kline = await self._kline_repo.find_by_symbol_date(stock_code, trade_date)
        if not kline:
            raise KlineNotFoundError(symbol, str(trade_date))
        return self._kline_to_item(kline)

    async def get_stats(self, symbol: str) -> KlineStatsResponse:
        stock_code = StockCode(symbol)
        count = await self._kline_repo.count_by_symbol(stock_code)
        if count == 0:
            return KlineStatsResponse(symbol=symbol, name="", count=0)
        klines = await self._kline_repo.find_by_symbol(
            symbol=stock_code, limit=1, order_desc=True,
        )
        if not klines:
            return KlineStatsResponse(symbol=symbol, name="", count=count)
        latest = klines[0]
        all_klines = await self._kline_repo.find_by_symbol(
            symbol=stock_code, limit=count, order_desc=False,
        )
        if all_klines:
            start_date = all_klines[0].trade_date.date
            end_date = all_klines[-1].trade_date.date
        else:
            start_date = end_date = None
        return KlineStatsResponse(
            symbol=symbol, name=latest.name, count=count,
            start_date=start_date, end_date=end_date,
            latest_close=latest.close, latest_volume=latest.volume,
        )

    async def delete(self, request: KlineDeleteRequest) -> KlineDeleteResponse:
        stock_code = StockCode(request.symbol)
        if request.trade_date:
            deleted = await self._kline_repo.delete_one(stock_code, request.trade_date)
            message = f"成功删除 {deleted} 条K线"
        else:
            deleted = await self._kline_repo.delete_by_symbol(stock_code)
            message = f"成功删除股票 {request.symbol} 的全部 {deleted} 条K线"
        return KlineDeleteResponse(
            symbol=request.symbol, deleted_count=deleted, message=message,
        )

    @staticmethod
    def _kline_to_item(k: Kline) -> KlineItemResponse:
        return KlineItemResponse(
            symbol=k.symbol.code, name=k.name, date=k.trade_date.date,
            open=k.open, high=k.high, low=k.low, close=k.close,
            volume=k.volume, amount=k.amount, change_pct=k.change_pct,
            ma5=k.ma5, ma10=k.ma10, ma20=k.ma20, ma60=k.ma60,
            ema12=k.ema12, ema26=k.ema26,
            macd_dif=k.macd_dif, macd_dea=k.macd_dea, macd_bar=k.macd_bar,
            rsi6=k.rsi6, rsi12=k.rsi12, rsi24=k.rsi24,
            kdj_k=k.kdj_k, kdj_d=k.kdj_d, kdj_j=k.kdj_j,
            boll_up=k.boll_up, boll_mid=k.boll_mid, boll_dn=k.boll_dn,
        )

    # ══════════════════════════════════════════════════════════════════════
    # 归因分析（原 StockAnalysisAppService）
    # ══════════════════════════════════════════════════════════════════════

    async def build_analysis(self, symbol: str, days: int = 365) -> StockAnalysisResponse:
        """组装完整的股票分析数据"""
        stock_entity = await self._stock_repo.find_by_symbol(symbol)
        if stock_entity is None:
            raise StockNotFoundError(symbol)
        stock_info = StockInfoVO(
            symbol=stock_entity.symbol, name=stock_entity.name,
            industry=stock_entity.industry.name if stock_entity.industry else None,
            market=stock_entity.market.name if stock_entity.market else None,
        )
        end = date.today()
        start = end - timedelta(days=days)
        klines = await self._kline_repo.find_by_symbol(
            StockCode(symbol),
            start_date=start, end_date=end,
            limit=days + 30, order_desc=False,
        )
        if not klines:
            raise KlineDataError(symbol, f"暂无 K 线数据, 请先采集（days={days}）")
        summary_entity = self._signal.summarize(klines)
        summary = TechnicalSummaryVO(
            latest_close=summary_entity.latest_close,
            pct_change_1d=summary_entity.pct_change_1d,
            pct_change_30d=summary_entity.pct_change_30d,
            ma_alignment=summary_entity.ma_alignment,
            ma5=summary_entity.ma5, ma10=summary_entity.ma10,
            ma20=summary_entity.ma20, ma60=summary_entity.ma60,
            ma5_above_ma20=summary_entity.ma5_above_ma20,
            golden_cross_recent=summary_entity.golden_cross_recent,
            macd_status=summary_entity.macd_status,
            macd_dif=summary_entity.macd_dif, macd_dea=summary_entity.macd_dea, macd_bar=summary_entity.macd_bar,
            rsi6=summary_entity.rsi6, rsi_status=summary_entity.rsi_status,
            kdj_k=summary_entity.kdj_k, kdj_d=summary_entity.kdj_d, kdj_j=summary_entity.kdj_j,
            kdj_status=summary_entity.kdj_status,
            boll_up=summary_entity.boll_up, boll_mid=summary_entity.boll_mid, boll_dn=summary_entity.boll_dn,
            boll_position=summary_entity.boll_position,
            signals=summary_entity.signals,
        )
        pool_entities = await self._pool_repo.find_pools_by_symbol(symbol)
        pools = [
            AnalysisPoolMembershipVO(
                pool_id=p.id, pool_name=p.name, joined_at=None,
            )
            for p in pool_entities
        ]
        kline_vos = [self._analysis_kline_to_vo(k) for k in klines]
        return StockAnalysisResponse(
            stock=stock_info, summary=summary, klines=kline_vos, pools=pools,
        )

    @staticmethod
    def _analysis_kline_to_vo(k: Kline) -> KlineWithIndicatorVO:
        return KlineWithIndicatorVO(
            date=k.trade_date.date, open=k.open, high=k.high, low=k.low, close=k.close,
            volume=k.volume, amount=k.amount, change_pct=k.change_pct,
            ma5=k.ma5, ma10=k.ma10, ma20=k.ma20, ma60=k.ma60,
            ema12=k.ema12, ema26=k.ema26,
            macd_dif=k.macd_dif, macd_dea=k.macd_dea, macd_bar=k.macd_bar,
            rsi6=k.rsi6, rsi12=k.rsi12, rsi24=k.rsi24,
            kdj_k=k.kdj_k, kdj_d=k.kdj_d, kdj_j=k.kdj_j,
            boll_up=k.boll_up, boll_mid=k.boll_mid, boll_dn=k.boll_dn,
        )

    # ══════════════════════════════════════════════════════════════════════
    # 列表面板（原 StockPanelAppService）
    # ══════════════════════════════════════════════════════════════════════

    async def query_panels(self, req: StockPanelQueryRequest) -> StockPanelListVO:
        """分页 + 多维筛选 + 4 表快照 + 池信息 + 主概念"""
        rows, total = await self._panel_repo.list_paginated(
            q=req.q, industry=req.industry, market=req.market,
            exchange=req.exchange, is_hs=req.is_hs,
            list_status=req.list_status, exclude_st=req.exclude_st,
            min_total_mv=req.min_total_mv, with_pools=req.with_pools,
            page=req.page, page_size=req.page_size,
        )
        symbols = [r.symbol for r in rows]
        pool_map: dict[str, list[PoolMembershipVO]] = {}
        if req.with_pools and rows:
            pool_map = await self._panel_repo.list_membership_by_symbols(symbols)
        concept_map: dict[str, list[ConceptBriefVO]] = {}
        if req.with_concepts and rows and self._concept_repo is not None:
            concept_map = await self._panel_repo.list_concepts_by_symbols(symbols)
        main_concept_map = self._brief_service.build_main_concepts(concept_map, top_k=self._top_k)
        items = [
            _panel_row_to_vo(
                r,
                pool_map.get(r.symbol, []),
                main_concept_map.get(r.symbol, ([], 0)),
            )
            for r in rows
        ]
        return StockPanelListVO.from_list(items, total, req.page, req.page_size)


# ── 模块级工具函数（被 service 内部引用 + scheduler 复用） ────────────

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return float(v)


def _row_idx_to_date(df: pd.DataFrame, idx) -> Optional[date]:
    try:
        d = df.iloc[idx]["date"]
    except Exception:
        return None
    if isinstance(d, pd.Timestamp):
        return d.date()
    return d


def _panel_row_to_vo(
    r: StockPanelRow,
    pools: list[PoolMembershipVO],
    main_concepts_with_overflow: tuple[list[ConceptMainVO], int],
) -> StockPanelItemVO:
    main_concepts, overflow = main_concepts_with_overflow
    return StockPanelItemVO(
        symbol=r.symbol, ts_code=r.ts_code, name=r.name,
        area=r.area, industry=r.industry, market=r.market, exchange=r.exchange,
        list_date=r.list_date, list_status=r.list_status, is_hs=r.is_hs,
        act_name=r.act_name, act_ent_type=r.act_ent_type,
        total_shares=r.total_shares, record_count=r.record_count,
        kline_start=r.kline_start, kline_end=r.kline_end,
        latest_close=r.latest_close, total_mv=r.total_mv, pe_ttm=r.pe_ttm,
        profit_margin=(round(r.profit_margin, 2) if r.profit_margin is not None else None),
        pools=pools, concepts=main_concepts, concepts_overflow=overflow,
    )
