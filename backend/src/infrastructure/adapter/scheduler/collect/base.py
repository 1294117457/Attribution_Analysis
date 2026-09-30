"""采集任务管理 — 抽象基类与模板方法

框架负责"通用"（进度 / 取消 / 收尾 / 并发安全）；
子类只负责"业务"（单元是什么 / 按什么顺序跑 / 跑完一个做什么）。

配套设计文档：
  docs/dev/07collect-class/01-collect-task-class-design.md
  docs/dev/07collect-class/02-concept-collect-integration.md

公开 API：
  - BaseCollectTask        抽象基类：实现 list_units + collect_one 即可，特殊流程可覆盖 run
  - UnitResult             单个单元的执行结果（frozen）
  - TaskSummary            整个 run() 的收尾汇报（frozen）
  - Cancelled              子类 run() 内 raise 即可中断
  - run_units              逐单元执行 + 首轮失败的单元末尾重试一轮
  - execute_task           模板方法本体，唯一后台入口
  - request_cancel         写入取消标志
  - is_cancelled           检查取消标志
  - clear_cancel           清理取消标志
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, ClassVar, Optional

from infrastructure.persistence.connection import AsyncSessionLocal
from infrastructure.persistence.models.sys_collect_task import SysCollectTaskDB
from infrastructure.adapter.cache.redis_client import get_redis

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 取消标志（兼容现状：模块级 set，单进程有效）
# ═══════════════════════════════════════════════════════════════════════════════

_cancel_flags: set[int] = set()


def request_cancel(task_id: int) -> None:
    """写入取消标志。被子类 run() 通过 is_cancelled() 检查。"""
    _cancel_flags.add(task_id)


def is_cancelled(task_id: int) -> bool:
    """检查 task_id 是否已收到取消信号。"""
    return task_id in _cancel_flags


def clear_cancel(task_id: int) -> None:
    """清理 task_id 的取消标志。execute_task 退出时自动调用。"""
    _cancel_flags.discard(task_id)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据类（frozen，不可变）
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class UnitResult:
    """单个单元的执行结果，由 run() 通过 on_unit_done 上报"""

    success: bool
    detail: str = ""
    error: str | None = None
    skipped: bool = False
    saved_count: int = 0
    # collect_one 给业务调用方的结构化结果（如 KlineCollectResponse.model_dump()）
    data: Any = None


@dataclass(frozen=True)
class TaskSummary:
    """整个 run() 结束后的收尾汇报"""

    success: int
    fail: int
    skip: int = 0
    message: str = ""
    total_count: int = 0
    elapsed_ms: int = 0


class Cancelled(Exception):
    """子任务取消异常。子类 run() 内 raise 即可让框架收尾。"""


# ═══════════════════════════════════════════════════════════════════════════════
# 单元执行器（默认 run() 与概念任务共用）
# ═══════════════════════════════════════════════════════════════════════════════

RETRY_DELAY = 2.0


@dataclass
class UnitTally:
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0


async def run_units(
    task_id: int,
    units: list,
    label: Callable[[Any], str],
    work: Callable[[Any, Optional[float]], Awaitable[UnitResult]],
    on_unit_done,
    *,
    concurrency: int = 1,
    retry_delay: float = RETRY_DELAY,
) -> UnitTally:
    """逐单元执行 work(unit, delay)；抛异常的单元先挂起，主循环结束后以 delay=retry_delay 再试一轮

    - 首轮 delay=None；按 concurrency 分批并发
    - 挂起的单元在重试结束后才上报，避免进度被重复计数
    """
    tally = UnitTally()
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

    async def attempt(unit) -> tuple[Optional[UnitResult], Optional[Exception]]:
        try:
            return await work(unit, None), None
        except Cancelled:
            raise
        except Exception as e:
            return None, e

    size = max(1, concurrency)
    for i in range(0, len(units), size):
        if is_cancelled(task_id):
            raise Cancelled()
        batch = units[i:i + size]
        outcomes = await asyncio.gather(*(attempt(u) for u in batch))
        for unit, (result, error) in zip(batch, outcomes):
            if error is not None:
                logger.debug("单元 %s 失败，稍后重试: %s", label(unit), error)
                pending.append(unit)
                continue
            await report(unit, result)

    if pending:
        logger.info("任务 %d：%d 个单元首轮失败，间隔 %.1fs 重试", task_id, len(pending), retry_delay)
    for unit in pending:
        if is_cancelled(task_id):
            raise Cancelled()
        try:
            result = await work(unit, retry_delay)
        except Cancelled:
            raise
        except Exception as e:
            logger.warning("单元 %s 重试仍失败: %s", label(unit), str(e)[:200])
            result = UnitResult(success=False, detail=label(unit), error=str(e)[:500])
        await report(unit, result)

    return tally


# ═══════════════════════════════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════════════════════════════


class BaseCollectTask(ABC):
    """采集任务抽象基类

    子类契约：
      ① 必须设置类变量 name（与 registry 中的 task_type 一致）
      ② 实现 list_units(params) + collect_one(unit, params)，即可使用默认
         estimate_total / run（遍历单元、并发、失败重试一轮、上报进度）
         - collect_one 采一个单元并落库（自开 session、自 commit）
         - 成功 / 跳过返回 UnitResult；失败直接抛异常（任务内会重试一轮，
           业务调用方 CollectAppService.run_one 拿到原始异常）
         - collect_one 同时是业务可复用的最小单位（单只股票 / 单个交易日）
      ③ 有特殊流程的任务可覆盖 estimate_total / run：
         - 每完成一个单元，立即调 on_unit_done(UnitResult, label)
         - 若需要取消，raise Cancelled() 让 framework 收尾

    可选钩子：
      - pre_execute(params): execute_task 开头调用一次（预热 fetcher 池 / 打开连接）
      - post_execute(params, summary): execute_task 收尾调用一次（资源清理）

    框架内部方法（子类勿调）：
      - _update_progress: 累加 success/fail/skip，写 Redis done++ / current=label
      - _finish_task:     更新 sys_collect_tasks 行（status / success / fail / ...）
    """

    # ── 任务标识（子类必须设置，与 registry 中的 task_type 一致） ──
    name: ClassVar[str] = ""

    # ── 元数据（四面分类用，前端通过 /collect/catalog 拉取） ──
    # 取值约定：
    #   facet:    tech / capital / fundamental / news / market  (5 选 1)
    #   sub_facet: 子分组自由命名，如 kline / valuation / concept_list ...
    #   label:     UI 显示名（中文）
    #   status:    ready / planned  (planned 时 run() 直接返回'待实现')
    #   description: 一句话说明（UI 副标题 / tooltip）
    #   sort_order: 同一 sub_facet 内的显示顺序（升序，相同时按 label）
    facet: ClassVar[str] = ""
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    status: ClassVar[str] = "ready"
    description: ClassVar[str] = ""
    sort_order: ClassVar[int] = 0

    # ── 执行配置 ──
    #   default_params: 接口默认参数（优先级：手动传入 > 采集方案 params > default_params）
    #   concurrency:    默认 run() 的单元并发数
    #   retry_delay:    默认 run() 首轮失败单元重试前的等待秒数
    default_params: ClassVar[dict] = {}
    concurrency: ClassVar[int] = 1
    retry_delay: ClassVar[float] = RETRY_DELAY

    def __init__(self) -> None:
        # 由 execute_task() 在调用 run() 之前注入
        self._task_id: int = -1

    # ── 单元接口（子类实现）────────────────────────────────────────────

    async def list_units(self, params: dict) -> list[str]:
        """本次要跑的单元（股票代码 / 交易日 / ...）"""
        raise NotImplementedError(f"{type(self).__name__} 未实现 list_units")

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        """采一个单元并落库；失败抛异常"""
        raise NotImplementedError(f"{type(self).__name__} 未实现 collect_one")

    @property
    def supports_collect_one(self) -> bool:
        return type(self).collect_one is not BaseCollectTask.collect_one

    # ── 默认实现（特殊流程的子类可覆盖）────────────────────────────────

    async def estimate_total(self, params: dict) -> int:
        """预估单元总数（router 同步 await）"""
        return len(await self.list_units(params))

    async def run(
        self,
        params: dict,
        on_unit_done: Callable[[UnitResult, str], Awaitable[None]],
    ) -> TaskSummary:
        """业务主循环；完成一个单元立即调用 on_unit_done(result, label)"""
        units = await self.list_units(params)

        async def work(unit: str, delay: Optional[float]) -> UnitResult:
            if delay:
                await asyncio.sleep(delay)
            return await self.collect_one(unit, params)

        tally = await run_units(
            self._task_id, units, str, work, on_unit_done,
            concurrency=self.concurrency, retry_delay=self.retry_delay,
        )
        return TaskSummary(
            success=tally.success,
            fail=tally.fail,
            skip=tally.skip,
            total_count=len(units),
            message=self.summary_message(tally),
        )

    def summary_message(self, tally: UnitTally) -> str:
        return f"完成: 成功 {tally.success}（跳过 {tally.skip}），失败 {tally.fail}；写入 {tally.saved} 条"

    # ── 可选钩子 ────────────────────────────────────────────────────────

    async def pre_execute(self, params: dict) -> None:
        """预热钩子（默认空），子类可覆盖：预热 fetcher 池 / 打开连接池"""

    async def post_execute(self, params: dict, summary: TaskSummary) -> None:
        """收尾钩子（默认空），子类可覆盖：释放资源 / 关闭连接"""

    # ── framework 内部方法（子类勿调）───────────────────────────────────

    async def _update_progress(
        self,
        redis,
        task_id: int,
        label: str,
        result: UnitResult,
    ) -> None:
        """累加 success/fail/skip，写 Redis done++ / current=label

        使用 pipeline 减少 RTT 次数。
        """
        pipe = redis.pipeline()
        pipe.hincrby(f"collect:progress:{task_id}", "done", 1)
        if result.success:
            pipe.hincrby(f"collect:progress:{task_id}", "success", 1)
        else:
            pipe.hincrby(f"collect:progress:{task_id}", "fail", 1)
        if result.skipped:
            pipe.hincrby(f"collect:progress:{task_id}", "skip", 1)
        pipe.hset(f"collect:progress:{task_id}", "current", label)
        await pipe.execute()

    async def _finish_task(
        self,
        task_id: int,
        status: str,
        success: int = 0,
        fail: int = 0,
        skip: int = 0,
        duration_ms: int | None = None,
        message: str = "",
        total_count: int | None = None,
    ) -> None:
        """更新 sys_collect_tasks 行（status / success / fail / duration / message）"""
        logger.info(
            "_finish_task %d → %s (成功%d 失败%d 跳过%d) %s",
            task_id, status, success, fail, skip, message,
        )
        async with AsyncSessionLocal() as session:
            task = await session.get(SysCollectTaskDB, task_id)
            if task:
                task.status = status
                task.success_count = success
                task.fail_count = fail
                task.skip_count = skip
                task.finished_at = datetime.now()
                task.duration_ms = duration_ms
                task.message = message
                if total_count is not None:
                    task.total_count = total_count
                await session.commit()


# ═══════════════════════════════════════════════════════════════════════════════
# 模板方法本体
# ═══════════════════════════════════════════════════════════════════════════════


async def execute_task(
    task_id: int,
    handler: BaseCollectTask,
    params: dict,
) -> None:
    """模板方法本体：所有 task_type 走这一条流水线

    流程：
      ① pre_execute           预热（子类钩子）
      ② estimate_total        估算单元数 → 写 Redis total
      ③ run                   业务主循环（每单元 on_unit_done → 取消检查 → Redis 累加）
      ④ _finish_task + Redis  收尾写库

    异常处理：
      - Cancelled         → status=cancelled（用 accumulated summary）
      - 其它 Exception    → status=failed（用 accumulated summary，错误信息入 message）
      - 正常返回          → status=success（用 handler.run() 返回的 final summary）
    """
    redis = await get_redis()
    start = time.time()

    # accumulated 由 on_unit_done 累加；final_summary 由 handler.run() 返回
    accumulated = TaskSummary(success=0, fail=0)
    final_summary: TaskSummary = accumulated
    estimated_total: int = 0

    try:
        # ① 预热
        await handler.pre_execute(params)
        # 注入 task_id（供子类在 run() 内用 is_cancelled(self._task_id)）
        handler._task_id = task_id

        # ② 估算单元数 → 写 Redis total
        estimated_total = await handler.estimate_total(params)
        await redis.hset(
            f"collect:progress:{task_id}", "total", str(estimated_total)
        )

        # ③ 业务主循环（取消检查放在 on_unit_done 闭包内）
        async def on_unit_done(result: UnitResult, label: str) -> None:
            nonlocal accumulated
            if is_cancelled(task_id):
                raise Cancelled()
            accumulated = dataclasses.replace(
                accumulated,
                success=accumulated.success + (1 if result.success else 0),
                fail=accumulated.fail + (0 if result.success else 1),
                skip=accumulated.skip + (1 if result.skipped else 0),
            )
            await handler._update_progress(redis, task_id, label, result)

        final_summary = await handler.run(params, on_unit_done)

        # ④ 收尾：用 run() 返回的 final_summary 作为权威统计
        elapsed = int((time.time() - start) * 1000)
        status = _decide_status(final_summary)
        effective_total = final_summary.total_count or estimated_total
        await handler._finish_task(
            task_id,
            status,
            success=final_summary.success,
            fail=final_summary.fail,
            skip=final_summary.skip,
            duration_ms=elapsed,
            message=final_summary.message or (
                f"完成: 成功 {final_summary.success}, 失败 {final_summary.fail}"
            ),
            total_count=effective_total,
        )
        await redis.hset(f"collect:progress:{task_id}", "status", status)
        logger.info(
            "采集任务 %d 完成: status=%s, total=%d, success=%d, fail=%d, skip=%d, %dms",
            task_id, status, effective_total,
            final_summary.success, final_summary.fail, final_summary.skip, elapsed,
        )

    except Cancelled:
        logger.info("采集任务 %d 被取消", task_id)
        await handler._finish_task(
            task_id,
            "cancelled",
            success=accumulated.success,
            fail=accumulated.fail,
            skip=accumulated.skip,
            message=f"已取消: 成功 {accumulated.success}, 失败 {accumulated.fail}",
        )
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")

    except asyncio.CancelledError:
        # 进程关闭 / 重载时事件循环取消后台协程：记录收尾后继续向上抛
        logger.warning("采集任务 %d 被事件循环取消（服务关闭或重载）", task_id)
        await handler._finish_task(
            task_id,
            "cancelled",
            success=accumulated.success,
            fail=accumulated.fail,
            skip=accumulated.skip,
            message=f"服务关闭中断: 成功 {accumulated.success}, 失败 {accumulated.fail}",
        )
        await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
        raise

    except Exception as e:
        logger.exception("采集任务 %d 异常终止", task_id)
        await handler._finish_task(
            task_id,
            "failed",
            success=accumulated.success,
            fail=accumulated.fail + 1,
            message=str(e),
        )
        await redis.hset(f"collect:progress:{task_id}", "status", "failed")

    finally:
        # post_execute 在 finally 中调用，保证清理资源（即便异常也保证）
        try:
            await handler.post_execute(params, final_summary)
        except Exception as e:
            logger.warning("post_execute 异常: %s", e)
        # 清理取消标志（避免 set 无限增长）
        clear_cancel(task_id)


def _decide_status(summary: TaskSummary) -> str:
    """根据 summary 决定最终 status（兼容既有"部分失败也算成功"的语义）"""
    if summary.success == 0 and summary.fail > 0:
        return "failed"
    return "success"


__all__ = [
    "BaseCollectTask",
    "UnitResult",
    "UnitTally",
    "TaskSummary",
    "Cancelled",
    "run_units",
    "execute_task",
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
]
