"""BaseCollectTask 框架单元测试

不依赖 DB / Redis — 用 AsyncMock 隔离。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.tasks.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    clear_cancel,
    execute_task,
    is_cancelled,
    request_cancel,
)


# ── 测试用具体子类 ──────────────────────────────────────────────


class _StubTask(BaseCollectTask):
    """最小可运行的子类，用于测试模板方法行为"""

    name = "stub"
    estimate_calls = 0
    pre_execute_calls = 0
    post_execute_calls = 0

    def __init__(self, total: int = 3, fail_indices: set[int] | None = None,
                 raise_cancelled: bool = False):
        super().__init__()
        self._total = total
        self._fail_indices = fail_indices or set()
        self._raise_cancelled = raise_cancelled

    async def estimate_total(self, params: dict) -> int:
        _StubTask.estimate_calls += 1
        return self._total

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        success = fail = 0
        for i in range(self._total):
            if is_cancelled(self._task_id):
                raise Cancelled()
            if self._raise_cancelled and i == 1:
                raise Cancelled()
            label = f"unit-{i}"
            ok = i not in self._fail_indices
            # on_unit_done is async (Redis pipeline); tests must pass AsyncMock
            import asyncio
            await on_unit_done(
                UnitResult(success=ok, detail=label, error=None if ok else "boom"),
                label,
            )
            if ok:
                success += 1
            else:
                fail += 1
        return TaskSummary(success=success, fail=fail, total_count=self._total,
                           message=f"stub done: {success}/{self._total}")

    async def pre_execute(self, params: dict) -> None:
        _StubTask.pre_execute_calls += 1

    async def post_execute(self, params: dict, summary: TaskSummary) -> None:
        _StubTask.post_execute_calls += 1


def _make_redis_mock():
    """构造一个简单的 redis mock（pipeline 支持链式调用）"""
    redis = MagicMock()
    pipe = MagicMock()
    pipe.hincrby = MagicMock(return_value=pipe)
    pipe.hset = MagicMock(return_value=pipe)
    pipe.execute = AsyncMock(return_value=[])
    redis.pipeline = MagicMock(return_value=pipe)
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def fake_redis(monkeypatch):
    redis = _make_redis_mock()

    async def _fake_get_redis():
        return redis

    # Patch the symbol imported in base.py
    import infrastructure.tasks.collect.base as base_mod
    monkeypatch.setattr(base_mod, "get_redis", _fake_get_redis)
    return redis


@pytest.fixture
def fake_db(monkeypatch):
    """Mock AsyncSessionLocal so _finish_task 不真的写库"""
    session = MagicMock()
    task_row = MagicMock()
    session.get = AsyncMock(return_value=task_row)
    session.commit = AsyncMock()

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=session)
    cm.__aexit__ = AsyncMock(return_value=None)

    @staticmethod
    def _factory():
        return cm

    import infrastructure.tasks.collect.base as base_mod
    monkeypatch.setattr(base_mod, "AsyncSessionLocal", _factory)
    return session


# ═══════════════════════════════════════════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════════════════════════════════════════


class TestDataClasses:
    def test_unit_result_frozen(self):
        ur = UnitResult(success=True, detail="x", saved_count=5)
        with pytest.raises(Exception):
            ur.success = False  # type: ignore[misc]

    def test_task_summary_defaults(self):
        ts = TaskSummary(success=1, fail=2)
        assert ts.success == 1
        assert ts.fail == 2
        assert ts.skip == 0
        assert ts.message == ""
        assert ts.total_count == 0


class TestCancelFlags:
    def setup_method(self):
        clear_cancel(0)

    def test_request_and_check(self):
        assert not is_cancelled(1)
        request_cancel(1)
        assert is_cancelled(1)
        clear_cancel(1)
        assert not is_cancelled(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 模板方法 execute_task
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestExecuteTaskNormal:
    async def test_all_success(self, fake_redis, fake_db):
        clear_cancel(999)
        _StubTask.estimate_calls = 0
        _StubTask.pre_execute_calls = 0
        _StubTask.post_execute_calls = 0

        handler = _StubTask(total=3)
        await execute_task(999, handler, {})

        assert _StubTask.pre_execute_calls == 1
        assert _StubTask.post_execute_calls == 1
        # estimate_total called once
        assert _StubTask.estimate_calls == 1
        # redis.hset for total
        fake_redis.hset.assert_any_call("collect:progress:999", "total", "3")
        # redis.hset for status=success
        fake_redis.hset.assert_any_call("collect:progress:999", "status", "success")
        # DB row updated
        assert fake_db.commit.called


@pytest.mark.asyncio
class TestExecuteTaskPartialFail:
    async def test_partial_failure_is_success(self, fake_redis, fake_db):
        """unit 0 失败、unit 1/2 成功 → status=success（既有语义：部分成功也算成功）"""
        clear_cancel(1000)
        handler = _StubTask(total=3, fail_indices={0})
        await execute_task(1000, handler, {})
        # 调用 hset(..., status, "success") 表示 task status
        status_calls = [
            call for call in fake_redis.hset.call_args_list
            if call.args[:2] == ("collect:progress:1000", "status")
        ]
        assert status_calls, "expected status hset call"
        assert status_calls[-1].args[2] == "success"


@pytest.mark.asyncio
class TestExecuteTaskAllFail:
    async def test_all_failure_is_failed(self, fake_redis, fake_db):
        clear_cancel(1001)
        handler = _StubTask(total=3, fail_indices={0, 1, 2})
        await execute_task(1001, handler, {})
        status_calls = [
            call for call in fake_redis.hset.call_args_list
            if call.args[:2] == ("collect:progress:1001", "status")
        ]
        assert status_calls[-1].args[2] == "failed"


@pytest.mark.asyncio
class TestExecuteTaskCancel:
    async def test_soft_cancel_midway(self, fake_redis, fake_db):
        """raise_cancelled=True 让子任务在第 2 个单元前 raise Cancelled"""
        clear_cancel(1002)
        handler = _StubTask(total=5, raise_cancelled=True)
        await execute_task(1002, handler, {})
        status_calls = [
            call for call in fake_redis.hset.call_args_list
            if call.args[:2] == ("collect:progress:1002", "status")
        ]
        assert status_calls[-1].args[2] == "cancelled"
        # cancel flag cleared after run
        assert not is_cancelled(1002)


@pytest.mark.asyncio
class TestExecuteTaskException:
    async def test_unexpected_exception_marks_failed(self, fake_redis, fake_db, monkeypatch):
        clear_cancel(1003)

        class _Boom(BaseCollectTask):
            name = "boom"

            async def estimate_total(self, params):
                return 1

            async def run(self, params, on_unit_done):
                raise RuntimeError("unexpected")

        handler = _Boom()
        await execute_task(1003, handler, {})
        status_calls = [
            call for call in fake_redis.hset.call_args_list
            if call.args[:2] == ("collect:progress:1003", "status")
        ]
        assert status_calls[-1].args[2] == "failed"


@pytest.mark.asyncio
class TestExecuteTaskCleanup:
    async def test_post_execute_called_on_exception(self, fake_redis, fake_db):
        """即便 run() 抛异常，post_execute 也应在 finally 中调用"""
        clear_cancel(1004)

        class _Boom(BaseCollectTask):
            name = "boom"
            post_called = False

            async def estimate_total(self, params):
                return 1

            async def run(self, params, on_unit_done):
                raise RuntimeError("x")

            async def post_execute(self, params, summary):
                _Boom.post_called = True

        await execute_task(1004, _Boom(), {})
        assert _Boom.post_called is True
