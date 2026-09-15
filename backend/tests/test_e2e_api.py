"""端到端 API 集成测试

通过 TestClient 测试完整的 API 流程（含数据库）。
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import pytest
import pytest_asyncio

# 添加 src 到路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir / "src"))


@pytest.fixture(scope="function")
def event_loop():
    """每个测试用新的事件循环"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _run_async(coro):
    """运行协程（用于同步 fixture / 测试）"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(scope="function")
def client():
    """每个测试用独立 TestClient"""
    from main import app
    return TestClient(app)


@pytest.fixture(scope="function")
def clean_db():
    """清理数据库"""
    from sqlalchemy import text
    from infrastructure.database.connection import async_engine

    async def _do():
        async with async_engine.begin() as conn:
            await conn.execute(text("DELETE FROM daily_klines"))
            await conn.execute(text("DELETE FROM stock_infos"))

    _run_async(_do())
    yield
    _run_async(_do())


@pytest.fixture(scope="function")
def insert_kline():
    """辅助函数：插入 K 线（带显式 commit）"""
    from infrastructure.database.connection import AsyncSessionLocal
    from infrastructure.repositories.kline_repository import KlineRepoImpl
    from domain.kline.entity import Kline

    def _do(symbol="000001", day=1, **overrides):
        kwargs = dict(
            symbol=symbol,
            name="测试股票",
            trade_date=date(2024, 1, day),
            open=10.0, high=11.0, low=9.0, close=10.5,
            volume=1000, amount=10000,
        )
        kwargs.update(overrides)

        async def _async():
            async with AsyncSessionLocal() as s:
                repo = KlineRepoImpl(s)
                k = Kline.create(**kwargs)
                await repo.save(k)
                await s.commit()  # 显式提交

        _run_async(_async())

    return _do


from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"


class TestStockAPI:
    def test_create_stock(self, client, clean_db):
        r = client.post(
            "/api/v1/stocks/",
            params={"symbol": "000001", "name": "平安银行", "industry": "银行", "market": "SZ"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == 201
        assert data["data"]["symbol"] == "000001"
        assert data["data"]["name"] == "平安银行"

    def test_get_stock(self, client, clean_db):
        client.post(
            "/api/v1/stocks/",
            params={"symbol": "000002", "name": "万科A"},
        )
        r = client.get("/api/v1/stocks/000002")
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "万科A"

    def test_get_stock_not_found(self, client, clean_db):
        r = client.get("/api/v1/stocks/999999")
        assert r.status_code == 404
        assert "999999" in r.json()["message"]

    def test_list_stocks(self, client, clean_db):
        for sym in ["000001", "000002", "600000"]:
            client.post(
                "/api/v1/stocks/",
                params={"symbol": sym, "name": f"股票{sym}"},
            )
        r = client.get("/api/v1/stocks/")
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_update_stock(self, client, clean_db):
        client.post("/api/v1/stocks/", params={"symbol": "000001", "name": "旧名"})
        r = client.patch(
            "/api/v1/stocks/000001",
            json={"name": "新名", "industry": "银行"},
        )
        assert r.status_code == 200
        assert r.json()["data"]["name"] == "新名"

    def test_delete_stock(self, client, clean_db):
        client.post("/api/v1/stocks/", params={"symbol": "000001", "name": "X"})
        r = client.delete("/api/v1/stocks/000001")
        assert r.status_code == 200
        assert r.json()["data"]["deleted_count"] == 1


class TestKlineAPI:
    def test_get_klines(self, client, clean_db, insert_kline):
        for day in range(1, 6):
            insert_kline("000001", day)

        r = client.get("/api/v1/klines/000001", params={"limit": 10})
        assert r.status_code == 200
        data = r.json()["data"]
        assert data["total"] == 5

    def test_get_kline_stats(self, client, clean_db, insert_kline):
        for day in range(1, 4):
            insert_kline("000001", day)

        r = client.get("/api/v1/klines/000001/stats")
        assert r.status_code == 200
        data = r.json()
        assert data["data"]["count"] == 3

    def test_get_kline_by_date_not_found(self, client, clean_db):
        r = client.get("/api/v1/klines/000001/2024-01-01")
        assert r.status_code == 404

    def test_delete_kline(self, client, clean_db, insert_kline):
        insert_kline("000001", 1)

        r = client.delete("/api/v1/klines/000001/2024-01-01")
        assert r.status_code == 200
        assert r.json()["data"]["deleted_count"] == 1

    def test_delete_all_klines(self, client, clean_db, insert_kline):
        for day in range(1, 4):
            insert_kline("000001", day)

        r = client.delete("/api/v1/klines/000001")
        assert r.status_code == 200
        assert r.json()["data"]["deleted_count"] == 3


class TestAPIResponseFormat:
    """统一响应格式测试"""

    def test_success_response(self, client):
        """健康检查端点（自定义格式）"""
        r = client.get("/health")
        body = r.json()
        assert "status" in body

    def test_api_success_response(self, client, clean_db):
        """API 成功响应格式"""
        client.post("/api/v1/stocks/", params={"symbol": "000001", "name": "X"})
        r = client.get("/api/v1/stocks/000001")
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 200
        assert body["data"] is not None

    def test_not_found_response(self, client, clean_db):
        r = client.get("/api/v1/stocks/999999")
        body = r.json()
        assert body["code"] == 404
        assert body["data"] is None
