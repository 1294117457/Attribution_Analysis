"""股票信息应用服务（step7 重构：直接调 service，不走旧 gateway）"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

from contexts.market.domain.entities.kline.entity import CollectionError, Kline, KlineDataError, KlineNotFoundError
from contexts.market.domain.entities.kline.repository import KlineRepository
from contexts.market.domain.entities.kline.vo import IndicatorValues, StockCode
from contexts.market.domain.entities.stock_info.entity import StockInfo, StockNotFoundError
from contexts.market.domain.entities.stock_info.repository import StockInfoRepository
from contexts.user.domain.stock_pool.repository import StockPoolRepository
from contexts.market.domain.services.indicator_calculator import WARMUP_BARS, IndicatorCalculator
from contexts.market.domain.services.signal_detector import SignalDetector
from contexts.market.interface.dto.request.kline import (
    KlineCollectRequest,
    KlineDeleteRequest,
    KlineQueryRequest,
)
from contexts.market.interface.dto.request.stock import (
    StockDeleteResponse,
    StockItemResponse,
    StockListItemResponse,
    StockListResponse,
    StockMetaResponse,
    StockUpdateRequest,
    SyncStockResponse,
)
from contexts.market.interface.dto.response.kline import (
    KlineCollectResponse,
    KlineDeleteResponse,
    KlineItemResponse,
    KlineListResponse,
    KlineStatsResponse,
)
from contexts.market.interface.dto.response.panel import (
    StockPanelItemVO,
    StockPanelListVO,
    StockPanelQueryRequest,
)
from contexts.user.interface.dto.response.pool import PoolMembershipVO
from contexts.market.interface.dto.response.stock_analysis import (
    KlineWithIndicatorVO,
    PoolMembershipVO as AnalysisPoolMembershipVO,
    StockAnalysisResponse,
    StockInfoVO,
    TechnicalSummaryVO,
)
from contexts.concept.domain.repository import ConceptRepository
from contexts.concept.domain.vo import ConceptBriefVO, ConceptMainVO
from contexts.market.domain.entities.panel.repository import StockPanelComposeRepository
from contexts.market.domain.entities.panel.vo import StockPanelRow
from contexts.concept.domain.services.concept_brief_service import ConceptBriefService
from contexts.collect.application.service.fundamental.stock_basic_service import StockBasicService
from contexts.collect.application.service.tech.daily_service import DailyService
from contexts.collect.application.service.tech.minute_service import MinuteService

logger = logging.getLogger(__name__)

DEFAULT_MAIN_CONCEPT_TOP_K = 3


def _format_minute_bar(item: dict) -> dict:
    return {
        "datetime": item.get("datetime", ""),
        "interval": item.get("interval", ""),
        "open": item.get("open"),
        "high": item.get("high"),
        "low": item.get("low"),
        "close": item.get("close"),
        "volume": item.get("volume"),
        "amount": item.get("amount"),
    }


class StockInfoService:
    """股票信息应用服务（CRUD + K 线 + 归因 + 面板）

    step7：依赖注入改为
    - 直接持有各 CollectService 引用（不通过 gateway 多源切换）
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
        stock_basic_svc: Optional[StockBasicService] = None,
        daily_svc: Optional[DailyService] = None,
        minute_svc: Optional[MinuteService] = None,
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
        self._stock_basic_svc = stock_basic_svc
        self._daily_svc = daily_svc
        self._minute_svc = minute_svc
        self._top_k = top_k

    # ══════════════════════════════════════════════════════════════
    # 股票 CRUD
    # ══════════════════════════════════════════════════════════════

    async def list_stocks(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockListResponse:
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
        )

    async def get_meta(self) -> StockMetaResponse:
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
            list_date=stock.list_date,
        )

    async def sync_stocks(self, list_status: str = "L") -> SyncStockResponse:
        """全量同步 A股 股票元数据（直接调 StockBasicService）"""
        if self._stock_basic_svc is None:
            raise RuntimeError("StockInfoService 未注入 StockBasicService")
        result = await self._stock_basic_svc.collect({"list_status": list_status})
        return SyncStockResponse(
            synced_count=result.saved,
            inserted=result.saved,
            updated=0,
            message=result.message or f"成功同步 {result.saved} 只股票",
        )

    async def delete_stock(self, symbol: str) -> StockDeleteResponse:
        success = await self._stock_repo.delete(symbol)
        if not success:
            raise StockNotFoundError(symbol)
        return StockDeleteResponse(
            symbol=symbol, deleted_count=1, message=f"成功删除股票 {symbol}",
        )

    # ══════════════════════════════════════════════════════════════
    # K 线
    # ══════════════════════════════════════════════════════════════

    async def collect(self, request: KlineCollectRequest) -> KlineCollectResponse:
        """采集 K 线（直接调 DailyService.collect）"""
        if self._daily_svc is None:
            raise RuntimeError("StockInfoService 未注入 DailyService")
        try:
            params = {
                "symbol": request.symbol,
                "start_date": request.start_date.isoformat() if request.start_date else None,
                "end_date": request.end_date.isoformat() if request.end_date else None,
                "days": request.days,
            }
            params = {k: v for k, v in params.items() if v is not None}
            result = await self._daily_svc.collect(params)
            return KlineCollectResponse(
                symbol=request.symbol,
                name="",
                saved_count=result.saved,
                total_count=result.total,
                message=result.message,
            )
        except Exception as e:
            raise CollectionError(request.symbol, str(e))

    async def get_minute_klines(
        self, symbol: str, interval: str = "5min", days: int = 1,
    ) -> dict:
        """实时分 K（直接调 MinuteService）"""
        if self._minute_svc is None:
            raise RuntimeError("StockInfoService 未注入 MinuteService")
        items = await self._minute_svc.get(symbol, interval=interval, days=days)
        return {
            "total": len(items),
            "items": [_format_minute_bar(it) for it in items],
            "cached": False,
            "fetched_at": None,
        }

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
            ts_code=existing.ts_code if existing else None,
        )
        await self._stock_repo.upsert(stock)

    async def _load_klines_with_indicators(
        self,
        symbol: str,
        start_date: Optional[date],
        end_date: Optional[date],
        limit: int,
        order_desc: bool,
    ) -> list[tuple[Kline, IndicatorValues]]:
        code = StockCode(symbol)
        main = await self._kline_repo.find_by_symbol(
            code, start_date=start_date, end_date=end_date,
            limit=limit, order_desc=order_desc,
        )
        if not main:
            return []
        first_day = min(k.trade_date.date for k in main)
        warm = await self._kline_repo.find_by_symbol(
            code, end_date=first_day - timedelta(days=1),
            limit=WARMUP_BARS, order_desc=True,
        )
        series = sorted(warm + main, key=lambda k: k.trade_date.date)
        values = await asyncio.to_thread(self._calc.calculate, series)
        offset = len(warm)
        pairs = list(zip(series[offset:], values[offset:]))
        return list(reversed(pairs)) if order_desc else pairs

    async def get_klines(self, request: KlineQueryRequest) -> KlineListResponse:
        pairs = await self._load_klines_with_indicators(
            request.symbol, request.start_date, request.end_date,
            limit=request.limit, order_desc=request.order_desc,
        )
        items = [self._kline_to_item(k, ind) for k, ind in pairs]
        return KlineListResponse(total=len(items), items=items)

    async def get_tech_kline(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 250,
    ) -> list[tuple[Kline, IndicatorValues]]:
        return await self._load_klines_with_indicators(
            symbol, start_date, end_date, limit=limit, order_desc=True,
        )

    async def get_kline_by_date(
        self, symbol: str, trade_date: date,
    ) -> KlineItemResponse:
        pairs = await self._load_klines_with_indicators(
            symbol, trade_date, trade_date, limit=1, order_desc=False,
        )
        if not pairs:
            raise KlineNotFoundError(symbol, str(trade_date))
        kline, ind = pairs[0]
        return self._kline_to_item(kline, ind)

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
    def _kline_to_item(k: Kline, ind: IndicatorValues) -> KlineItemResponse:
        return KlineItemResponse(
            symbol=k.symbol.code, name=k.name, date=k.trade_date.date,
            open=k.open, high=k.high, low=k.low, close=k.close,
            volume=k.volume, amount=k.amount, change_pct=k.change_pct,
            **ind.to_dict(),
        )

    # ══════════════════════════════════════════════════════════════
    # 归因分析
    # ══════════════════════════════════════════════════════════════

    async def build_analysis(self, symbol: str, days: int = 365) -> StockAnalysisResponse:
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
        pairs = await self._load_klines_with_indicators(
            symbol, start, end, limit=days + 30, order_desc=False,
        )
        if not pairs:
            raise KlineDataError(symbol, f"暂无 K 线数据, 请先采集（days={days}）")
        klines = [k for k, _ in pairs]
        indicators = [ind for _, ind in pairs]
        summary_entity = self._signal.summarize(klines, indicators)
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
        kline_vos = [self._analysis_kline_to_vo(k, ind) for k, ind in pairs]
        return StockAnalysisResponse(
            stock=stock_info, summary=summary, klines=kline_vos, pools=pools,
        )

    @staticmethod
    def _analysis_kline_to_vo(k: Kline, ind: IndicatorValues) -> KlineWithIndicatorVO:
        return KlineWithIndicatorVO(
            date=k.trade_date.date, open=k.open, high=k.high, low=k.low, close=k.close,
            volume=k.volume, amount=k.amount, change_pct=k.change_pct,
            **ind.to_dict(),
        )

    # ══════════════════════════════════════════════════════════════
    # 列表面板
    # ══════════════════════════════════════════════════════════════

    async def query_panels(self, req: StockPanelQueryRequest) -> StockPanelListVO:
        rows, total = await self._panel_repo.list_paginated(
            q=req.q, industry=req.industry, market=req.market,
            exchange=req.exchange, is_hs=req.is_hs,
            list_status=req.list_status, exclude_st=req.exclude_st,
            min_total_mv=req.min_total_mv, concept_id=req.concept_id,
            with_pools=req.with_pools,
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


# ── 模块级工具函数 ────────────────────────────────────────────────

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
        record_count=r.record_count,
        kline_start=r.kline_start, kline_end=r.kline_end,
        latest_close=r.latest_close, total_mv=r.total_mv, pe_ttm=r.pe_ttm,
        profit_margin=(round(r.profit_margin, 2) if r.profit_margin is not None else None),
        pools=pools, concepts=main_concepts, concepts_overflow=overflow,
    )
