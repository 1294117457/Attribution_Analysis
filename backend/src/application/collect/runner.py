"""CollectRunner — 模板方法本体（原 execute_task）

流程与异常分支与 base.execute_task 完全一致：
  ① pre_execute
  ② estimate_total → progress.set_total
  ③ run（on_unit_done：取消检查 → 累加 → progress.step）
  ④ 收尾：status = TaskOutcome(...).status → tasks.finish + progress.set_status
  Cancelled → cancelled；asyncio.CancelledError → cancelled 后继续上抛；其它异常 → failed
  finally：重置 cancel_check、post_execute、clear_cancel
"""
from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from typing import TYPE_CHECKING

from application.collect.task import (
    BaseCollectTask,
    Cancelled,
    TaskSummary,
    UnitResult,
    clear_cancel,
    is_cancelled,
)
from application.port.collect_port import (
    CollectProgressPort,
    CollectTaskStorePort,
)
from application.port.data.context import cancel_check
from domain.entitys.collect_task.vo import TaskOutcome

if TYPE_CHECKING:
    from application.collect.context import CollectContext

logger = logging.getLogger(__name__)


class CollectRunner:
    """模板方法本体：所有 task_type 走这一条流水线

    只依赖两个端口 + cancel_check contextvar + TaskOutcome。
    """

    def __init__(
        self,
        tasks: CollectTaskStorePort,
        progress: CollectProgressPort,
    ) -> None:
        self._tasks = tasks
        self._progress = progress

    async def execute(
        self,
        task_id: int,
        handler: BaseCollectTask,
        params: dict,
        ctx: "CollectContext | None" = None,
    ) -> None:
        """ctx 兼容入参：BaseCollectTask 由 registry.bind 绑定后可省略"""
        if ctx is not None:
            handler.bind(ctx)
        start = time.time()

        # accumulated 由 on_unit_done 累加；final_summary 由 handler.run() 返回
        accumulated = TaskSummary(success=0, fail=0)
        final_summary: TaskSummary = accumulated
        estimated_total: int = 0

        def _raise_if_cancelled() -> None:
            if is_cancelled(task_id):
                raise Cancelled()

        cancel_token = cancel_check.set(_raise_if_cancelled)
        try:
            # ① 预热
            await handler.pre_execute(params)
            # 注入 task_id（供子类在 run() 内用 is_cancelled(self._task_id)）
            handler._task_id = task_id

            # ② 估算单元数 → 写 Redis total
            estimated_total = await handler.estimate_total(params)
            await self._progress.set_total(task_id, estimated_total)

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
                await self._progress.step(
                    task_id, label,
                    success=result.success, skipped=result.skipped,
                )

            final_summary = await handler.run(params, on_unit_done)

            # ④ 收尾：用 run() 返回的 final_summary 作为权威统计
            elapsed = int((time.time() - start) * 1000)
            outcome = TaskOutcome(
                success=final_summary.success,
                fail=final_summary.fail,
                skip=final_summary.skip,
            )
            status = outcome.status
            effective_total = final_summary.total_count or estimated_total
            await self._tasks.finish(
                task_id,
                status=status,
                success=final_summary.success,
                fail=final_summary.fail,
                skip=final_summary.skip,
                duration_ms=elapsed,
                message=final_summary.message or (
                    f"完成: 成功 {final_summary.success}, 失败 {final_summary.fail}"
                ),
                total_count=effective_total,
            )
            await self._progress.set_status(task_id, status)
            logger.info(
                "采集任务 %d 完成: status=%s, total=%d, success=%d, fail=%d, skip=%d, %dms",
                task_id, status, effective_total,
                final_summary.success, final_summary.fail, final_summary.skip, elapsed,
            )

        except Cancelled:
            logger.info("采集任务 %d 被取消", task_id)
            await self._tasks.finish(
                task_id,
                "cancelled",
                success=accumulated.success,
                fail=accumulated.fail,
                skip=accumulated.skip,
                message=f"已取消: 成功 {accumulated.success}, 失败 {accumulated.fail}",
            )
            await self._progress.set_status(task_id, "cancelled")

        except asyncio.CancelledError:
            logger.warning("采集任务 %d 被事件循环取消（服务关闭或重载）", task_id)
            await self._tasks.finish(
                task_id,
                "cancelled",
                success=accumulated.success,
                fail=accumulated.fail,
                skip=accumulated.skip,
                message=f"服务关闭中断: 成功 {accumulated.success}, 失败 {accumulated.fail}",
            )
            await self._progress.set_status(task_id, "cancelled")
            raise

        except Exception as e:
            logger.exception("采集任务 %d 异常终止", task_id)
            await self._tasks.finish(
                task_id,
                "failed",
                success=accumulated.success,
                fail=accumulated.fail + 1,
                message=str(e),
            )
            await self._progress.set_status(task_id, "failed")

        finally:
            cancel_check.reset(cancel_token)
            try:
                await handler.post_execute(params, final_summary)
            except Exception as e:
                logger.warning("post_execute 异常: %s", e)
            clear_cancel(task_id)


__all__ = ["CollectRunner"]
