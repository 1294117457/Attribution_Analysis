"""概念采集任务（adata · 同花顺）

5 个任务，依赖顺序：
  concept（清单）→ concept_membership（成分股）→ concept_reason（入选理由）
  concept（清单）→ concept_index_th（指数日 K）→ concept_snapshot（行情快照）

全链路以同花顺指数编码 index_code（885xxx）为业务键。

配套设计文档：docs/dev/step2/02datamanage/04-概念数据adata同源改造方案.md §5.4
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Optional

from application.port.collector_port import ConceptFetcher
from infrastructure.adapter import get_registry
from infrastructure.adapter.scheduler.collect.base import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    is_cancelled,
)
from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl
from route.dto.request.concept import ConceptSnapshotBO

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


@dataclass
class _Tally:
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0


async def _run_units(
    task_id: int,
    units: list,
    label: Callable[[Any], str],
    work: Callable[[Any, Optional[float]], Awaitable[UnitResult]],
    on_unit_done,
) -> _Tally:
    """逐单元执行；抛异常的单元先挂起，主循环结束后以 RETRY_DELAY 间隔再试一轮

    挂起的单元在重试结束后才上报，避免进度被重复计数。
    """
    tally = _Tally()
    pending: list = []

    async def report(unit, result: UnitResult) -> None:
        if result.success:
            tally.success += 1
            tally.saved += result.saved_count
            if result.skipped:
                tally.skip += 1
        else:
            tally.fail += 1
        await on_unit_done(result, label(unit))

    for unit in units:
        if is_cancelled(task_id):
            raise Cancelled()
        try:
            result = await work(unit, None)
        except Cancelled:
            raise
        except Exception as e:
            logger.debug("单元 %s 失败，稍后重试: %s", label(unit), e)
            pending.append(unit)
            continue
        await report(unit, result)

    if pending:
        logger.info("任务 %d：%d 个单元首轮失败，间隔 %.1fs 重试", task_id, len(pending), RETRY_DELAY)
    for unit in pending:
        if is_cancelled(task_id):
            raise Cancelled()
        try:
            result = await work(unit, RETRY_DELAY)
        except Cancelled:
            raise
        except Exception as e:
            logger.warning("单元 %s 重试仍失败: %s", label(unit), str(e)[:200])
            result = UnitResult(success=False, detail=label(unit), error=str(e)[:500])
        await report(unit, result)

    return tally


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
    sort_order = 3
    description = "按概念拉成分股并替换关系（保留入选理由），adata concept_constituent_ths"

    async def estimate_total(self, params: dict) -> int:
        return len(await _active_concepts(params))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await _active_concepts(params)
        fetcher = _fetcher()
        added_total = removed_total = 0

        async def work(c: tuple[int, str, str], delay: Optional[float]) -> UnitResult:
            nonlocal added_total, removed_total
            concept_id, index_code, name = c
            symbols = await asyncio.to_thread(fetcher.fetch_constituents, index_code, delay)
            label = _concept_label(c)
            if not symbols:
                return UnitResult(success=True, skipped=True, detail=f"{label}：接口返回空，保留旧关系")
            async with AsyncSessionLocal() as session:
                repo = ConceptRepoImpl(session)
                old = await repo.count_members(concept_id)
                if old > MEMBER_SHRINK_MIN and len(symbols) < old * MEMBER_SHRINK_GUARD:
                    return UnitResult(
                        success=True, skipped=True,
                        detail=f"{label}：成分股 {old} → {len(symbols)} 疑似不全，保留旧关系",
                    )
                added, removed = await repo.replace_members(concept_id, symbols)
            added_total += added
            removed_total += removed
            return UnitResult(success=True, detail=label, saved_count=len(symbols))

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
# 3. 入选理由
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptReasonCollectTask(BaseCollectTask):
    """按股票拉所属概念的入选理由 → stock_concept_members.reason（只更新，不新增关系）"""

    name = "concept_reason"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念入选理由"
    sort_order = 2
    description = "按股票补充每个概念的入选理由，adata get_concept_ths；先跑概念成分股"

    async def _symbols(self, params: dict) -> list[str]:
        async with AsyncSessionLocal() as session:
            symbols = await ConceptRepoImpl(session).list_member_symbols(
                only_missing_reason=bool(params.get("only_missing")),
            )
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols

    async def estimate_total(self, params: dict) -> int:
        return len(await self._symbols(params))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        symbols = await self._symbols(params)
        fetcher = _fetcher()
        async with AsyncSessionLocal() as session:
            id_map = await ConceptRepoImpl(session).concept_id_map()

        async def work(symbol: str, delay: Optional[float]) -> UnitResult:
            bos = await asyncio.to_thread(fetcher.fetch_concepts_by_stock, symbol, delay)
            pairs = [(id_map[b.index_code], b.reason) for b in bos if b.reason and b.index_code in id_map]
            if not pairs:
                return UnitResult(success=True, skipped=True, detail=symbol)
            async with AsyncSessionLocal() as session:
                updated = await ConceptRepoImpl(session).update_reasons(symbol, pairs)
            return UnitResult(success=True, detail=symbol, saved_count=updated)

        tally = await _run_units(self._task_id, symbols, str, work, on_unit_done)
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(symbols),
            message=f"完成: 股票 {tally.success}（无理由 {tally.skip}），失败 {tally.fail}；更新理由 {tally.saved} 条",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 4. 概念指数日 K
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptIndexTHCollectTask(BaseCollectTask):
    """概念指数日 K → concept_index_ths（默认增量，params.full=true 全量重写）"""

    name = "concept_index_th"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念指数日 K"
    sort_order = 4
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


# ═══════════════════════════════════════════════════════════════════════════════
# 5. 概念行情快照
# ═══════════════════════════════════════════════════════════════════════════════


class ConceptSnapshotCollectTask(BaseCollectTask):
    """概念实时行情 → concept_snapshots（涨跌幅 = 现价 / 昨收，昨收取自日 K 表；批次内排名）"""

    name = "concept_snapshot"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念行情快照"
    sort_order = 5
    description = "现价 / 涨跌幅 / 涨幅排名 / 成交额，adata get_market_concept_current_ths；先跑概念指数日 K"

    async def estimate_total(self, params: dict) -> int:
        return len(await _active_concepts(params))

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        concepts = await _active_concepts(params)
        fetcher = _fetcher()
        currents: dict[str, tuple[str, Any]] = {}

        async def work(c: tuple[int, str, str], delay: Optional[float]) -> UnitResult:
            _, index_code, name = c
            cur = await asyncio.to_thread(fetcher.fetch_current, index_code, delay)
            if cur is None:
                return UnitResult(success=True, skipped=True, detail=_concept_label(c))
            currents[index_code] = (name, cur)
            return UnitResult(success=True, detail=_concept_label(c), saved_count=1)

        tally = await _run_units(self._task_id, concepts, _concept_label, work, on_unit_done)

        async with AsyncSessionLocal() as session:
            repo = ConceptRepoImpl(session)
            bos, missing_prev = await _build_snapshots(repo, currents)
            written = await repo.insert_snapshots(bos)

        message = f"完成: 快照 {written} 条，失败 {tally.fail}，无行情 {tally.skip}"
        if missing_prev:
            message += f"；{missing_prev} 个概念缺昨收（先跑概念指数日 K）"
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(concepts),
            message=message,
        )


async def _build_snapshots(
    repo: ConceptRepoImpl,
    currents: dict[str, tuple[str, Any]],
) -> tuple[list[ConceptSnapshotBO], int]:
    """用昨收算涨跌幅并做批次内排名；返回 (快照列表, 缺昨收数量)"""
    today = date.today()
    prev_by_day: dict[date, dict[str, float]] = {}
    captured_at = datetime.now(timezone.utc)
    bos: list[ConceptSnapshotBO] = []
    missing_prev = 0

    for index_code, (name, cur) in currents.items():
        trade_day = cur.trade_time.date() if cur.trade_time else today
        if trade_day not in prev_by_day:
            prev_by_day[trade_day] = await repo.get_prev_closes(before=trade_day)
        prev_close = prev_by_day[trade_day].get(index_code)
        pct = None
        if prev_close:
            pct = round((cur.price / prev_close - 1) * 100, 2)
        else:
            missing_prev += 1
        bos.append(ConceptSnapshotBO(
            index_code=index_code,
            concept_name=name,
            trade_time=cur.trade_time,
            open_price=cur.open,
            high=cur.high,
            low=cur.low,
            price=cur.price,
            prev_close=prev_close,
            pct_change=pct,
            volume_wan=round(cur.volume / 1e6, 2) if cur.volume is not None else None,
            turnover_yi=round(cur.amount / 1e8, 2) if cur.amount is not None else None,
            captured_at=captured_at,
        ))

    ranked = sorted((b for b in bos if b.pct_change is not None), key=lambda b: b.pct_change, reverse=True)
    for i, b in enumerate(ranked, 1):
        b.rank_current = i
        b.rank_total = len(ranked)
    return bos, missing_prev


__all__ = [
    "ConceptListCollectTask",
    "ConceptMembershipCollectTask",
    "ConceptReasonCollectTask",
    "ConceptIndexTHCollectTask",
    "ConceptSnapshotCollectTask",
]
