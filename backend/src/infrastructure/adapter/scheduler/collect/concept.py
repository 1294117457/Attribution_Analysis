"""概念采集任务（adata · 同花顺）

3 个任务，依赖顺序：
  concept（清单）→ concept_membership（成分股）
  concept（清单）→ concept_index_th（指数日 K）

概念实时行情不入库，见 infrastructure/adapter/realtime/concept_minute.py。
全链路以同花顺指数编码 index_code（885xxx）为业务键。

配套设计文档：
- docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.4
- docs/dev/step2/04采集管理优化/05接口优化.md
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Awaitable, Callable, Optional

from application.port.collector_port import ConceptFetcher
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    TaskSummary,
    UnitResult,
    UnitTally,
    run_units,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl

logger = logging.getLogger(__name__)

# 清单数量低于库中活跃数的该比例时，视为问财接口返回不全，不做下线
LIST_SHRINK_GUARD = 0.8
# 成分股数量骤降保护：旧数量超过 MIN 且新数量低于旧数量的该比例时，不替换
MEMBER_SHRINK_GUARD = 0.5
MEMBER_SHRINK_MIN = 20
# 失败单元重试时的请求间隔（秒），高于 fetcher 默认值以避开限频
RETRY_DELAY = 2.0
# 日 K 增量：重写库中最大日期往前 N 天，修正盘中写入的当日数据
INDEX_TH_OVERLAP_DAYS = 5


def _fetcher() -> ConceptFetcher:
    return get_registry().get(ConceptFetcher)


async def _active_concepts(params: dict) -> list[tuple[int, str, str]]:
    async with AsyncSessionLocal() as session:
        concepts = await ConceptRepoImpl(session).list_active_concepts()
    limit = params.get("limit")
    return concepts[: int(limit)] if limit else concepts


async def _run_units(
    task_id: int,
    units: list,
    label: Callable[[Any], str],
    work: Callable[[Any, Optional[float]], Awaitable[UnitResult]],
    on_unit_done,
) -> UnitTally:
    """概念任务的 work 把 delay 作为 fetcher 请求间隔使用，而不是先 sleep"""
    return await run_units(task_id, units, label, work, on_unit_done, retry_delay=RETRY_DELAY)


def _concept_label(c: tuple[int, str, str]) -> str:
    return f"{c[1]} {c[2]}"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 概念清单
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptListCollectTask(BaseCollectTask):
    """同花顺全部概念 → concepts（按 index_code upsert，清单消失的置不活跃）"""

    name = "concept"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念清单"
    sort_order = 1
    description = "同花顺全部概念（约 390 个），adata all_concept_code_ths"

    async def estimate_total(self, params: dict) -> int:
        return 1

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        bos, error = [], "问财接口返回空清单"
        for attempt in range(2):
            if attempt:
                await asyncio.sleep(RETRY_DELAY)
            try:
                bos = await asyncio.to_thread(_fetcher().fetch_concept_list)
            except Exception as e:
                error = str(e)[:500]
                continue
            if bos:
                break
        if not bos:
            logger.error("概念清单拉取失败: %s", error)
            await on_unit_done(UnitResult(success=False, detail="清单", error=error), "清单")
            return TaskSummary(success=0, fail=1, total_count=1, message=f"清单拉取失败: {error}")

        async with AsyncSessionLocal() as session:
            repo = ConceptRepoImpl(session)
            active_before = await repo.count_active()
            id_map = await repo.upsert_concepts(bos)
            shrunk = active_before > 0 and len(bos) < active_before * LIST_SHRINK_GUARD
            deactivated = 0 if shrunk else await repo.deactivate_missing(list(id_map.keys()))

        message = f"完成: 清单 {len(bos)} 个，下线 {deactivated} 个"
        if shrunk:
            message = f"清单疑似不全（{len(bos)} < 库中活跃 {active_before} × {LIST_SHRINK_GUARD}），仅更新未下线"
            logger.warning(message)
        await on_unit_done(UnitResult(success=True, detail="清单", saved_count=len(bos)), "清单")
        return TaskSummary(success=1, fail=0, total_count=1, message=message)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. 概念成分股
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptMembershipCollectTask(BaseCollectTask):
    """按概念拉成分股 → stock_concept_members（集合差替换，回填 stock_count）"""

    name = "concept_membership"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念成分股"
    sort_order = 2
    description = "按概念拉成分股并替换关系（保留已有入选理由），adata concept_constituent_ths"

    async def estimate_total(self, params: dict) -> int:
        return len(await _active_concepts(params))

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        """unit = 概念 index_code"""
        concept = next((c for c in await _active_concepts({}) if c[1] == unit), None)
        if concept is None:
            raise ValueError(f"概念 {unit} 不存在或已下线")
        result, _, _ = await self._collect_concept(_fetcher(), concept, None)
        return result

    async def _collect_concept(
        self, fetcher: ConceptFetcher, c: tuple[int, str, str], delay: Optional[float],
    ) -> tuple[UnitResult, int, int]:
        """返回 (结果, 新增关系数, 移除关系数)"""
        concept_id, index_code, name = c
        symbols = await asyncio.to_thread(fetcher.fetch_constituents, index_code, delay)
        label = _concept_label(c)
        if not symbols:
            return UnitResult(success=True, skipped=True, detail=f"{label}：接口返回空，保留旧关系"), 0, 0
        async with AsyncSessionLocal() as session:
            repo = ConceptRepoImpl(session)
            old = await repo.count_members(concept_id)
            if old > MEMBER_SHRINK_MIN and len(symbols) < old * MEMBER_SHRINK_GUARD:
                return UnitResult(
                    success=True, skipped=True,
                    detail=f"{label}：成分股 {old} → {len(symbols)} 疑似不全，保留旧关系",
                ), 0, 0
            added, removed = await repo.replace_members(concept_id, symbols)
        return UnitResult(success=True, detail=label, saved_count=len(symbols)), added, removed

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await _active_concepts(params)
        fetcher = _fetcher()
        added_total = removed_total = 0

        async def work(c: tuple[int, str, str], delay: Optional[float]) -> UnitResult:
            nonlocal added_total, removed_total
            result, added, removed = await self._collect_concept(fetcher, c, delay)
            added_total += added
            removed_total += removed
            return result

        tally = await _run_units(self._task_id, concepts, _concept_label, work, on_unit_done)
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(concepts),
            message=(
                f"完成: 概念 {tally.success}（跳过 {tally.skip}），失败 {tally.fail}；"
                f"关系 {tally.saved} 条，新增 {added_total}，移除 {removed_total}"
            ),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. 概念指数日 K
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptIndexTHCollectTask(BaseCollectTask):
    """概念指数日 K → concept_index_ths（默认增量，params.full=true 全量重写）"""

    name = "concept_index_th"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念指数日 K"
    sort_order = 3
    description = "概念指数日 K + 涨跌幅（全部历史），adata get_market_concept_ths"

    async def estimate_total(self, params: dict) -> int:
        return len(await _active_concepts(params))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await _active_concepts(params)
        fetcher = _fetcher()
        full = bool(params.get("full"))
        async with AsyncSessionLocal() as session:
            max_dates = {} if full else await ConceptRepoImpl(session).get_max_trade_dates()

        async def work(c: tuple[int, str, str], delay: Optional[float]) -> UnitResult:
            _, index_code, name = c
            bos = await asyncio.to_thread(fetcher.fetch_index_daily, index_code, name, delay)
            last = max_dates.get(index_code)
            if last is not None:
                cutoff = last - timedelta(days=INDEX_TH_OVERLAP_DAYS)
                bos = [b for b in bos if b.trade_date > cutoff]
            if not bos:
                return UnitResult(success=True, skipped=True, detail=_concept_label(c))
            async with AsyncSessionLocal() as session:
                written = await ConceptRepoImpl(session).upsert_index_th(bos)
            return UnitResult(success=True, detail=_concept_label(c), saved_count=written)

        tally = await _run_units(self._task_id, concepts, _concept_label, work, on_unit_done)
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(concepts),
            message=(
                f"完成({'全量' if full else '增量'}): 概念 {tally.success}，失败 {tally.fail}；"
                f"写入 {tally.saved} 行"
            ),
        )


__all__ = [
    "ConceptListCollectTask",
    "ConceptMembershipCollectTask",
    "ConceptIndexTHCollectTask",
]
