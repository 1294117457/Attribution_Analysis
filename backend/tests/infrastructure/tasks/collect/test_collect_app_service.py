"""CollectAppService 单元测试（不依赖 DB / Redis）

  · 参数合并：传入 > 方案 params > default_params
  · run_one：不支持 collect_one 的任务报错；默认参数合并
  · run_group：顺序执行、group_run_id 取第一项、冲突跳过、stop_on_fail
  · 调度器：cron 校验、job 同步 / 移除
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.service import collect_app_service as mod
from application.service.collect_app_service import (
    CollectAppService,
    SubmittedTask,
    TaskConflict,
    UnknownTaskType,
)
from infrastructure.adapter.scheduler.collect.base import BaseCollectTask, TaskSummary, UnitResult
from infrastructure.adapter.scheduler.collect.registry import setup_collect_task_registry
from infrastructure.adapter.scheduler.collect_scheduler import CollectScheduler, validate_cron


class _A(BaseCollectTask):
    name = "a"
    default_params = {"days": 1, "x": "default"}

    async def list_units(self, params):
        return ["u1"]

    async def collect_one(self, unit, params):
        return UnitResult(success=True, detail=unit, data=params)


class _B(BaseCollectTask):
    name = "b"

    async def estimate_total(self, params):
        return 1

    async def run(self, params, on_unit_done):
        return TaskSummary(success=1, fail=0)


class _C(_A):
    name = "c"


class _Session:
    def __init__(self, rows=None):
        self._rows = rows or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, model, pk):
        status = self._rows.get(pk)
        return SimpleNamespace(status=status) if status else None


class _Repo:
    plan = None
    group = None

    def __init__(self, session):
        pass

    async def get_plan(self, task_type):
        return _Repo.plan

    async def get_group(self, group_id):
        return _Repo.group


@pytest.fixture(autouse=True)
def registry():
    setup_collect_task_registry([_A(), _B(), _C()])
    _Repo.plan = None
    _Repo.group = None
    yield


@pytest.fixture
def wiring(monkeypatch):
    rows: dict[int, str] = {}
    monkeypatch.setattr(mod, "AsyncSessionLocal", lambda: _Session(rows))
    monkeypatch.setattr(mod, "CollectConfigRepoImpl", _Repo)
    return rows


class TestParams:
    async def test_merge_priority(self, wiring):
        _Repo.plan = SimpleNamespace(params={"days": 5, "y": "plan"})
        merged = await CollectAppService().resolve_params("a", {"y": "given"})
        assert merged == {"days": 5, "x": "default", "y": "given"}

    async def test_no_plan_uses_defaults(self, wiring):
        assert await CollectAppService().resolve_params("a") == {"days": 1, "x": "default"}

    def test_unknown_task_type(self):
        with pytest.raises(UnknownTaskType):
            CollectAppService.handler("nope")


class TestRunOne:
    async def test_merges_default_params(self):
        result = await CollectAppService().run_one("a", "u1", {"days": 9})
        assert result.data == {"days": 9, "x": "default"}

    async def test_task_without_collect_one(self):
        with pytest.raises(UnknownTaskType, match="不支持按单元调用"):
            await CollectAppService().run_one("b", "u1")


class TestRunGroup:
    @pytest.fixture
    def svc(self, monkeypatch, wiring):
        svc = CollectAppService()
        svc.calls = []
        next_id = iter(range(100, 200))

        async def prepare(task_type, params=None, trigger="manual", *, group_run_id=None, group_first=False):
            svc.calls.append((task_type, group_run_id, group_first))
            if task_type in svc.conflicts:
                raise TaskConflict("running")
            task_id = next(next_id)
            wiring[task_id] = svc.statuses.get(task_type, "success")
            return SubmittedTask(task_id=task_id, task_type=task_type, total_count=1, params=params or {})

        svc.conflicts = set()
        svc.statuses = {}
        svc.prepare = prepare
        monkeypatch.setattr(mod, "execute_task", AsyncMock())
        monkeypatch.setattr(CollectAppService, "_touch_group", AsyncMock())
        return svc

    def _group(self, items, stop_on_fail=True):
        _Repo.group = SimpleNamespace(
            name="盘后", items=[{"task_type": t, "params": {}} for t in items], stop_on_fail=stop_on_fail,
        )

    async def test_sequential_and_shared_run_id(self, svc):
        self._group(["a", "b", "c"])
        run_id = await svc.run_group(1)
        assert run_id == 100
        assert svc.calls == [("a", None, True), ("b", 100, False), ("c", 100, False)]
        assert mod.execute_task.await_count == 3
        CollectAppService._touch_group.assert_awaited_once_with(1, 100)

    async def test_conflict_skipped_and_next_becomes_first(self, svc):
        self._group(["a", "b", "c"])
        svc.conflicts = {"a"}
        run_id = await svc.run_group(1)
        assert run_id == 100
        assert svc.calls[1:] == [("b", None, True), ("c", 100, False)]
        assert mod.execute_task.await_count == 2

    async def test_stop_on_fail(self, svc):
        self._group(["a", "b", "c"])
        svc.statuses = {"b": "failed"}
        await svc.run_group(1)
        assert [c[0] for c in svc.calls] == ["a", "b"]

    async def test_continue_when_stop_on_fail_off(self, svc):
        self._group(["a", "b", "c"], stop_on_fail=False)
        svc.statuses = {"b": "failed"}
        await svc.run_group(1)
        assert [c[0] for c in svc.calls] == ["a", "b", "c"]

    async def test_missing_group(self, svc):
        assert await svc.run_group(404) is None
        assert svc.calls == []


class TestScheduler:
    def test_validate_cron(self):
        validate_cron("30 15 * * 1-5")
        with pytest.raises(ValueError, match="cron 表达式无效"):
            validate_cron("every day")

    def test_sync_adds_and_removes_job(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan("a", True, "0 16 * * 1-5")
        assert s._scheduler.get_job("plan:a") is not None
        s.sync_plan("a", False, "0 16 * * 1-5")
        assert s._scheduler.get_job("plan:a") is None
        s.sync_group(3, True, None)
        assert s._scheduler.get_job("group:3") is None
