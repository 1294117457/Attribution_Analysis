"""股票应用服务

用例编排：
- 查询股票列表 / 详情（简单版，DataCollect/StockManage 用）
- 新增 / 更新 / 删除股票
- 同步股票（从外部数据源全量导入）
- 元数据查询（枚举值）

面板列表面板（分页 + 4 表快照 + 池信息）已迁移至 application.panel_service.StockPanelAppService。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.stock import (
    StockDeleteResponse,
    StockItemResponse,
    StockListItemResponse,
    StockListResponse,
    StockMetaResponse,
    StockUpdateRequest,
    SyncStockResponse,
)
from application.exceptions import StockNotFoundError
from domain.stock_info.entity import StockInfo
from domain.stock_info.repository import StockInfoRepository
from infrastructure.collectors.interfaces import CollectParams
from infrastructure.collectors.protocols import StockBasicFetcher
from infrastructure.repositories.stock_repository import StockRepoImpl

logger = logging.getLogger(__name__)


class StockAppService:
    """股票应用服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockInfoRepository = StockRepoImpl(session)

    # ── 查询用例 ────────────────────────────────────────────

    async def list_stocks(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockListResponse:
        """查询所有股票列表（含K线统计，兼容旧接口）"""
        rows = await self._repo.list_with_kline_stats(
            industry=industry,
            market=market,
        )
        items = [StockListItemResponse(**row) for row in rows]
        return StockListResponse(
            total=len(items),
            page=1,
            page_size=len(items) or 1,
            items=items,
        )

    async def get_stock(self, symbol: str) -> StockItemResponse:
        """查询股票详情"""
        stock = await self._repo.find_by_symbol(symbol)
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
        meta = await self._repo.distinct_meta()
        return StockMetaResponse(
            industries=meta.get("industries", []),
            markets=meta.get("markets", []),
            exchanges=meta.get("exchanges", []),
        )

    # ── 写入用例 ────────────────────────────────────────────

    async def upsert_stock(
        self,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockItemResponse:
        """新增或更新股票（兼容旧接口）"""
        stock = StockInfo.create(
            symbol=symbol,
            name=name,
            industry=industry,
            market=market,
        )
        await self._repo.upsert(stock)

        return StockItemResponse(
            symbol=stock.symbol,
            name=stock.name,
            industry=industry,
            market=market,
        )

    async def update_stock(
        self, symbol: str, request: StockUpdateRequest
    ) -> StockItemResponse:
        """部分更新股票"""
        stock = await self._repo.find_by_symbol(symbol)
        if not stock:
            raise StockNotFoundError(symbol)

        if request.name is not None:
            stock.update_name(request.name)
        if request.industry is not None:
            stock.update_industry(request.industry)

        await self._repo.upsert(stock)

        return StockItemResponse(
            symbol=stock.symbol,
            name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.name if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )

    # ── 同步用例 ────────────────────────────────────────────

    async def sync_stocks(
        self,
        fetcher: StockBasicFetcher,
        list_status: str = "L",
    ) -> SyncStockResponse:
        """全量同步 A股 股票元数据

        从 Tushare stock_basic 获取所有上市股票，upsert 到数据库。
        返回同步条数与统计信息。
        """
        params = CollectParams(symbol=None, list_status=list_status)
        raw_data = await asyncio.to_thread(fetcher.fetch_stock_basic, params)
        if not raw_data:
            return SyncStockResponse(
                synced_count=0,
                inserted=0,
                updated=0,
                message="未获取到数据（可能是数据源未配置或无网络）",
            )

        # 转换为领域实体
        stocks: list[StockInfo] = []
        for data in raw_data:
            try:
                stock = data.to_entity()
                stocks.append(stock)
            except Exception as e:
                logger.warning("跳过无效股票数据: %s", e)

        if not stocks:
            return SyncStockResponse(
                synced_count=0,
                inserted=0,
                updated=0,
                message="数据解析后为空",
            )

        # 批量 upsert
        synced = await self._repo.bulk_upsert(stocks)

        return SyncStockResponse(
            synced_count=synced,
            inserted=synced,  # 简化：Tushare 全量同步视为全量写入
            updated=0,
            message=f"成功同步 {synced} 只股票（list_status={list_status}）",
        )

    # ── 删除用例 ────────────────────────────────────────────

    async def delete_stock(self, symbol: str) -> StockDeleteResponse:
        """删除股票"""
        success = await self._repo.delete(symbol)
        if not success:
            raise StockNotFoundError(symbol)
        return StockDeleteResponse(
            symbol=symbol,
            deleted_count=1,
            message=f"成功删除股票 {symbol}",
        )
