"""集成测试 - 需要真实数据库连接

测试仓储层（KlineRepoImpl、StockRepoImpl）的真实数据库操作。

运行：
    PYTHONPATH=src pytest tests/test_integration.py -v

注意：依赖 .env 中配置的远程数据库（iddata_test）。
"""

from __future__ import annotations

from datetime import date
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from infrastructure.config import get_settings
from infrastructure.database.base import Base
from infrastructure.database.models.kline import DailyKlineDB
from infrastructure.database.models.stock_info import StockInfoDB
from infrastructure.repositories.kline_repository import KlineRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl

from domain.kline.entity import Kline
from domain.kline.value_objects import StockCode
from domain.stock_info.entity import StockInfo


# ════════════════════════════════════════════════════════════════
# 每个测试一个独立的事件循环 + 独立引擎（避免连接泄漏）
# ════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture(scope="function")
async def engine():
    """每个测试用新的引擎和 NullPool（不连接池）"""
    settings = get_settings()
    eng = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """每个测试使用独立的 session，结束后清理数据"""
    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as s:
        yield s
        # 清理测试数据
        try:
            await s.execute(DailyKlineDB.__table__.delete())
            await s.execute(StockInfoDB.__table__.delete())
            await s.commit()
        except Exception:
            pass


@pytest_asyncio.fixture(scope="function")
async def kline_repo(session) -> KlineRepoImpl:
    return KlineRepoImpl(session)


@pytest_asyncio.fixture(scope="function")
async def stock_repo(session) -> StockRepoImpl:
    return StockRepoImpl(session)


def make_kline(symbol: str = "000001", day: int = 1) -> Kline:
    return Kline.create(
        symbol=symbol,
        name="测试股票",
        trade_date=date(2024, 1, day),
        open=10.0,
        high=11.0,
        low=9.0,
        close=10.5,
        volume=1000,
        amount=10000,
        change_pct=5.0,
    )


def make_stock(symbol: str = "000001") -> StockInfo:
    return StockInfo.create(
        symbol=symbol,
        name="平安银行",
        industry="银行",
        market="SZ",
    )


# ════════════════════════════════════════════════════════════════
# KlineRepoImpl 测试
# ════════════════════════════════════════════════════════════════

class TestKlineRepository:
    @pytest.mark.asyncio
    async def test_save_single(self, kline_repo):
        """保存单条 K 线"""
        kline = make_kline(day=1)
        result = await kline_repo.save(kline)

        assert result.id > 0
        assert result.symbol.code == "000001"

    @pytest.mark.asyncio
    async def test_save_batch_no_conflict(self, kline_repo):
        """批量保存无冲突"""
        klines = [make_kline(day=i) for i in range(1, 6)]
        count = await kline_repo.save_batch(klines)

        assert count == 5

    @pytest.mark.asyncio
    async def test_save_batch_with_conflict(self, kline_repo):
        """批量保存有冲突时只插入新数据"""
        # 第一次：插入 day 1-5
        klines = [make_kline(day=i) for i in range(1, 6)]
        first_count = await kline_repo.save_batch(klines)
        assert first_count == 5

        # 第二次：插入 day 4-8（其中 day 4、5 重复，6、7、8 是新的）
        new_klines = [make_kline(day=i) for i in range(4, 9)]
        second_count = await kline_repo.save_batch(new_klines)
        assert second_count == 3

        # 验证总数
        total = await kline_repo.count_by_symbol(StockCode("000001"))
        assert total == 8

    @pytest.mark.asyncio
    async def test_find_by_id(self, kline_repo):
        klines = [make_kline(day=i) for i in range(1, 4)]
        await kline_repo.save_batch(klines)

        # 先找到任意一条的 id（id 可能不连续，不假设 id=1）
        results = await kline_repo.find_by_symbol(
            klines[0].symbol, limit=1, order_desc=True
        )
        assert len(results) == 1
        target_id = results[0].id

        first = await kline_repo.find_by_id(target_id)
        assert first is not None
        assert first.symbol.code == "000001"
        assert first.trade_date.date == date(2024, 1, 3)

    @pytest.mark.asyncio
    async def test_find_by_symbol_date(self, kline_repo):
        klines = [make_kline(day=i) for i in range(1, 4)]
        await kline_repo.save_batch(klines)

        result = await kline_repo.find_by_symbol_date(StockCode("000001"), date(2024, 1, 2))
        assert result is not None
        assert result.trade_date.date == date(2024, 1, 2)

    @pytest.mark.asyncio
    async def test_find_by_symbol_desc(self, kline_repo):
        """按日期降序查询"""
        klines = [make_kline(day=i) for i in range(1, 6)]
        await kline_repo.save_batch(klines)

        results = await kline_repo.find_by_symbol(
            StockCode("000001"),
            order_desc=True,
            limit=3,
        )
        assert len(results) == 3
        assert results[0].trade_date.date == date(2024, 1, 5)

    @pytest.mark.asyncio
    async def test_find_by_symbol_with_date_range(self, kline_repo):
        """带日期范围查询"""
        klines = [make_kline(day=i) for i in range(1, 11)]
        await kline_repo.save_batch(klines)

        results = await kline_repo.find_by_symbol(
            StockCode("000001"),
            start_date=date(2024, 1, 3),
            end_date=date(2024, 1, 7),
            order_desc=False,
        )
        assert len(results) == 5
        assert results[0].trade_date.date == date(2024, 1, 3)
        assert results[-1].trade_date.date == date(2024, 1, 7)

    @pytest.mark.asyncio
    async def test_count_by_symbol(self, kline_repo):
        klines = [make_kline(day=i) for i in range(1, 6)]
        await kline_repo.save_batch(klines)

        count = await kline_repo.count_by_symbol(StockCode("000001"))
        assert count == 5

        count = await kline_repo.count_by_symbol(StockCode("999999"))
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_by_symbol(self, kline_repo):
        klines = [make_kline(day=i) for i in range(1, 6)]
        await kline_repo.save_batch(klines)

        deleted = await kline_repo.delete_by_symbol(StockCode("000001"))
        assert deleted == 5

        count = await kline_repo.count_by_symbol(StockCode("000001"))
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_one(self, kline_repo):
        klines = [make_kline(day=i) for i in range(1, 4)]
        await kline_repo.save_batch(klines)

        deleted = await kline_repo.delete_one(StockCode("000001"), date(2024, 1, 2))
        assert deleted == 1

        count = await kline_repo.count_by_symbol(StockCode("000001"))
        assert count == 2


