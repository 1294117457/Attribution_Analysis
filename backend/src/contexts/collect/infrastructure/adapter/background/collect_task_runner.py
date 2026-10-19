"""CollectTaskRunner — 后台采集任务派发器

设计要点（参考 user.contexts.infrastructure.adapter.background.operation_dispatcher）：
    - 不持有父请求的 session！后台任务必须自己创建独立 session
    - 维护进程内 task registry（log_id → asyncio.Task）
    - 派发即返回（fire-and-forget）
    - 单例模式（lifespan 内常驻）
    - 注入 CollectLogService，手动调 mark_running / update_progress / mark_finished / mark_failed

Phase 2 重构（2026-10-19）：
    - 注入 CollectLogService（无 AOP，日志全手动调）
    - 实例化 service 时传入 session
    - service.collect() 由 Route 层调用，本 Runner 只调 _run_collect()
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class CollectTaskRunner:
    """采集后台任务派发器（单例）"""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}  # log_id → Task

    def dispatch(
        self,
        log_id: str,
        service_name: str,
        service_class: type,  # DailyKlineService 等，不是实例
        facet: str,
        kind: str,
        params: dict,
    ) -> None:
        """派发后台任务（立即返回）

        Args:
            log_id: 日志 ID（已由 service.collect() 创建）
            service_name: 服务名（与 META.name 一致）
            service_class: service 的 class（每次创建新实例）
            facet: 大类
            kind: 采集类型
            params: 采集参数
        """
        task = asyncio.create_task(
            self._run(log_id, service_name, service_class, facet, kind, params)
        )
        self._tasks[log_id] = task
        logger.info(
            "派发采集任务: log_id=%s, service=%s/%s",
            log_id, facet, service_name,
        )

        # 完成后自动清理 registry
        task.add_done_callback(lambda t: self._tasks.pop(log_id, None))

    async def _run(
        self,
        log_id: str,
        service_name: str,
        service_class: type,
        facet: str,
        kind: str,
        params: dict,
    ) -> None:
        """后台任务执行入口

        流程：
            1. 独立 session（get_db_context）
            2. 注入 CollectLogService
            3. 实例化 service
            4. 调 service._run_collect()
            5. 手动更新日志：mark_running → update_progress → mark_finished/mark_failed
        """
        from shared.infrastructure.di.db_session import get_db_context
        from shared.infrastructure.di.redis_session import get_redis
        from contexts.collect.application.service.manage import CollectLogService

        # ★ 独立 session（不持父请求的）
        async with get_db_context() as session:
            # ★ 注入 CollectLogService（同一 session）
            redis = await get_redis()
            log_service = CollectLogService(session=session, redis_client=redis)
            # ★ 注入 task_runner（让 service 能再次派发子任务）
            task_runner = self

            try:
                # 实例化 service（注入独立 session + log_service + task_runner）
                # 兼容未升级的 service：尝试新参数，失败回退到旧签名
                try:
                    svc = service_class(
                        session=session,
                        log_service=log_service,
                        task_runner=task_runner,
                    )
                except TypeError:
                    # 未升级的 service：只传 session
                    svc = service_class(session=session)

                # ★ 1. 标记 running
                await log_service.mark_running(service_name, log_id)

                # ★ 2. 执行采集（generator 模式）
                saved_total = 0
                fail_total = 0
                total = 0

                async for batch in svc._run_collect(
                    params=params,
                    session=session,
                    log_id=log_id,
                    facet=facet,
                    kind=kind,
                ):
                    saved = batch.get("saved", 0)
                    fail = batch.get("fail", 0)
                    total = batch.get("total", total)
                    saved_total += saved
                    fail_total += fail

                    # 计算进度
                    progress = (
                        min(100, int((saved_total + fail_total) / total * 100))
                        if total > 0 else 0
                    )

                    # ★ 3. 实时更新进度（只写 Redis）
                    await log_service.update_progress(
                        service_name=service_name,
                        log_id=log_id,
                        progress=progress,
                        saved_count=saved_total,
                        fail_count=fail_total,
                        total_count=total,
                    )

                # ★ 4. 终态
                if fail_total == 0:
                    status = "success"
                elif saved_total == 0:
                    status = "failed"
                else:
                    status = "partial_fail"

                await log_service.mark_finished(
                    service_name=service_name,
                    log_id=log_id,
                    status=status,
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

            except Exception as e:
                logger.exception(
                    "采集任务失败: log_id=%s, service=%s, err=%r",
                    log_id, service_name, e,
                )
                # ★ 5. 异常：写 failed
                await log_service.mark_failed(
                    service_name=service_name,
                    log_id=log_id,
                    error=str(e),
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

    def is_running(self, log_id: str) -> bool:
        """查询任务是否在跑"""
        task = self._tasks.get(log_id)
        return task is not None and not task.done()

    async def cancel(self, log_id: str) -> bool:
        """取消任务"""
        task = self._tasks.get(log_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True


# ── 单例 ────────────────────────────────────────────────────────────

_runner_instance: "CollectTaskRunner | None" = None


def get_collect_task_runner() -> "CollectTaskRunner":
    """获取全局 Runner 单例（lifespan 内常驻）"""
    global _runner_instance
    if _runner_instance is None:
        _runner_instance = CollectTaskRunner()
    return _runner_instance


__all__ = ["CollectTaskRunner", "get_collect_task_runner"]
