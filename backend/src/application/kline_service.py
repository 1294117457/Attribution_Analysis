"""K线应用服务

用例编排：
- 采集 K 线
- 查询 K 线
- 删除 K 线

应用层不包含业务逻辑，业务逻辑在领域层。
"""

from __future__ import annotations

from datetime import date
from typing import Optional

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
from domain.kline.repository import KlineRepository
from domain.kline.value_objects import StockCode
from domain.stock_info.repository import StockInfoRepository
from domain.stock_info.entity import StockInfo
from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl


class KlineAppService:
    """K线应用服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: KlineRepository = KlineRepoImpl(session)
        self._stock_repo: StockInfoRepository = StockRepoImpl(session)

    # ── 采集用例 ────────────────────────────────────────────

    async def collect(
        self,
        request: KlineCollectRequest,
        fetcher: FetcherProtocol,
    ) -> KlineCollectResponse:
        """采集 K 线用例"""
        try:
            params = CollectParams(
                symbol=request.symbol,
                days=request.days,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            raw_data = fetcher.fetch(params)

            if not raw_data:
                return KlineCollectResponse(
                    symbol=request.symbol,
                    name="",
                    saved_count=0,
                    total_count=0,
                    message="未获取到数据（代码无效或无交易记录）",
                )

            # 转换为领域实体
            klines = []
            name = ""
            for data in raw_data:
                kline = data.to_entity()
                klines.append(kline)
                if not name:
                    name = kline.name

            # 批量保存（使用 ON CONFLICT DO NOTHING 去重）
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
        """批量采集多只股票"""
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
            market=existing.market.code if existing and existing.market else None,
            list_date=existing.list_date if existing else None,
            total_shares=existing.total_shares if existing else None,
        )
        await self._stock_repo.upsert(stock)

    # ── 查询用例 ────────────────────────────────────────────

    async def get_klines(self, request: KlineQueryRequest) -> KlineListResponse:
        """查询K线用例"""
        stock_code = StockCode(request.symbol)
        klines = await self._repo.find_by_symbol(
            symbol=stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            limit=request.limit,
            order_desc=request.order_desc,
        )

        items = [
            KlineItemResponse(
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
            )
            for k in klines
        ]

        return KlineListResponse(total=len(items), items=items)

    async def get_kline_by_date(
        self, symbol: str, trade_date: date
    ) -> KlineItemResponse:
        """查询单条K线"""
        stock_code = StockCode(symbol)
        kline = await self._repo.find_by_symbol_date(stock_code, trade_date)

        if not kline:
            raise KlineNotFoundError(symbol, str(trade_date))

        return KlineItemResponse(
            symbol=kline.symbol.code,
            name=kline.name,
            date=kline.trade_date.date,
            open=kline.open,
            high=kline.high,
            low=kline.low,
            close=kline.close,
            volume=kline.volume,
            amount=kline.amount,
            change_pct=kline.change_pct,
        )

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
