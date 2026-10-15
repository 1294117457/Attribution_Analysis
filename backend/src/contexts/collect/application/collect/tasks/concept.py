"""概念采集任务（adata · 同花顺）

3 个任务，依赖顺序：
  concept（清单）→ concept_membership（成分股）
  concept（清单）→ concept_index_th（指数日 K）

概念实时行情不入库，见 application/service/concept_realtime.py。
全链路以同花顺指数编码 index_code（885xxx）为业务键。
取数经 DataGateway（限速 / 重试由横向装饰器负责）。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Awaitable, Callable

from contexts.collect.application.collect.task import (
    RETRY_DELAY,
    BaseCollectTask,
    TaskSummary,
    UnitResult,
    UnitTally,
    run_units,
)
from contexts.data.application.port.concept import (
    ConceptIndexDailyPort,
    ConceptListPort,
    ConceptMembersPort,
)
from contexts.collect.domain.services.concept_collection_policy import ConceptCollectionPolicy

logger = logging.getLogger(__name__)


# 清单缩量保护阈值（与领域常量保持一致，保留为模块级常量以便历史 grep）
LIST_SHRINK_GUARD = 0.8
# 成分股骤降保护阈值
MEMBER_SHRINK_GUARD = 0.5
MEMBER_SHRINK_MIN = 20
# 日 K 增量：重写库中最大日期往前 N 天，修正盘中写入的当日数据
INDEX_TH_OVERLAP_DAYS = 5

# 领域策略（注入同一进程，保证导入期间无副作用）
_COLLECTION_POLICY = ConceptCollectionPolicy(
    list_shrink_guard=LIST_SHRINK_GUARD,
    member_shrink_min=MEMBER_SHRINK_MIN,
    member_shrink_guard=MEMBER_SHRINK_GUARD,
)


def _concept_label(c: tuple[int, str, str]) -> str:
    return f"{c[1]} {c[2]}"


async def _run_units(
    task_id: int,
    units: list,
    label: Callable[[object], str],
    work: Callable[[object], Awaitable[UnitResult]],
    on_unit_done,
) -> UnitTally:
    async def spaced(unit: object, delay: float | None) -> UnitResult:
        if delay:
            await asyncio.sleep(delay)
        return await work(unit)

    return await run_units(task_id, units, label, spaced, on_unit_done, retry_delay=RETRY_DELAY)


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
                bos = (await self.ctx.gateway.fetch(ConceptListPort, {})).items
            except Exception as e:
                error = str(e)[:500]
                continue
            if bos:
                break
        if not bos:
            logger.error("概念清单拉取失败: %s", error)
            await on_unit_done(UnitResult(success=False, detail="清单", error=error), "清单")
            return TaskSummary(success=0, fail=1, total_count=1, message=f"清单拉取失败: {error}")

        active_before = await self.ctx.concepts.count_active()
        id_map = await self.ctx.concepts.upsert_concepts(bos)
        shrunk = _COLLECTION_POLICY.should_skip_list_update(
            old_active_count=active_before,
            new_listing_count=len(bos),
        )
        deactivated = 0 if shrunk else await self.ctx.concepts.deactivate_missing(list(id_map.keys()))

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
        return len(await self.ctx.concepts.list_active_concepts())

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        """unit = 概念 index_code"""
        concept = next(
            (c for c in await self.ctx.concepts.list_active_concepts() if c[1] == unit),
            None,
        )
        if concept is None:
            raise ValueError(f"概念 {unit} 不存在或已下线")
        result, _, _ = await self._collect_concept(concept)
        return result

    async def _collect_concept(self, c: tuple[int, str, str]) -> tuple[UnitResult, int, int]:
        """返回 (结果, 新增关系数, 移除关系数)"""
        concept_id, index_code, name = c
        members = (await self.ctx.gateway.fetch(
            ConceptMembersPort, {"index_code": index_code},
        )).items
        symbols = [m.symbol for m in members]
        label = _concept_label(c)
        if not symbols:
            return UnitResult(success=True, skipped=True, detail=f"{label}：接口返回空，保留旧关系"), 0, 0
        old = await self.ctx.concepts.count_members(concept_id)
        if _COLLECTION_POLICY.should_skip_member_sync(
            old_member_count=old,
            new_member_count=len(symbols),
        ):
            return UnitResult(
                success=True, skipped=True,
                detail=f"{label}：成分股 {old} → {len(symbols)} 疑似不全，保留旧关系",
            ), 0, 0
        added, removed = await self.ctx.concepts.replace_members(concept_id, symbols)
        return UnitResult(success=True, detail=label, saved_count=len(symbols)), added, removed

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await self.ctx.concepts.list_active_concepts()
        added_total = removed_total = 0

        async def work(c: tuple[int, str, str]) -> UnitResult:
            nonlocal added_total, removed_total
            result, added, removed = await self._collect_concept(c)
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
        return len(await self.ctx.concepts.list_active_concepts())

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await self.ctx.concepts.list_active_concepts()
        full = bool(params.get("full"))
        max_dates = {} if full else await self.ctx.concepts.get_max_trade_dates()

        async def work(c: tuple[int, str, str]) -> UnitResult:
            _, index_code, name = c
            bos = (await self.ctx.gateway.fetch(
                ConceptIndexDailyPort, {"index_code": index_code, "concept_name": name},
            )).items
            last = max_dates.get(index_code)
            if last is not None:
                cutoff = last - timedelta(days=INDEX_TH_OVERLAP_DAYS)
                bos = [b for b in bos if b.trade_date > cutoff]
            if not bos:
                return UnitResult(success=True, skipped=True, detail=_concept_label(c))
            written = await self.ctx.concepts.upsert_index_th(bos)
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
    "ConceptIndexTHCollectTask",
    "ConceptListCollectTask",
    "ConceptMembershipCollectTask",
]
