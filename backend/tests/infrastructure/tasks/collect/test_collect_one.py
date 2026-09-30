"""采集接口（list_units / collect_one / 默认 run）单元测试

  · 基类默认 run：遍历单元、并发分批、首轮失败末尾重试、取消、supports_collect_one
  · daily_basic / stock_basic / daily_kline 的 collect_one：落库、跳过、data 回传
"""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from infrastructure.adapter.scheduler.collect import daily_basic, daily_kline, stock_basic
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    UnitResult,
    clear_cancel,
    request_cancel,
)

TASK_ID = 7171


class _Reporter:
    def __init__(self):
        self.labels: list[str] = []
        self.results: list[UnitResult] = []

    async def __call__(self, result, label):
        self.results.append(result)
        self.labels.append(label)


class _Session:
    def __init__(self):
        self.commit = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


# ── 基类默认 run ─────────────────────────────────────────────────────


class _UnitTask(BaseCollectTask):
    name = "unit_stub"
    default_params = {"days": 1}
    retry_delay = 0

    def __init__(self, units, fail_first=(), always_fail=(), concurrency=1):
        super().__init__()
        self._units = units
        self._fail_first = set(fail_first)
        self._always_fail = set(always_fail)
        self.concurrency = concurrency
        self.calls: list[str] = []
        self._task_id = TASK_ID

    async def list_units(self, params):
        return list(self._units)

    async def collect_one(self, unit, params):
        self.calls.append(unit)
        if unit in self._always_fail or (unit in self._fail_first and self.calls.count(unit) == 1):
            raise RuntimeError(f"{unit} boom")
        return UnitResult(success=True, detail=unit, saved_count=2, skipped=unit == "empty")


@pytest.fixture(autouse=True)
def _clear():
    clear_cancel(TASK_ID)
    yield
    clear_cancel(TASK_ID)


class TestDefaultRun:
    async def test_estimate_total_uses_list_units(self):
        assert await _UnitTask(["a", "b", "c"]).estimate_total({}) == 3

    async def test_all_units_reported(self):
        task, reporter = _UnitTask(["a", "empty", "c"]), _Reporter()
        summary = await task.run({}, reporter)
        assert (summary.success, summary.fail, summary.skip, summary.total_count) == (3, 0, 1, 3)
        assert reporter.labels == ["a", "empty", "c"]
        assert "写入 6 条" in summary.message

    async def test_failed_unit_retried_at_end(self):
        task, reporter = _UnitTask(["a", "b", "c"], fail_first={"b"}), _Reporter()
        summary = await task.run({}, reporter)
        assert summary.success == 3 and summary.fail == 0
        assert task.calls == ["a", "b", "c", "b"]
        assert reporter.labels == ["a", "c", "b"]

    async def test_retry_still_failing_counts_fail(self):
        task, reporter = _UnitTask(["a", "b"], always_fail={"a"}), _Reporter()
        summary = await task.run({}, reporter)
        assert summary.success == 1 and summary.fail == 1
        failed = [r for r in reporter.results if not r.success]
        assert failed[0].error == "a boom"

    async def test_concurrency_batches(self):
        task = _UnitTask(["a", "b", "c", "d", "e"], concurrency=2)
        summary = await task.run({}, _Reporter())
        assert summary.success == 5 and sorted(task.calls) == ["a", "b", "c", "d", "e"]

    async def test_cancel(self):
        request_cancel(TASK_ID)
        with pytest.raises(Cancelled):
            await _UnitTask(["a"]).run({}, _Reporter())

    def test_supports_collect_one(self):
        class _NoUnit(BaseCollectTask):
            name = "no_unit"

        assert _UnitTask([]).supports_collect_one is True
        assert _NoUnit().supports_collect_one is False


# ── daily_basic ──────────────────────────────────────────────────────


