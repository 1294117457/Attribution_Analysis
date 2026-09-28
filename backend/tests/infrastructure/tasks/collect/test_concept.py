"""概念采集任务单元测试（adata · 同花顺）

fetcher / 仓储 / session 全部替换为内存假对象，验证：
  · 清单：正常下线 / 清单骤减时不下线
  · 成分股：空结果跳过 / 骤降保护 / 首轮失败后重试 / 取消
  · 入选理由：只按库中已有的 index_code 更新
  · 指数日 K：增量按最大日期往前 5 天截断
  · 快照：昨收算涨跌幅、批次内排名、缺昨收时 pct 为 None
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from infrastructure.adapter.scheduler.collect import concept as mod
from infrastructure.adapter.scheduler.collect.base import Cancelled, clear_cancel, request_cancel
from route.dto.request.concept import (
    ConceptCurrentBO,
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptOfStockBO,
)

TASK_ID = 4242


class FakeRepo:
    def __init__(self):
        self.active = [(1, "885001", "机器人"), (2, "885002", "算力"), (3, "885003", "白酒")]
        self.members: dict[int, set[str]] = {1: set(), 2: set(), 3: set()}
        self.upserted: list = []
        self.deactivated_with: list | None = None
        self.reasons: list = []
        self.index_rows: list = []
        self.max_dates: dict = {}
        self.prev_closes: dict = {}
        self.snapshots: list = []

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

    async def concept_id_map(self):
        return {code: cid for cid, code, _ in self.active}

    async def count_members(self, concept_id):
        return len(self.members[concept_id])

    async def replace_members(self, concept_id, symbols):
        old = self.members[concept_id]
        new = set(symbols)
        self.members[concept_id] = new
        return len(new - old), len(old - new)

    async def list_member_symbols(self, only_missing_reason=False):
        return ["600519", "000001"]

    async def update_reasons(self, symbol, pairs):
        self.reasons.append((symbol, pairs))
        return len(pairs)

    async def get_max_trade_dates(self):
        return self.max_dates

    async def upsert_index_th(self, bos):
        self.index_rows.extend(bos)
        return len(bos)

    async def get_prev_closes(self, before):
        return self.prev_closes

    async def insert_snapshots(self, bos):
        self.snapshots = bos
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


# ── 入选理由 ─────────────────────────────────────────────────────────


class TestConceptReason:
    async def test_only_known_codes_updated(self, repo, fetcher):
        fetcher.fetch_concepts_by_stock.side_effect = lambda symbol, delay: [
            ConceptOfStockBO(symbol=symbol, index_code="885003", name="白酒", reason="白酒龙头"),
            ConceptOfStockBO(symbol=symbol, index_code="889999", name="未知", reason="不在库中"),
            ConceptOfStockBO(symbol=symbol, index_code="885001", name="机器人", reason=None),
        ]
        summary = await _task(mod.ConceptReasonCollectTask).run({}, _Reporter())
        assert repo.reasons == [("600519", [(3, "白酒龙头")]), ("000001", [(3, "白酒龙头")])]
        assert "更新理由 2 条" in summary.message


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


# ── 快照 ─────────────────────────────────────────────────────────────


class TestConceptSnapshot:
    async def test_pct_rank_and_units(self, repo, fetcher):
        repo.prev_closes = {"885001": 100.0, "885002": 200.0}
        t = datetime(2026, 9, 28, 14, 30)
        prices = {"885001": 102.0, "885002": 198.0, "885003": 50.0}
        fetcher.fetch_current.side_effect = lambda code, delay: ConceptCurrentBO(
            index_code=code, trade_time=t, price=prices[code], volume=2_000_000, amount=3e8,
        )
        summary = await _task(mod.ConceptSnapshotCollectTask).run({}, _Reporter())

        by_code = {b.index_code: b for b in repo.snapshots}
        assert by_code["885001"].pct_change == 2.0
        assert by_code["885002"].pct_change == -1.0
        assert by_code["885003"].pct_change is None
        assert (by_code["885001"].rank_current, by_code["885001"].rank_total) == (1, 2)
        assert by_code["885002"].rank_current == 2
        assert by_code["885003"].rank_current is None
        assert by_code["885001"].volume_wan == 2.0
        assert by_code["885001"].turnover_yi == 3.0
        assert "缺昨收" in summary.message

    async def test_no_quote_is_skipped(self, repo, fetcher):
        fetcher.fetch_current.return_value = None
        summary = await _task(mod.ConceptSnapshotCollectTask).run({}, _Reporter())
        assert summary.skip == 3 and repo.snapshots == []


def test_task_metadata():
    tasks = [
        mod.ConceptListCollectTask, mod.ConceptMembershipCollectTask, mod.ConceptReasonCollectTask,
        mod.ConceptIndexTHCollectTask, mod.ConceptSnapshotCollectTask,
    ]
    assert [t.name for t in tasks] == [
        "concept", "concept_membership", "concept_reason", "concept_index_th", "concept_snapshot",
    ]
    assert {(t.facet, t.sub_facet) for t in tasks} == {("fundamental", "concept")}


def test_catalog_groups_concepts_in_user_order():
    from infrastructure.adapter.scheduler.collect.registry import CollectTaskRegistry

    registry = CollectTaskRegistry()
    for cls in (
        mod.ConceptSnapshotCollectTask, mod.ConceptMembershipCollectTask, mod.ConceptListCollectTask,
        mod.ConceptIndexTHCollectTask, mod.ConceptReasonCollectTask,
    ):
        registry.register(cls.name, cls())
    catalog = registry.catalog()
    assert [g.facet for g in catalog] == ["fundamental"]
    assert [t.label for t in catalog[0].sub_groups["concept"]] == [
        "概念清单", "概念入选理由", "概念成分股", "概念指数日 K", "概念行情快照",
    ]
