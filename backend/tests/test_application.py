"""应用层单元测试

测试应用服务的用例编排，使用 mock 隔离仓储和采集器。
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from application.kline_service import KlineAppService
from application.exceptions import KlineNotFoundError
from application.dto.kline import (
    KlineCollectRequest,
    KlineQueryRequest,
    KlineDeleteRequest,
)
from domain.kline.schemas import KlineBO


def make_kline_bo(symbol: str = "000001", day: int = 1) -> KlineBO:
    return KlineBO(
        symbol=symbol,
        name="平安银行",
        trade_date=date(2024, 1, day),
        open=10.0,
        high=11.0,
        low=9.0,
        close=10.5,
        volume=1000,
        amount=10000,
        change_pct=5.0,
    )


class TestKlineAppService:
    def _make_service(self):
        session = MagicMock()
        service = KlineAppService(session=session)
        # Mock 仓储
        service._repo = MagicMock()
        service._stock_repo = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_collect_success(self):
        service = self._make_service()
        fetcher = MagicMock()
        fetcher.fetch.return_value = [make_kline_bo(day=1), make_kline_bo(day=2)]
        service._repo.save_batch = AsyncMock(return_value=2)
        service._stock_repo.find_by_symbol = AsyncMock(return_value=None)
        service._stock_repo.upsert = AsyncMock()

        request = KlineCollectRequest(symbol="000001", days=30)
        response = await service.collect(request, fetcher)

        assert response.symbol == "000001"
        assert response.name == "平安银行"
        assert response.saved_count == 2
        assert response.total_count == 2

    @pytest.mark.asyncio
    async def test_collect_no_data(self):
        service = self._make_service()
        fetcher = MagicMock()
        fetcher.fetch.return_value = []

        request = KlineCollectRequest(symbol="000001", days=30)
        response = await service.collect(request, fetcher)

        assert response.saved_count == 0
        assert response.total_count == 0

    @pytest.mark.asyncio
    async def test_get_klines(self):
        service = self._make_service()
        from domain.kline.entity import Kline
        k = Kline.create(
            symbol="000001", name="test", trade_date=date(2024, 1, 1),
            open=10, high=11, low=9, close=10.5,
            volume=1000, amount=10000,
        )
        service._repo.find_by_symbol = AsyncMock(return_value=[k])

        request = KlineQueryRequest(symbol="000001", limit=10)
        response = await service.get_klines(request)

        assert response.total == 1
        assert response.items[0].symbol == "000001"

    @pytest.mark.asyncio
    async def test_get_kline_by_date_not_found(self):
        service = self._make_service()
        service._repo.find_by_symbol_date = AsyncMock(return_value=None)

        with pytest.raises(KlineNotFoundError):
            await service.get_kline_by_date("000001", date(2024, 1, 1))

    @pytest.mark.asyncio
    async def test_delete_one(self):
        service = self._make_service()
        service._repo.delete_one = AsyncMock(return_value=1)

        request = KlineDeleteRequest(symbol="000001", trade_date=date(2024, 1, 1))
        response = await service.delete(request)

        assert response.deleted_count == 1

    @pytest.mark.asyncio
    async def test_delete_all(self):
        service = self._make_service()
        service._repo.delete_by_symbol = AsyncMock(return_value=100)

        request = KlineDeleteRequest(symbol="000001")
        response = await service.delete(request)

        assert response.deleted_count == 100