class TestDailyBasic:
    @pytest.fixture
    def wiring(self, monkeypatch):
        fetcher, repo, session = MagicMock(), MagicMock(), _Session()
        repo.save_batch = AsyncMock(return_value=5)
        registry = MagicMock()
        registry.get.return_value = fetcher
        monkeypatch.setattr(daily_basic, "get_registry", lambda: registry)
        monkeypatch.setattr(daily_basic, "AsyncSessionLocal", lambda: session)
        monkeypatch.setattr(daily_basic, "FinDailyBasicRepoImpl", lambda s: repo)
        return fetcher, repo, session

    async def test_list_units(self):
        task = daily_basic.DailyBasicCollectTask()
        assert await task.list_units({"trade_date": "2026-09-30"}) == ["20260930"]
        units = await task.list_units({"days": 3})
        assert len(units) == 3 and units[0] == date.today().strftime("%Y%m%d")

    async def test_saves_and_commits(self, wiring):
        fetcher, repo, session = wiring
        bo = MagicMock()
        fetcher.fetch_daily_basic.return_value = [bo, bo]
        result = await daily_basic.DailyBasicCollectTask().collect_one("20260930", {})
        assert result.success and result.saved_count == 5 and not result.skipped
        fetcher.fetch_daily_basic.assert_called_once_with("20260930")
        session.commit.assert_awaited_once()

    async def test_empty_is_skipped(self, wiring):
        fetcher, repo, _ = wiring
        fetcher.fetch_daily_basic.return_value = []
        result = await daily_basic.DailyBasicCollectTask().collect_one("20260927", {})
        assert result.skipped and result.success
        repo.save_batch.assert_not_called()


# ── stock_basic ──────────────────────────────────────────────────────


class TestStockBasic:
    async def test_returns_sync_response_as_data(self, monkeypatch):
        session = _Session()
        response = MagicMock(synced_count=5300, message="ok")
        response.model_dump.return_value = {"synced_count": 5300, "inserted": 3, "updated": 5297, "message": "ok"}
        svc = MagicMock()
        svc.sync_stocks = AsyncMock(return_value=response)
        monkeypatch.setattr(stock_basic, "get_registry", lambda: MagicMock())
        monkeypatch.setattr(stock_basic, "AsyncSessionLocal", lambda: session)
        monkeypatch.setattr(stock_basic, "StockAppService", lambda session: svc)

        task = stock_basic.StockBasicCollectTask()
        assert await task.list_units({}) == ["all"]
        result = await task.collect_one("all", {"list_status": "D"})
        assert result.saved_count == 5300 and result.data["inserted"] == 3
        assert svc.sync_stocks.call_args.kwargs["list_status"] == "D"
        session.commit.assert_awaited_once()


# ── daily_kline ──────────────────────────────────────────────────────


class TestDailyKline:
    def test_build_request_days(self):
        req = daily_kline.build_request("000001", {"days": 30})
        assert req.days == 30 and req.start_date is None

    @pytest.mark.parametrize("start, end", [
        ("20260101", "20260131"), ("2026-01-01", "2026-01-31"), (date(2026, 1, 1), date(2026, 1, 31)),
    ])
    def test_build_request_range(self, start, end):
        req = daily_kline.build_request("000001", {"start_date": start, "end_date": end, "days": 7})
        assert req.start_date == date(2026, 1, 1) and req.end_date == date(2026, 1, 31)

    async def test_list_units_symbols_param(self):
        task = daily_kline.DailyKlineCollectTask()
        assert await task.list_units({"symbols": ["1", "600519"]}) == ["000001", "600519"]

    async def test_collect_one_builds_service_with_repos(self, monkeypatch):
        session = _Session()
        built = {}

        class _Svc:
            def __init__(self, kline_repo, stock_repo):
                built["repos"] = (kline_repo, stock_repo)

            async def collect(self, request, fetcher):
                built["request"] = request
                resp = MagicMock(saved_count=7, total_count=7, message="成功采集 7 条")
                resp.model_dump.return_value = {"symbol": request.symbol, "saved_count": 7}
                return resp

        monkeypatch.setattr(daily_kline, "AsyncSessionLocal", lambda: session)
        monkeypatch.setattr(daily_kline, "KlineAppService", _Svc)
        monkeypatch.setattr(daily_kline, "KlineRepoImpl", lambda s: "kline_repo")
        monkeypatch.setattr(daily_kline, "StockRepoImpl", lambda s: "stock_repo")
        monkeypatch.setattr(daily_kline, "get_registry", lambda: MagicMock())

        result = await daily_kline.DailyKlineCollectTask().collect_one("600519", {"days": 5})
        assert built["repos"] == ("kline_repo", "stock_repo")
        assert built["request"].days == 5
        assert result.saved_count == 7 and result.data == {"symbol": "600519", "saved_count": 7}
        session.commit.assert_awaited_once()
