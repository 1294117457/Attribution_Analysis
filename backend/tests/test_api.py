"""API 路由集成测试

不需要数据库（mock 依赖），验证路由层的基本流程。
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


# Mock tushare 模块（环境无 tushare）
tushare_stub = types.ModuleType("tushare")
tushare_stub.__path__ = []
tushare_stub.set_token = lambda *a, **k: None
tushare_stub.pro_api = lambda *a, **k: MagicMock()
sys.modules.setdefault("tushare", tushare_stub)


from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    def test_health(self, client):
        """健康检查端点"""
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "2.0.0"


class TestOpenAPISchema:
    def test_openapi_generated(self, client):
        """OpenAPI Schema 生成"""
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        # 关键路径都应该存在
        paths = schema["paths"].keys()
        assert "/health" in paths
        assert "/api/v1/klines/{symbol}" in paths
        assert "/api/v1/klines/collect" in paths
        assert "/api/v1/stocks/" in paths
        assert "/api/v1/stocks/{symbol}" in paths


class TestValidationError:
    def test_invalid_date_format(self, client):
        """日期格式错误返回 422"""
        r = client.get("/api/v1/klines/000001/2024-99-99")
        assert r.status_code == 422
        data = r.json()
        assert data["code"] == 422
        assert "校验失败" in data["message"]
