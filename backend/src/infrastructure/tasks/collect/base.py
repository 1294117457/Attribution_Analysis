"""采集任务管理 — 抽象基类与模板方法

框架负责"通用"（进度 / 取消 / 收尾 / 并发安全）；
子类只负责"业务"（单元是什么 / 按什么顺序跑 / 跑完一个做什么）。

配套设计文档：
  docs/dev/07collect-class/01-collect-task-class-design.md
  docs/dev/07collect-class/02-concept-collect-integration.md

公开 API：
  - BaseCollectTask        抽象基类，子类必须实现 estimate_total / run
  - UnitResult             单个单元的执行结果（frozen）
  - TaskSummary            整个 run() 的收尾汇报（frozen）
  - Cancelled              子类 run() 内 raise 即可中断
  - execute_task           模板方法本体，唯一后台入口
  - request_cancel         写入取消标志
  - is_cancelled           检查取消标志
  - clear_cancel           清理取消标志
"""

from __future__ import annotations

import dataclasses
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, ClassVar

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.database.models.sys_collect_task import SysCollectTaskDB
from infrastructure.redis import get_redis

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
# 抽象基类
# ═══════════════════════════════════════════════════════════════════════════════


class BaseCollectTask(ABC):
    """采集任务抽象基类

    子类契约：
      ① 必须设置类变量 name（与 registry 中的 task_type 一致）
      ② 必须实现 async estimate_total(params) → int
         - 由 router 在创建任务时同步调（await）
         - 0 是合法值（表示"无单元"或"未取到预估值"）
      ③ 必须实现 async run(params, on_unit_done) → TaskSummary
         - 每完成一个单元，立即调 on_unit_done(UnitResult, label)
         - 业务异常不逃出，捕获后包装成 UnitResult(success=False, error=...)
         - 若需要取消，raise Cancelled() 让 framework 收尾

    可选钩子：
      - pre_execute(params): execute_task 开头调用一次（预热 fetcher 池 / 打开连接）
      - post_execute(params, summary): execute_task 收尾调用一次（资源清理）

    框架内部方法（子类勿调）：
      - _update_progress: 累加 success/fail/skip，写 Redis done++ / current=label
      - _finish_task:     更新 sys_collect_tasks 行（status / success / fail / ...）
    """

    name: ClassVar[str] = ""

    def __init__(self) -> None:
        # 由 execute_task() 在调用 run() 之前注入
        self._task_id: int = -1

    # ── 抽象方法（子类必须实现）────────────────────────────────────────

    @abstractmethod
    async def estimate_total(self, params: dict) -> int:
        """预估单元总数（router 同步 await）"""

    @abstractmethod
    async def run(
        self,
        params: dict,
        on_unit_done: Callable[[UnitResult, str], None],
    ) -> TaskSummary:
        """业务主循环；完成一个单元立即调用 on_unit_done(result, label)"""

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
    "TaskSummary",
    "Cancelled",
    "execute_task",
    "request_cancel",
    "is_cancelled",
    "clear_cancel",
]
