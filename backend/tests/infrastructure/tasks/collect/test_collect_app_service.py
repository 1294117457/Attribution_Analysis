"""采集管理应用服务 单元测试（不依赖 DB / Redis / 调度器）

  · 参数合并：传入 > 方案项 params > default_params
  · run_one：不支持 collect_one 的任务报错；默认参数合并
  · _check_plan：名称 / 触发方式 / 方案项校验
  · run_plan：顺序执行、plan_run_id 取第一项、冲突跳过、stop_on_fail
  · 调度器：schedule 校验、job 同步 / 前缀清理
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from application.service import collect_manage_service as mod
from application.service.collect_manage_service import (
    CollectManageService,
    PlanNotFound,
    SubmittedTask,
    TaskConflict,
    UnknownTaskType,
)
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
)
from infrastructure.adapter.scheduler.collect.registry import setup_collect_task_registry
from infrastructure.adapter.scheduler.collect_scheduler import (
    MIN_INTERVAL_SECONDS,
    CollectScheduler,
    normalize_times,
    validate_schedule,
)


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


# ── 假 session / repo / registry ───────────────────────────────────────


class _Session:
    """模拟 AsyncSession：仅实现本服务真正用到的接口"""

    _table: dict = {}                          # task_id → row

    def __init__(self, *a, **k):
        self._committed: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, model, pk):
        # 优先在本次的写入缓冲里查
        for row in self._committed:
            if getattr(row, "id", None) == pk:
                return row
        return _Session._table.get(pk)

    async def execute(self, stmt):
        """prepare 里查 running 任务用：返回空结果集"""
        return SimpleNamespace(first=lambda: None, mappings=lambda: SimpleNamespace(all=lambda: []))

    async def flush(self):
        # 不动 _committed（save 后由 commit 写入）
        pass

    async def commit(self):
        for row in self._committed:
            _Session._table[getattr(row, "id", id(row))] = row
        self._committed.clear()

    async def refresh(self, obj):
        """真实 session 会回填 server default（created_at/updated_at），桩里是 no-op"""
        return None

    def add(self, row):
        # 给一个递增 id
        row.id = max(list(_Session._table.keys()) + [99]) + 1
        self._committed.append(row)


class _Repo:
    """假的采集配置仓储

    plan  → SimpleNamespace(plan 字段)
    items → [(task_type, params, enabled)]，已按 sort_order 排好
    """

    plan = None
    items: list = []
    fetchers: list = []
    realtime: set = set()

    def __init__(self, session=None):
        pass

    # ── fetchers ──
    async def list_fetchers(self, session):
        return list(_Repo.fetchers)

    async def get_fetcher(self, task_type, session):
        return next(
            (f for f in _Repo.fetchers if f.task_type == task_type), None,
        )

    # ── plans ──
    async def list_plans(self, session):
        return [p for p in [_Repo.plan] if p is not None]

    async def get_plan(self, plan_id, session):
        if _Repo.plan is None or _Repo.plan.id != plan_id:
            return None
        return _Repo.plan

    async def create_plan(self, session, **fields):
        defaults = dict(
            id=7, times=[], interval_seconds=None,
            last_run_at=None, last_task_id=None,
            created_at=None, updated_at=None,
        )
        defaults.update(fields)
        _Repo.plan = SimpleNamespace(**defaults)
        return _Repo.plan

    async def update_plan(self, session, plan, **fields):
        for k, v in fields.items():
            setattr(plan, k, v)
        return plan

    async def delete_plan(self, session, plan):
        _Repo.plan = None

    async def touch_plan(self, session, plan_id, task_id):
        self.touched = (plan_id, task_id)

    # ── plan items ──
    async def list_plan_items(self, session, plan_id):
        return [
            SimpleNamespace(id=i, plan_id=plan_id, task_type=tt, params=pp,
                            enabled=en, sort_order=i * 10)
            for i, (tt, pp, en) in enumerate(_Repo.items)
            if en
        ]

    async def list_all_plan_items(self, session, plan_id):
        return [
            SimpleNamespace(id=i, plan_id=plan_id, task_type=tt, params=pp,
                            enabled=en, sort_order=i * 10)
            for i, (tt, pp, en) in enumerate(_Repo.items)
        ]

    async def replace_plan_items(self, session, plan_id, items):
        _Repo.items = [
            (it["task_type"], it["params"], it.get("enabled", True)) for it in items
        ]


class _Registry:
    def __init__(self, handlers, realtime=()):
        self._handlers = {h.name: h for h in handlers}
        self._realtime = {n: object() for n in realtime}

    def get(self, task_type):
        return self._handlers.get(task_type)

    def supported_types(self):
        return list(self._handlers)

    def realtime_get(self, name):
        return self._realtime.get(name)


def _svc(repo=None, scheduler=None, realtime=()):
    """构造一个零依赖的 service（只测纯逻辑，不触 DB/Redis）"""
    return CollectManageService(
        redis=SimpleNamespace(hset=AsyncMock(), expire=AsyncMock()),
        task_registry=_Registry([_A(), _B(), _C()], realtime),
        scheduler=scheduler,
        config_repo=repo or _Repo(),
        realtime_registry=SimpleNamespace(get=_Registry([], realtime).realtime_get),
        session_factory=lambda: _Session(),
    )


@pytest.fixture(autouse=True)
def registry():
    setup_collect_task_registry([_A(), _B(), _C()])
    _Repo.plan = None
    _Repo.items = []
    _Repo.fetchers = []
    yield


# ═══════════════════════════════════════════════════════════════════════
class TestParams:
    async def test_merge_priority(self):
        svc = _svc()
        merged = await svc.resolve_params(
            "a", {"y": "given"}, plan_item_params={"days": 5, "y": "plan"},
        )
        # 传入 > 方案项 > default
        assert merged == {"days": 5, "x": "default", "y": "given"}

    async def test_no_plan_uses_defaults(self):
        assert await _svc().resolve_params("a") == {"days": 1, "x": "default"}

    def test_unknown_task_type(self):
        with pytest.raises(UnknownTaskType):
            _svc().handler("nope")


# ═══════════════════════════════════════════════════════════════════════
class TestRunOne:
    async def test_merges_default_params(self):
        result = await _svc().run_one("a", "u1", {"days": 9})
        assert result.data == {"days": 9, "x": "default"}

    async def test_task_without_collect_one(self):
        with pytest.raises(UnknownTaskType, match="不支持按单元调用"):
            await _svc().run_one("b", "u1")


# ═══════════════════════════════════════════════════════════════════════
class TestCheckPlan:
    def test_normalizes_and_sorts_times(self):
        out = _svc()._check_plan({
            "name": "盘后", "enabled": True, "schedule_type": "time",
            "times": ["15:00", "09:30", "15:00"],
            "items": [{"task_type": "a"}],
        })
        assert out["times"] == ["09:30", "15:00"]     # 去重 + 升序
        assert out["schedule_type"] == "time"

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError, match="名称不能为空"):
            _svc()._check_plan({"name": "  ", "items": [{"task_type": "a"}]})

    def test_rejects_enabled_without_schedule(self):
        with pytest.raises(ValueError, match="启用方案需要选择触发方式"):
            _svc()._check_plan({"name": "x", "enabled": True, "items": [{"task_type": "a"}]})

    def test_rejects_empty_items(self):
        with pytest.raises(ValueError, match="至少需要包含一个采集接口"):
            _svc()._check_plan({"name": "x", "items": []})

    def test_rejects_duplicate_task_type(self):
        with pytest.raises(ValueError, match="重复的采集接口"):
            _svc()._check_plan({
                "name": "x", "items": [{"task_type": "a"}, {"task_type": "a"}],
            })

    def test_rejects_realtime_interface(self, ):
        svc = _svc(realtime=("concept_minute",))
        with pytest.raises(ValueError, match="实时接口，不能加入方案"):
            svc._check_plan({"name": "x", "items": [{"task_type": "concept_minute"}]})

    def test_rejects_enabled_without_active_item(self):
        with pytest.raises(ValueError, match="至少一个启用的采集接口"):
            _svc()._check_plan({
                "name": "x", "enabled": True, "schedule_type": "interval",
                "interval_seconds": 60, "items": [{"task_type": "a", "enabled": False}],
            })

    def test_interval_lower_bound(self):
        with pytest.raises(ValueError, match="不能小于"):
            _svc()._check_plan({
                "name": "x", "enabled": True, "schedule_type": "interval",
                "interval_seconds": MIN_INTERVAL_SECONDS - 1,
                "items": [{"task_type": "a"}],
            })


# ═══════════════════════════════════════════════════════════════════════
class TestRunPlan:
    @pytest.fixture
    def svc(self, monkeypatch):
        svc = _svc()
        svc.calls = []
        next_id = iter(range(100, 200))
        svc.statuses = {}
        svc.conflicts = set()

        async def prepare(task_type, params=None, trigger="manual", *,
                      plan_item_params=None, plan_run_id=None, plan_first=False):
            svc.calls.append((task_type, plan_run_id, plan_first))
            if task_type in svc.conflicts:
                raise TaskConflict("running")
            task_id = next(next_id)
            status = svc.statuses.get(task_type, "success")
            row = SimpleNamespace(
                id=task_id, status=status, success_count=1, fail_count=0,
                plan_run_id=plan_run_id,
            )
            _Session._table[task_id] = row
            return SubmittedTask(task_id=task_id, task_type=task_type,
                                 total_count=1, params=params or {})

        svc.prepare = prepare
        monkeypatch.setattr(mod, "execute_task", AsyncMock())
        return svc

    def _plan(self, items, stop_on_fail=True):
        _Repo.plan = SimpleNamespace(
            id=1, name="盘后", stop_on_fail=stop_on_fail,
        )
        _Repo.items = [(t, {}, True) for t in items]

    async def test_sequential_and_shared_run_id(self, svc):
        self._plan(["a", "b", "c"])
        run_id = await svc.run_plan(1)
        # 第一项 plan_run_id=None + plan_first=True；后续共享第一项 id
        assert run_id == 100
        assert svc.calls == [("a", None, True), ("b", 100, False), ("c", 100, False)]
        assert mod.execute_task.await_count == 3

    async def test_conflict_skipped_and_next_becomes_first(self, svc):
        self._plan(["a", "b", "c"])
        svc.conflicts = {"a"}
        run_id = await svc.run_plan(1)
        assert run_id == 100
        assert svc.calls[1:] == [("b", None, True), ("c", 100, False)]
        assert mod.execute_task.await_count == 2

    async def test_stop_on_fail(self, svc):
        self._plan(["a", "b", "c"])
        svc.statuses["b"] = "failed"
        await svc.run_plan(1)
        assert [c[0] for c in svc.calls] == ["a", "b"]

    async def test_continue_when_stop_on_fail_off(self, svc):
        self._plan(["a", "b", "c"], stop_on_fail=False)
        svc.statuses["b"] = "failed"
        await svc.run_plan(1)
        assert [c[0] for c in svc.calls] == ["a", "b", "c"]

    async def test_missing_plan_returns_none(self, svc):
        assert await svc.run_plan(404) is None
        assert svc.calls == []

    async def test_all_items_disabled_returns_none(self, svc):
        _Repo.plan = SimpleNamespace(id=1, name="空", stop_on_fail=True)
        _Repo.items = [("a", {}, False)]
        assert await svc.run_plan(1) is None
        assert svc.calls == []


# ═══════════════════════════════════════════════════════════════════════
class TestPlanCrud:
    async def test_create_calls_scheduler(self):
        sched = SimpleNamespace(sync_plan=lambda *a, **k: sched.calls.append((a, k)))
        sched.calls = []
        svc = _svc(scheduler=sched)
        out = await svc.create_plan({
            "name": "盘后", "enabled": True, "schedule_type": "time",
            "times": ["15:30"], "items": [{"task_type": "a"}],
        })
        assert out["name"] == "盘后"
        assert _Repo.items == [("a", {}, True)]
        assert len(sched.calls) == 1                     # 建表后同步了定时

    async def test_scheduler_none_is_noop(self):
        svc = _svc(scheduler=None)                      # 调度器未启用
        out = await svc.create_plan({
            "name": "手动", "items": [{"task_type": "a"}],
        })
        assert out["enabled"] is False

    async def test_update_missing_plan_raises(self):
        with pytest.raises(PlanNotFound):
            await _svc().update_plan(404, {"name": "x", "items": [{"task_type": "a"}]})

    async def test_delete_missing_plan_raises(self):
        with pytest.raises(PlanNotFound):
            await _svc().delete_plan(404)

    async     def test_list_plans_joins_labels(self):
        _Repo.plan = SimpleNamespace(
            id=1, name="盘后", enabled=False, schedule_type=None, times=[],
            interval_seconds=None, stop_on_fail=True, last_run_at=None,
            last_task_id=None, created_at=None, updated_at=None,
        )
        _Repo.items = [("a", {}, True)]
        _Repo.fetchers = [SimpleNamespace(
            task_type="a", label="任务A", facet="tech", sub_facet="kline",
            description="", kind="batch", status="ready", default_params={},
            supports_run_one=False, sort_order=0,
        )]
        out = await _svc().list_plans()
        assert len(out) == 1
        assert out[0]["items"][0]["label"] == "任务A"

    async def test_list_fetchers(self):
        _Repo.fetchers = [SimpleNamespace(
            task_type="a", label="任务A", facet="tech", sub_facet="kline",
            description="", kind="batch", status="ready", default_params={},
            supports_run_one=False, sort_order=0,
        )]
        out = await _svc().list_fetchers()
        assert out[0]["task_type"] == "a"


# ═══════════════════════════════════════════════════════════════════════
class TestValidateSchedule:
    def test_time_ok(self):
        validate_schedule("time", ["09:30", "15:00"], None)

    def test_time_requires_times(self):
        with pytest.raises(ValueError, match="至少一个触发时间"):
            validate_schedule("time", [], None)

    def test_time_rejects_bad_format(self):
        with pytest.raises(ValueError, match="时间格式无效"):
            validate_schedule("time", ["9:30"], None)     # 未补零

    def test_time_rejects_25h(self):
        with pytest.raises(ValueError, match="时间格式无效"):
            validate_schedule("time", ["25:00"], None)

    def test_time_caps_at_24(self):
        with pytest.raises(ValueError, match="最多"):
            validate_schedule("time", [f"{h:02d}:00" for h in range(24)] + ["00:00"], None)

    def test_interval_ok(self):
        validate_schedule("interval", [], 300)

    def test_interval_requires_value(self):
        with pytest.raises(ValueError, match="需要设置间隔"):
            validate_schedule("interval", [], None)

    def test_interval_lower_bound(self):
        with pytest.raises(ValueError, match="不能小于"):
            validate_schedule("interval", [], MIN_INTERVAL_SECONDS - 1)

    def test_none_means_manual_only(self):
        validate_schedule(None, [], None)

    def test_normalize_times_drops_garbage(self):
        assert normalize_times(["15:00", "bad", "09:30", "15:00"]) == ["09:30", "15:00"]


# ═══════════════════════════════════════════════════════════════════════
class TestSchedulerJobs:
    def _ids(self, s):
        return {j.id for j in s._scheduler.get_jobs()}

    def test_time_mode_registers_one_job_per_time(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "time", ["09:30", "15:00"])
        assert self._ids(s) == {"plan:1@09:30", "plan:1@15:00"}

    def test_interval_mode_registers_single_job(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "interval", [], 300)
        assert self._ids(s) == {"plan:1"}

    def test_disable_removes_all_sub_jobs(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "time", ["09:30", "15:00"])
        s.sync_plan(1, False, "time", ["09:30", "15:00"])
        assert self._ids(s) == set()

    def test_switching_mode_clears_old_jobs(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "time", ["09:30"])
        s.sync_plan(1, True, "interval", [], 300)
        # 旧的 plan:1@09:30 必须被清掉，不能残留
        assert self._ids(s) == {"plan:1"}

    def test_prefix_match_does_not_bleed(self):
        """plan:1 的清理不能误删 plan:11 —— 这是 _remove_prefix 的核心约束"""
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "time", ["09:30"])
        s.sync_plan(11, True, "time", ["09:30"])
        s.sync_plan(1, False, "time", ["09:30"])
        assert self._ids(s) == {"plan:11@09:30"}

    def test_interval_below_bound_not_registered(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "interval", [], 10)
        assert self._ids(s) == set()

    def test_none_schedule_not_registered(self):
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, None, [], None)
        assert self._ids(s) == set()

    def test_next_run_is_earliest(self):
        """next_run 必须返回所有子 job 里最早的那个触发时间

        ⚠️ 不能断言固定时刻：若当前已过 09:30，APScheduler 会把 09:30 排到明天，
           此时"最早"其实是今天的 15:00/23:00。这里改为与各 job 自身的
           next fire 取 min 做等价校验。
        """
        from apscheduler.util import convert_to_datetime
        s = CollectScheduler("Asia/Shanghai")
        s.sync_plan(1, True, "time", ["15:00", "09:30", "23:00"])
        nxt = s.next_run("plan:1")
        assert nxt is not None

        now = datetime.now(tz=s._tz)
        expected = []
        for job in s._scheduler.get_jobs():
            base = getattr(job, "_next_run_time", None) or now
            expected.append(
                convert_to_datetime(job.trigger.get_next_fire_time(base, now), s._tz, "x")
            )
        assert nxt == min(expected)

    def test_next_run_none_for_unknown_plan(self):
        assert CollectScheduler("Asia/Shanghai").next_run("plan:99") is None
