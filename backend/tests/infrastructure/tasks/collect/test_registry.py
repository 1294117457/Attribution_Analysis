"""CollectTaskRegistry 单元测试"""

from __future__ import annotations

import pytest

from infrastructure.tasks.collect.base import BaseCollectTask
from infrastructure.tasks.collect.registry import CollectTaskRegistry


class _Handler(BaseCollectTask):
    name = "x"
    async def estimate_total(self, params): return 0
    async def run(self, params, on_unit_done):
        from infrastructure.tasks.collect.base import TaskSummary
        return TaskSummary(success=0, fail=0)


def test_register_and_get():
    reg = CollectTaskRegistry()
    h = _Handler()
    reg.register("x", h)
    assert reg.get("x") is h
    assert "x" in reg.supported_types()


def test_register_duplicate_raises():
    reg = CollectTaskRegistry()
    reg.register("x", _Handler())
    with pytest.raises(ValueError, match="已注册"):
        reg.register("x", _Handler())


def test_register_name_mismatch_raises():
    """handler.name 与 task_type 不一致时拒绝"""
    reg = CollectTaskRegistry()
    bad = _Handler()
    bad.name = "y"
    with pytest.raises(ValueError, match="不一致"):
        reg.register("x", bad)


def test_register_empty_name_raises():
    """handler.name 空字符串时拒绝"""
    reg = CollectTaskRegistry()
    bad = _Handler()
    bad.name = ""
    with pytest.raises(ValueError, match="未设置 name"):
        reg.register("x", bad)


def test_get_unknown_returns_none():
    reg = CollectTaskRegistry()
    assert reg.get("unknown") is None
    assert reg.supported_types() == []
