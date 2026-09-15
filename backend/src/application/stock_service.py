"""股票应用服务

用例编排：
- 查询股票列表 / 详情
- 新增 / 更新 / 删除股票
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.stock import (
    StockDeleteResponse,
    StockItemResponse,
    StockListItemResponse,
    StockListResponse,
    StockUpdateRequest,
)
from application.exceptions import StockNotFoundError
from domain.stock_info.entity import StockInfo
from domain.stock_info.repository import StockInfoRepository
from infrastructure.repositories.stock_repository import StockRepoImpl


class StockAppService:
    """股票应用服务"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: StockInfoRepository = StockRepoImpl(session)

    async def list_stocks(
        self,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockListResponse:
        """查询所有股票列表（含K线统计）"""
        rows = await self._repo.list_with_kline_stats(
            industry=industry,
            market=market,
        )

        items = [StockListItemResponse(**row) for row in rows]
        return StockListResponse(total=len(items), items=items)

    async def get_stock(self, symbol: str) -> StockItemResponse:
        """查询股票详情"""
        stock = await self._repo.find_by_symbol(symbol)
        if not stock:
            raise StockNotFoundError(symbol)

        return StockItemResponse(
            symbol=stock.symbol,
            name=stock.name,
            industry=stock.industry.name if stock.industry else None,
            market=stock.market.code if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )

    async def upsert_stock(
        self,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
    ) -> StockItemResponse:
        """新增或更新股票"""
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
            market=stock.market.code if stock.market else None,
            list_date=stock.list_date,
            total_shares=stock.total_shares,
        )

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