# ════════════════════════════════════════════════════════════════
# StockRepoImpl 测试
# ════════════════════════════════════════════════════════════════

class TestStockRepository:
    @pytest.mark.asyncio
    async def test_upsert_insert(self, stock_repo):
        """新增股票"""
        stock = make_stock()
        await stock_repo.upsert(stock)

        found = await stock_repo.find_by_symbol("000001")
        assert found is not None
        assert found.name == "平安银行"
        assert found.industry.name == "银行"

    @pytest.mark.asyncio
    async def test_upsert_update(self, stock_repo):
        """upsert 更新现有股票"""
        stock1 = make_stock()
        await stock_repo.upsert(stock1)

        stock2 = StockInfo.create(symbol="000001", name="新名字", industry="科技", market="SZ")
        await stock_repo.upsert(stock2)

        found = await stock_repo.find_by_symbol("000001")
        assert found.name == "新名字"
        assert found.industry.name == "科技"

    @pytest.mark.asyncio
    async def test_find_all(self, stock_repo):
        await stock_repo.upsert(make_stock("000001"))
        await stock_repo.upsert(make_stock("000002"))
        await stock_repo.upsert(make_stock("600000"))

        stocks = await stock_repo.find_all()
        assert len(stocks) == 3

    @pytest.mark.asyncio
    async def test_find_by_industry(self, stock_repo):
        bank = StockInfo.create(symbol="000001", name="A", industry="银行", market="SZ")
        tech = StockInfo.create(symbol="000002", name="B", industry="科技", market="SZ")
        await stock_repo.upsert(bank)
        await stock_repo.upsert(tech)

        banks = await stock_repo.find_all(industry="银行")
        assert len(banks) == 1
        assert banks[0].symbol == "000001"

    @pytest.mark.asyncio
    async def test_delete(self, stock_repo):
        await stock_repo.upsert(make_stock())

        success = await stock_repo.delete("000001")
        assert success is True

        not_found = await stock_repo.delete("000001")
        assert not_found is False

    @pytest.mark.asyncio
    async def test_list_with_kline_stats(self, stock_repo, kline_repo):
        """联表查询 - 股票 + K线统计"""
        await stock_repo.upsert(make_stock("000001"))
        await stock_repo.upsert(make_stock("000002"))

        klines = [make_kline("000001", day=i) for i in range(1, 6)]
        await kline_repo.save_batch(klines)

        rows = await stock_repo.list_with_kline_stats()
        assert len(rows) == 2

        row_001 = next(r for r in rows if r["symbol"] == "000001")
        assert row_001["name"] == "平安银行"
        assert row_001["record_count"] == 5
        assert row_001["kline_start"] == date(2024, 1, 1)
        assert row_001["kline_end"] == date(2024, 1, 5)


# ════════════════════════════════════════════════════════════════
# 完整流程测试
# ════════════════════════════════════════════════════════════════

class TestFullFlow:
    @pytest.mark.asyncio
    async def test_kline_and_stock_workflow(self, kline_repo, stock_repo):
        """完整流程：股票 + K 线管理"""
        # 1. 注册股票
        stock = StockInfo.create(
            symbol="600519",
            name="贵州茅台",
            industry="白酒",
            market="SH",
        )
        await stock_repo.upsert(stock)

        # 2. 插入 K 线
        klines = [make_kline("600519", day=i) for i in range(1, 11)]
        await kline_repo.save_batch(klines)

        # 3. 查询 K 线
        results = await kline_repo.find_by_symbol(StockCode("600519"))
        assert len(results) == 10

        # 4. 统计
        count = await kline_repo.count_by_symbol(StockCode("600519"))
        assert count == 10

        # 5. 联表查询
        stats = await stock_repo.list_with_kline_stats(industry="白酒")
        assert len(stats) == 1
        assert stats[0]["record_count"] == 10

        # 6. 删除 K 线
        deleted = await kline_repo.delete_by_symbol(StockCode("600519"))
        assert deleted == 10

        count_after = await kline_repo.count_by_symbol(StockCode("600519"))
        assert count_after == 0
