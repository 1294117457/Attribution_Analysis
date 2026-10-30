"""collect_logs 日志仓储：PG 永久审计（collector 写、Java 查）。

三态写入（见 采集模块现状文档（三类采集：增量-全量覆盖-实时查询）.md §5.3）：
  1. 创建：INSERT queued（create_task 首调）
  2. 运行：UPDATE running + started_at（_run 首调）
  3. 终态：UPDATE done/failed/cancelled + 计数 + finished_at（_run 收尾调一次）

中间高频进度只写 Redis，不碰 DB。DB 失败按场景分级处理（见 §7.7）：
  - insert_queued 失败 → 抛出（落审计账是受理任务的核心动作，失败就不该受理任务）
  - mark_running 失败 → 记 ERROR 后继续（任务已跑起来，不能因日志写不进去就中断采集）
  - mark_finished 失败 → 重试 3 次，再失败记 ERROR（终态写不进去 = 审计缺口）
  - mark_stale_failed 失败 → 记 ERROR

表归属：attribution 业务库 → 必须用 db_session_factory()，禁止 raw_session_factory()。
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timezone

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)

# 终态写库重试参数
_FINISH_RETRY = 3
_FINISH_RETRY_BASE_DELAY = 0.5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_day(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════
# 三态写入
# ═══════════════════════════════════════════════════════════════════════


async def insert_queued(
    *,
    task_id: str,
    facet: str,
    name: str,
    kind: str,
    mode: str,
    params: dict,
    range_start: date | None,
    range_end: date | None,
    total: int,
    trigger_source: str = "manual",
    trigger_user: str | None = None,
    parent_task_id: str | None = None,
) -> None:
    """创建日志行（status=queued）。

    🔴 失败必须抛出 —— 建任务的核心动作就是落审计账，失败就不该受理任务。
    幂等：ON CONFLICT (task_id) DO NOTHING。

    ★ kind 列承载「本次执行的采集方式」（incremental / full）；
      mode 列语义收敛为「编排来源」（manual / schedule）。
    """
    from core.db import db_session_factory
    from models.collect_logs import CollectLogDB

    async with db_session_factory() as session:
        stmt = pg_insert(CollectLogDB).values(
            task_id=task_id,
            facet=facet or "",
            name=name or "",
            kind=kind or "",
            mode=mode or "manual",
            trigger_source=trigger_source or "manual",
            trigger_user=trigger_user,
            params_json=params or {},
            range_start=range_start,
            range_end=range_end,
            status="queued",
            progress=0,
            total=total,
            done=0,
            success=0,
            fail=0,
            skip=0,
            saved_total=0,
            message="排队中",
            detail=[],
            parent_task_id=parent_task_id,
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["task_id"])
        await session.execute(stmt)
        await session.commit()


async def mark_running(task_id: str) -> None:
    """任务开始执行：queued -> running。

    🟡 失败记 ERROR 日志后继续执行 —— 任务已经跑起来了，
    不能因为日志写不进去就中断采集。
    幂等：WHERE status='queued'，重复调用不会覆盖已 running 的。
    """
    from core.db import db_session_factory
    from models.collect_logs import CollectLogDB

    try:
        async with db_session_factory() as session:
            await session.execute(
                update(CollectLogDB)
                .where(
                    CollectLogDB.task_id == task_id,
                    CollectLogDB.status == "queued",
                )
                # ⚠️ 必须显式写 updated_at：TimestampMixin 的 onupdate=func.now()
                #    只在 ORM flush 时生效，批量 update() 语句不会触发 → updated_at 会停在旧值。
                .values(status="running", started_at=_utcnow(), updated_at=_utcnow())
            )
            await session.commit()
    except Exception as e:
        logger.error("collect_logs mark_running 失败 task=%s: %r", task_id, e)


async def mark_finished(
    task_id: str,
    *,
    status: str,
    done: int,
    success: int,
    fail: int,
    saved_total: int,
    message: str,
    total_steps: int = 0,
    skip: int = 0,
    error: str | None = None,
    detail: list | None = None,
    duration_ms: int | None = None,
) -> None:
    """任务终态：done/failed/cancelled + 计数 + finished_at。

    🔴 失败重试 3 次，再失败记 ERROR（带 task_id，便于告警）。

    WHERE 条件必须是 status IN ('queued','running')——
    中断流程是「先置 cancelled，再 cancel asyncio task」，
    若不加条件，取消过程中 finally 里的 mark_finished(status='failed')
    会把 cancelled 覆盖成 failed（用户明明主动中断，却显示失败）。

    total_steps = 计划总步数，用于算 progress（0-100）。
    """
    from core.db import db_session_factory
    from models.collect_logs import CollectLogDB

    last_err: Exception | None = None
    for attempt in range(_FINISH_RETRY):
        try:
            # progress = 已完成步数占比（0-100），供列表页快速渲染进度条
            # ⚠️ total 为 0 时不能除 → 记 100（无步数可做 = 已完成）
            progress = 100 if total_steps <= 0 else int(done * 100 / total_steps)
            values: dict = {
                "status": status,
                "done": done,
                "success": success,
                "fail": fail,
                "skip": skip,
                "saved_total": saved_total,
                "progress": progress,
                "message": (message or "")[:800],
                "finished_at": _utcnow(),
                # ⚠️ 批量 update() 不会触发 TimestampMixin 的 onupdate → 必须显式写
                "updated_at": _utcnow(),
            }
            if error is not None:
                values["error"] = error[:4000]
            if detail is not None:
                values["detail"] = detail
            if duration_ms is not None:
                values["duration_ms"] = duration_ms
            if status == "cancelled":
                values["cancelled_at"] = _utcnow()

            async with db_session_factory() as session:
                await session.execute(
                    update(CollectLogDB)
                    .where(
                        CollectLogDB.task_id == task_id,
                        CollectLogDB.status.in_(["queued", "running"]),
                    )
                    .values(**values)
                )
                await session.commit()
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            logger.warning(
                "collect_logs mark_finished 失败 task=%s (第 %d 次): %r",
                task_id,
                attempt + 1,
                e,
            )
            await asyncio.sleep(_FINISH_RETRY_BASE_DELAY * (attempt + 1))
    logger.error(
        "collect_logs mark_finished 最终失败 task=%s：终态未落库！%r",
        task_id,
        last_err,
    )


async def mark_cancelled(
    task_id: str,
    *,
    done: int = 0,
    success: int = 0,
    fail: int = 0,
    saved_total: int = 0,
    message: str = "用户中断",
    total_steps: int = 0,
) -> None:
    """任务被中断：status=cancelled。

    与 mark_finished 共用 WHERE 条件（queued/running），
    保证不会把已经终态的任务改写。
    """
    await mark_finished(
        task_id,
        status="cancelled",
        done=done,
        success=success,
        fail=fail,
        saved_total=saved_total,
        message=message,
        total_steps=total_steps,
    )


async def mark_stale_failed(task_id: str, message: str) -> None:
    """重启恢复：queued/running -> failed（服务重启中断）。

    🟡 失败记 ERROR 日志。
    幂等：WHERE status IN ('queued','running')。
    """
    from core.db import db_session_factory
    from models.collect_logs import CollectLogDB

    try:
        async with db_session_factory() as session:
            await session.execute(
                update(CollectLogDB)
                .where(
                    CollectLogDB.task_id == task_id,
                    CollectLogDB.status.in_(["queued", "running"]),
                )
                .values(status="failed", message=message[:800],
                        finished_at=_utcnow(), updated_at=_utcnow())
            )
            await session.commit()
    except Exception as e:
        logger.error("collect_logs mark_stale_failed 失败 task=%s: %r", task_id, e)


async def mark_cancel_requested(task_id: str) -> None:
    """标记已收到中断请求（审计用；不改 status）。"""
    from core.db import db_session_factory
    from models.collect_logs import CollectLogDB

    try:
        async with db_session_factory() as session:
            await session.execute(
                update(CollectLogDB)
                .where(CollectLogDB.task_id == task_id)
                .values(cancel_requested=True, updated_at=_utcnow())
            )
            await session.commit()
    except Exception as e:
        logger.error("collect_logs mark_cancel_requested 失败 task=%s: %r", task_id, e)


# ═══════════════════════════════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════════════════════════════


def describe_range(params: dict, calls: list[dict]) -> tuple[date | None, date | None]:
    """从请求 params / 展开后的 calls 推导 range_start/end（审计用）。

    ★ 全量覆盖没有时间范围 → 返回 (None, None)。
    """
    start = _parse_day((params or {}).get("start_date"))
    end = _parse_day((params or {}).get("end_date"))
    trade = _parse_day((params or {}).get("trade_date"))
    if trade is not None:
        return trade, trade
    if start is not None or end is not None:
        return start or end, end or start
    # 按日展开的多步：取首末 trade_date
    days: list[date] = []
    for c in calls or []:
        d = _parse_day(c.get("trade_date"))
        if d is not None:
            days.append(d)
    if days:
        return min(days), max(days)
    return None, None


def params_json(params: dict) -> str:
    return json.dumps(params or {}, ensure_ascii=False, default=str)


__all__ = [
    "insert_queued",
    "mark_running",
    "mark_finished",
    "mark_cancelled",
    "mark_stale_failed",
    "mark_cancel_requested",
    "describe_range",
    "params_json",
]
