"""API 路由集成测试

不需要数据库（mock 依赖），验证路由层的基本流程。
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock

import pytest


# Mock akshare 模块（环境无 akshare）
akshare_stub = types.ModuleType("akshare")
akshare_stub.__path__ = []
sys.modules.setdefault("akshare", akshare_stub)


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
