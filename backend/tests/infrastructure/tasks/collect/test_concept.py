"""概念采集任务单元测试（adata · 同花顺）

fetcher / 仓储 / session 全部替换为内存假对象，验证：
  · 清单：正常下线 / 清单骤减时不下线
  · 成分股：空结果跳过 / 骤降保护 / 首轮失败后重试 / 取消
  · 指数日 K：增量按最大日期往前 5 天截断
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from infrastructure.adapter.scheduler.collect import concept as mod
from infrastructure.adapter.scheduler.collect.base import Cancelled, clear_cancel, request_cancel
from route.dto.request.concept import ConceptIndexTHBO, ConceptListBO

TASK_ID = 4242


class FakeRepo:
    def __init__(self):
        self.active = [(1, "885001", "机器人"), (2, "885002", "算力"), (3, "885003", "白酒")]
        self.members: dict[int, set[str]] = {1: set(), 2: set(), 3: set()}
        self.upserted: list = []
        self.deactivated_with: list | None = None
        self.index_rows: list = []
        self.max_dates: dict = {}

    async def count_active(self):
        return len(self.active)

    async def upsert_concepts(self, bos):
        self.upserted = bos
        return {b.index_code: i for i, b in enumerate(bos, 1)}

    async def deactivate_missing(self, codes):
        self.deactivated_with = codes
        return 1

    async def list_active_concepts(self):
        return list(self.active)

    async def count_members(self, concept_id):
        return len(self.members[concept_id])

    async def replace_members(self, concept_id, symbols):
        old = self.members[concept_id]
        new = set(symbols)
        self.members[concept_id] = new
        return len(new - old), len(old - new)

    async def get_max_trade_dates(self):
        return self.max_dates

    async def upsert_index_th(self, bos):
        self.index_rows.extend(bos)
        return len(bos)


class _Session:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def repo():
    return FakeRepo()


@pytest.fixture
def fetcher():
    return MagicMock()


@pytest.fixture(autouse=True)
def wiring(monkeypatch, repo, fetcher):
    monkeypatch.setattr(mod, "AsyncSessionLocal", lambda: _Session())
    monkeypatch.setattr(mod, "ConceptRepoImpl", lambda session: repo)
    monkeypatch.setattr(mod, "_fetcher", lambda: fetcher)
    yield
    clear_cancel(TASK_ID)


def _task(cls):
    t = cls()
    t._task_id = TASK_ID
    return t


class _Reporter:
    def __init__(self):
        self.calls: list = []

    async def __call__(self, result, label):
        self.calls.append((result, label))


# ── 清单 ─────────────────────────────────────────────────────────────


class TestConceptList:
    async def test_normal_list_deactivates_missing(self, repo, fetcher):
        fetcher.fetch_concept_list.return_value = [
            ConceptListBO(index_code=f"88500{i}", name=f"概念{i}") for i in range(1, 4)
        ]
        summary = await _task(mod.ConceptListCollectTask).run({}, _Reporter())
        assert summary.success == 1
        assert repo.deactivated_with == ["885001", "885002", "885003"]

    async def test_shrunk_list_skips_deactivation(self, repo, fetcher):
        repo.active = [(i, f"8850{i:02d}", "x") for i in range(10)]
        fetcher.fetch_concept_list.return_value = [ConceptListBO(index_code="885001", name="仅一个")]
        summary = await _task(mod.ConceptListCollectTask).run({}, _Reporter())
        assert repo.deactivated_with is None
        assert "疑似不全" in summary.message

    async def test_fetch_failure_reports_fail(self, monkeypatch, fetcher):
        monkeypatch.setattr(mod, "RETRY_DELAY", 0)
        fetcher.fetch_concept_list.side_effect = RuntimeError("iwencai down")
        reporter = _Reporter()
        summary = await _task(mod.ConceptListCollectTask).run({}, reporter)
        assert summary.fail == 1
        assert reporter.calls[0][0].success is False
        assert fetcher.fetch_concept_list.call_count == 2

    async def test_empty_list_retried_then_ok(self, monkeypatch, repo, fetcher):
        monkeypatch.setattr(mod, "RETRY_DELAY", 0)
        fetcher.fetch_concept_list.side_effect = [[], [ConceptListBO(index_code="885001", name="机器人")]]
        summary = await _task(mod.ConceptListCollectTask).run({}, _Reporter())
        assert summary.success == 1 and len(repo.upserted) == 1

    async def test_empty_list_twice_is_fail(self, monkeypatch, repo, fetcher):
        monkeypatch.setattr(mod, "RETRY_DELAY", 0)
        fetcher.fetch_concept_list.return_value = []
        summary = await _task(mod.ConceptListCollectTask).run({}, _Reporter())
        assert summary.fail == 1 and repo.deactivated_with is None


# ── 成分股 ───────────────────────────────────────────────────────────


class TestConceptMembership:
    async def test_replace_and_skip_empty(self, repo, fetcher):
        fetcher.fetch_constituents.side_effect = lambda code, delay: {
            "885001": ["600001", "600002"],
            "885002": [],
            "885003": ["600519"],
        }[code]
        summary = await _task(mod.ConceptMembershipCollectTask).run({}, _Reporter())
        assert summary.success == 3 and summary.skip == 1 and summary.fail == 0
        assert repo.members[1] == {"600001", "600002"}
        assert "关系 3 条" in summary.message

    async def test_shrink_guard_keeps_old_members(self, repo, fetcher):
        repo.members[1] = {f"{i:06d}" for i in range(100)}
        fetcher.fetch_constituents.side_effect = lambda code, delay: ["600001"]
        await _task(mod.ConceptMembershipCollectTask).run({"limit": 1}, _Reporter())
        assert len(repo.members[1]) == 100

    async def test_first_failure_is_retried_with_longer_delay(self, repo, fetcher):
        attempts: list = []

        def flaky(code, delay):
            attempts.append((code, delay))
            if code == "885002" and delay is None:
                raise RuntimeError("throttled")
            return ["600001"]

        fetcher.fetch_constituents.side_effect = flaky
        reporter = _Reporter()
        summary = await _task(mod.ConceptMembershipCollectTask).run({}, reporter)
        assert summary.fail == 0 and summary.success == 3
        assert ("885002", mod.RETRY_DELAY) in attempts
        assert len(reporter.calls) == 3

    async def test_retry_failure_counts_as_fail(self, fetcher):
        fetcher.fetch_constituents.side_effect = RuntimeError("down")
        summary = await _task(mod.ConceptMembershipCollectTask).run({"limit": 2}, _Reporter())
        assert summary.fail == 2 and summary.success == 0

    async def test_cancel(self, fetcher):
        fetcher.fetch_constituents.return_value = ["600001"]
        request_cancel(TASK_ID)
        with pytest.raises(Cancelled):
            await _task(mod.ConceptMembershipCollectTask).run({}, _Reporter())


# ── 指数日 K ─────────────────────────────────────────────────────────


def _daily(code, d):
    return ConceptIndexTHBO(index_code=code, trade_date=d, close=1000.0)


class TestConceptIndexTH:
    async def test_incremental_keeps_overlap_window(self, repo, fetcher):
        last = date(2026, 9, 25)
        repo.active = repo.active[:1]
        repo.max_dates = {"885001": last}
        fetcher.fetch_index_daily.return_value = [_daily("885001", last - timedelta(days=i)) for i in range(30)]
        await _task(mod.ConceptIndexTHCollectTask).run({}, _Reporter())
        assert min(b.trade_date for b in repo.index_rows) == last - timedelta(days=mod.INDEX_TH_OVERLAP_DAYS - 1)

    async def test_full_writes_everything(self, repo, fetcher):
        repo.active = repo.active[:1]
        repo.max_dates = {"885001": date(2026, 9, 25)}
        fetcher.fetch_index_daily.return_value = [_daily("885001", date(2020, 1, 1) + timedelta(days=i)) for i in range(30)]
        await _task(mod.ConceptIndexTHCollectTask).run({"full": True}, _Reporter())
        assert len(repo.index_rows) == 30


def test_task_metadata():
    tasks = [mod.ConceptListCollectTask, mod.ConceptMembershipCollectTask, mod.ConceptIndexTHCollectTask]
    assert [t.name for t in tasks] == ["concept", "concept_membership", "concept_index_th"]
    assert {(t.facet, t.sub_facet) for t in tasks} == {("fundamental", "concept")}


def test_catalog_groups_concepts_in_user_order(monkeypatch):
    from infrastructure.adapter.realtime import registry as rt_registry
    from infrastructure.adapter.realtime.concept_minute import ConceptMinuteQuery
    from infrastructure.adapter.scheduler.collect.registry import CollectTaskRegistry

    monkeypatch.setattr(rt_registry, "_registry", None)
    rt_registry.setup_realtime_registry([ConceptMinuteQuery()])

    registry = CollectTaskRegistry()
    for cls in (mod.ConceptIndexTHCollectTask, mod.ConceptMembershipCollectTask, mod.ConceptListCollectTask):
        registry.register(cls.name, cls())
    tasks = registry.catalog()[0].sub_groups["concept"]
    assert [t.label for t in tasks] == ["概念清单", "概念成分股", "概念指数日 K", "概念实时行情"]
    assert [t.kind for t in tasks] == ["batch", "batch", "batch", "realtime"]
