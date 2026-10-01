"""财报（利润表）采集单元测试

  · Fetcher：同报告期多行去重（update_flag / f_ann_date）、字段解析、限频转 RateLimitError
  · 任务：空结果跳过、首轮失败后重试、限频等待后重试、取消、only_missing / limit
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pandas as pd
import pytest

from application.port.collector_port import RateLimitError
from infrastructure.adapter.scheduler.collect import fin_report as mod
from infrastructure.adapter.scheduler.collect.base import Cancelled, clear_cancel, request_cancel
from infrastructure.adapter.fetcher.tushare import TushareFetcher, dedupe_income, symbol_to_ts_code
from route.dto.request.fin_report import FinReportBO

TASK_ID = 5151


def _income_df(rows: list[dict]) -> pd.DataFrame:
    base = {
        "ts_code": "600519.SH", "ann_date": "20260815", "f_ann_date": "20260815",
        "end_date": "20260630", "report_type": "1", "comp_type": "1",
        "basic_eps": 35.4, "diluted_eps": 35.4, "total_revenue": 9.2e10, "revenue": 9.07e10,
        "operate_profit": 6.1e10, "total_profit": 6.1e10, "n_income": 4.6e10, "n_income_attr_p": 4.45e10,
        "update_flag": "1",
    }
    return pd.DataFrame([{**base, **r} for r in rows])


def _fetcher_with(pro) -> TushareFetcher:
    f = object.__new__(TushareFetcher)
    f._pro = pro
    return f


# ── Fetcher ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("symbol, ts_code", [
    ("600519", "600519.SH"), ("688981", "688981.SH"), ("000001", "000001.SZ"),
    ("300750", "300750.SZ"), ("430047", "430047.BJ"), ("830799", "830799.BJ"), ("920000", "920000.BJ"),
])
def test_symbol_to_ts_code(symbol, ts_code):
    assert symbol_to_ts_code(symbol) == ts_code


class TestDedupe:
    def test_prefers_update_flag_1(self):
        df = _income_df([{"update_flag": "0", "n_income": 1.0}, {"update_flag": "1", "n_income": 2.0}])
        out = dedupe_income(df)
        assert len(out) == 1 and out.iloc[0]["n_income"] == 2.0

    def test_falls_back_to_latest_f_ann_date(self):
        df = _income_df([
            {"update_flag": None, "f_ann_date": "20260801", "n_income": 1.0},
            {"update_flag": None, "f_ann_date": "20260901", "n_income": 2.0},
        ])
        out = dedupe_income(df)
        assert len(out) == 1 and out.iloc[0]["n_income"] == 2.0

    def test_keeps_distinct_periods(self):
        df = _income_df([{"end_date": "20260630"}, {"end_date": "20260331"}, {"end_date": "20260331", "update_flag": "0"}])
        assert sorted(dedupe_income(df)["end_date"]) == ["20260331", "20260630"]


class TestFetchIncome:
    def test_parses_rows(self):
        pro = MagicMock()
        pro.income.return_value = _income_df([{}, {"update_flag": "0"}, {"end_date": "20260331", "revenue": None}])
        bos = _fetcher_with(pro).fetch_income("600519.SH", start_date="20250101")

        assert [b.end_date for b in bos] == [date(2026, 6, 30), date(2026, 3, 31)]
        assert bos[0].symbol == "600519" and bos[0].report_type == "1" and bos[0].n_income == 4.6e10
        assert bos[1].revenue is None
        kwargs = pro.income.call_args.kwargs
        assert kwargs["report_type"] == "1" and kwargs["start_date"] == "20250101"

    def test_empty_returns_empty_list(self):
        pro = MagicMock()
        pro.income.return_value = pd.DataFrame()
        assert _fetcher_with(pro).fetch_income("600519.SH") == []

    def test_rate_limit_error(self):
        pro = MagicMock()
        pro.income.side_effect = Exception("抱歉，您每分钟最多访问该接口200次")
        with pytest.raises(RateLimitError):
            _fetcher_with(pro).fetch_income("600519.SH")

    def test_other_error_raises(self):
        pro = MagicMock()
        pro.income.side_effect = Exception("network down")
        with pytest.raises(RuntimeError, match="network down"):
            _fetcher_with(pro).fetch_income("600519.SH")


# ── 任务 ─────────────────────────────────────────────────────────────


class FakeRepo:
    def __init__(self):
        self.saved: list = []
        self.existing: set[str] = set()

    async def save_batch(self, entities):
        self.saved.extend(entities)
        return len(entities)

    async def list_symbols_with_reports(self):
        return self.existing


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, stmt):
        result = MagicMock()
        result.all.return_value = [("000001",), ("600000",), ("600519",)]
        return result


class _Reporter:
    def __init__(self):
        self.calls: list = []

    async def __call__(self, result, label):
        self.calls.append((result, label))


@pytest.fixture
def repo():
    return FakeRepo()


@pytest.fixture
def fetcher():
    return MagicMock()


@pytest.fixture(autouse=True)
def wiring(monkeypatch, repo, fetcher):
    registry = MagicMock()
    registry.get.return_value = fetcher
    monkeypatch.setattr(mod, "get_registry", lambda: registry)
    monkeypatch.setattr(mod, "AsyncSessionLocal", lambda: _Session())
    monkeypatch.setattr(mod, "FinReportRepoImpl", lambda session: repo)
    monkeypatch.setattr(mod.FinReportCollectTask, "retry_delay", 0)
    monkeypatch.setattr(mod, "RATE_LIMIT_WAIT", 0)
    yield
    clear_cancel(TASK_ID)


def _task() -> mod.FinReportCollectTask:
    t = mod.FinReportCollectTask()
    t._task_id = TASK_ID
    return t


def _bo(symbol: str) -> FinReportBO:
    return FinReportBO(symbol=symbol, end_date=date(2026, 6, 30), report_type="1", revenue=100.0, n_income=10.0)


class TestFinReportTask:
    async def test_saves_and_skips_empty(self, repo, fetcher):
        fetcher.fetch_income.side_effect = lambda ts_code, start: [] if ts_code == "000001.SZ" else [_bo(ts_code[:6])]
        summary = await _task().run({}, _Reporter())

        assert summary.success == 3 and summary.skip == 1 and summary.fail == 0
        assert sorted(e.symbol for e in repo.saved) == ["600000", "600519"]
        assert all(e.n_income == 10.0 for e in repo.saved)

    async def test_default_start_date_is_one_year(self, fetcher):
        fetcher.fetch_income.return_value = []
        await _task().run({"symbol": "600519"}, _Reporter())
        ts_code, start = fetcher.fetch_income.call_args.args
        assert ts_code == "600519.SH"
        assert (date.today() - date(int(start[:4]), int(start[4:6]), int(start[6:]))).days == 365

    async def test_failure_retried_once_at_end(self, fetcher):
        calls: list[str] = []

        def fake(ts_code, start):
            calls.append(ts_code)
            if ts_code == "600000.SH" and calls.count(ts_code) == 1:
                raise RuntimeError("timeout")
            return [_bo(ts_code[:6])]

        fetcher.fetch_income.side_effect = fake
        reporter = _Reporter()
        summary = await _task().run({}, reporter)

        assert summary.success == 3 and summary.fail == 0
        assert calls == ["000001.SZ", "600000.SH", "600519.SH", "600000.SH"]
        assert [label for _, label in reporter.calls] == ["000001", "600519", "600000"]

    async def test_retry_still_failing_counts_fail(self, fetcher):
        fetcher.fetch_income.side_effect = RuntimeError("boom")
        summary = await _task().run({"limit": 1}, _Reporter())
        assert summary.fail == 1 and fetcher.fetch_income.call_count == 2

    async def test_rate_limit_waits_and_retries_same_unit(self, fetcher):
        fetcher.fetch_income.side_effect = [RateLimitError("每分钟最多访问"), [_bo("000001")]]
        summary = await _task().run({"limit": 1}, _Reporter())
        assert summary.success == 1 and fetcher.fetch_income.call_count == 2

    async def test_only_missing_and_limit(self, repo, fetcher):
        repo.existing = {"000001"}
        fetcher.fetch_income.return_value = []
        task = _task()
        assert await task.estimate_total({"only_missing": True}) == 2
        assert await task.estimate_total({"only_missing": True, "limit": 1}) == 1

    async def test_cancel(self, fetcher):
        fetcher.fetch_income.return_value = []
        request_cancel(TASK_ID)
        with pytest.raises(Cancelled):
            await _task().run({}, _Reporter())
