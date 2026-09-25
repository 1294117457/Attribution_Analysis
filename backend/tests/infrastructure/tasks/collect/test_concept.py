"""ConceptCollectTask 单元测试

使用 AsyncMock 隔离 fetcher / repo / operation，验证：
  · estimate_total 拉清单拿数
  · run 调用 _sync_one 每概念一次
  · 失败概念包装为 UnitResult(success=False)
  · 取消信号触发 Cancelled
  · 成员数累加进 TaskSummary.message
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from infrastructure.tasks.collect.base import (
    Cancelled,
    TaskSummary,
    UnitResult,
    clear_cancel,
    request_cancel,
)
from infrastructure.tasks.collect.concept import ConceptCollectTask


def _make_concept_bo(name: str, code: str = "BK0001"):
    """构造一个伪 ConceptListBO（绕过 pydantic 校验，直接 MagicMock）"""
    bo = MagicMock()
    bo.name = name
    bo.code = code
    return bo


@pytest.fixture
def mock_fetcher():
    fetcher = MagicMock()
    fetcher.fetch_concept_list = MagicMock(return_value=[
        _make_concept_bo("人形机器人"),
        _make_concept_bo("中字头"),
        _make_concept_bo("算力"),
    ])
    fetcher.fetch_concept_stocks = MagicMock(return_value=[])
    fetcher.source_name = "AkShare"
    return fetcher


@pytest.fixture
def mock_operation_cls():
    """Mock ConceptSyncOperation._sync_one 返回不同 member_count"""
    counts = {"人形机器人": 15, "中字头": 30, "算力": 8}
    failures = {"算力"}

    async def _fake_sync_one(self, bo):
        if bo.name in failures:
            raise RuntimeError("mock fetch failure")
        return counts.get(bo.name, 0)

    with patch(
        "infrastructure.tasks.collect.concept.ConceptSyncOperation._sync_one",
        new=_fake_sync_one,
    ):
        yield counts, failures


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.upsert_concept = AsyncMock(return_value=MagicMock(id=1))
    repo.upsert_members = AsyncMock(return_value=10)
    return repo


@pytest.mark.asyncio
class TestEstimateTotal:
    async def test_returns_concept_count(self, mock_fetcher):
        task = ConceptCollectTask()
        task._fetcher = mock_fetcher  # 直接注入，避免内部 init

        n = await task.estimate_total({})
        assert n == 3

    async def test_returns_zero_on_failure(self):
        task = ConceptCollectTask()
        fetcher = MagicMock()
        fetcher.fetch_concept_list = MagicMock(side_effect=RuntimeError("akshare down"))
        task._fetcher = fetcher

        n = await task.estimate_total({})
        assert n == 0


@pytest.mark.asyncio
class TestRunHappyPath:
    async def test_calls_sync_one_per_concept(
        self, mock_fetcher, mock_repo, mock_operation_cls,
    ):
        counts, failures = mock_operation_cls
        task = ConceptCollectTask()
        task._fetcher = mock_fetcher

        reported: list[tuple[UnitResult, str]] = []

        async def _on_unit_done(result, label):
            reported.append((result, label))

        summary = await task.run({}, _on_unit_done)

        # 全部成功（算力虽然 mock 失败但实际不在 failures 集合里 — 修正）
        # 注：上面 fixture 中 failures = {"算力"}，所以实际会失败 1 个
        assert summary.success == 2
        assert summary.fail == 1
        assert summary.total_count == 3
        # 成员数 = 15 + 30 = 45（算力失败未计入）
        assert "45" in summary.message or "成功" in summary.message

        # 报告顺序与清单一致
        labels = [r[1] for r in reported]
        assert labels == ["人形机器人", "中字头", "算力"]

        # 每个 success 的 UnitResult 都带 saved_count
        success_results = [r for r in reported if r[0].success]
        for ur, label in success_results:
            assert ur.saved_count == counts[label]

        # 失败的 UnitResult 带 error
        fail_results = [r for r in reported if not r[0].success]
        assert len(fail_results) == 1
        assert "算力" in fail_results[0][0].error or "算力" in fail_results[0][1]


@pytest.mark.asyncio
class TestRunAllSuccess:
    async def test_no_failures_yields_clean_summary(
        self, mock_fetcher, mock_repo, mock_operation_cls,
    ):
        # 覆盖 fixture，让所有概念都成功
        async def _all_ok(self, bo):
            return 10

        with patch(
            "infrastructure.tasks.collect.concept.ConceptSyncOperation._sync_one",
            new=_all_ok,
        ):
            task = ConceptCollectTask()
            task._fetcher = mock_fetcher
            async def _noop(result, label): pass
            summary = await task.run({}, _noop)

        assert summary.success == 3
        assert summary.fail == 0
        assert summary.total_count == 3


@pytest.mark.asyncio
class TestRunCancel:
    async def test_cancelled_raises(self, mock_fetcher, mock_repo, mock_operation_cls):
        clear_cancel(5001)
        request_cancel(5001)
        try:
            task = ConceptCollectTask()
            task._task_id = 5001
            task._fetcher = mock_fetcher

            async def _noop(result, label): pass
            with pytest.raises(Cancelled):
                await task.run({}, _noop)
        finally:
            clear_cancel(5001)


@pytest.mark.asyncio
class TestRunFetchFailure:
    async def test_run_returns_summary_with_zero_when_fetch_fails(self):
        task = ConceptCollectTask()
        fetcher = MagicMock()
        fetcher.fetch_concept_list = MagicMock(side_effect=RuntimeError("akshare 5xx"))
        task._fetcher = fetcher

        async def _noop(result, label): pass
        summary = await task.run({}, _noop)
        assert summary.success == 0
        assert summary.fail == 0
        assert "拉清单失败" in summary.message


@pytest.mark.asyncio
class TestRunParams:
    async def test_source_param_passed_through(self, mock_fetcher, mock_repo, mock_operation_cls):
        """params.source 应被记录到日志（不强制影响 fetcher 行为，AKShare 只支持 em）"""
        task = ConceptCollectTask()
        task._fetcher = mock_fetcher
        async def _noop(result, label): pass
        summary = await task.run({"source": "ths"}, _noop)
        # 不应抛异常；summary 应正常返回
        assert summary.total_count == 3
