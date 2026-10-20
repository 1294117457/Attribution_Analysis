"""CollectTaskRunner — 后台采集任务派发器（v4 双协议派发）

设计要点（参考 user.contexts.infrastructure.adapter.background.operation_dispatcher）：
    - 不持有父请求的 session！后台任务必须自己创建独立 session
    - 维护进程内 task registry（log_id → asyncio.Task）
    - 派发即返回（fire-and-forget）
    - 单例模式（lifespan 内常驻）

v3 重构（2026-10-19）—— step7 TaskRunner 统一派发方案 Phase 1：
    - dispatch 极简化：dispatch(log_id, service_name, params)
      · class / facet / kind 全从 CatalogService.get_class(name).META 派生
      · 复用 collect 模块唯一的 service 索引（不维护第二份 registry）
    - _run() 调 svc._run_collect(params=params) —— service 自己从 self.META 拿 facet/kind
    - 删 _safe_new 双签名回退 —— 所有 service 强制升级到 Phase 2 协议
    - 新增 collect_log 副作用 helper（mark_running / update_progress / mark_finished / mark_failed）

step8 修正（2026-10-20）—— session 注入修正：
    - v2 旧协议 service 的 session 统一取 raw_data_db（get_raw_db_context）
      此前误用 get_db_context（attribution_db），导致所有 RawBase 表写入失败
    - 日志写入改由 CollectLogService 自管 attribution 库 session，本类不再持有业务库 session
    - mark_failed 加兜底（_safe_mark_failed），杜绝日志卡在 running

v4 重构（2026-10-20）—— 双协议派发（v2 generator + v3 自管）：
    - _run() 通过 meta.self_collect_log 检测协议：
        · True  → v3 自管：service 自己开 session + 写 mark_*/update_*
                  TaskRunner 仅做「实例化 + 调 _run_collect + 兜底 mark_failed」
        · False → v2 旧协议：保持原有 generator + TaskRunner bookkeeping 行为
    - 首批 v3 服务：StockBasicService / DailyKlineService
    - 其他 26 个 service 暂保持 v2 协议不破坏（自我兼容）
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from contexts.collect.application.service.base import ServiceMeta


class CollectTaskRunner:
    """采集后台任务派发器（单例）"""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}  # log_id → Task

    # ═══════════════════════════════════════════════════════════════
    # dispatch（极简接口）
    # ═══════════════════════════════════════════════════════════════

    def dispatch(
        self,
        log_id: str,
        service_name: str,
        params: dict,
    ) -> None:
        """派发后台采集任务（立即返回）

        Args:
            log_id: 日志 ID（已由 create_pending 创建）
            service_name: 服务名（与 META.name 一致，用于路由）
            params: 采集参数

        Raises:
            KeyError: service_name 不在 CatalogService 路由表中
        """
        # ★ 从 CatalogService 路由表查 class 和 meta
        service_class = _catalog.get_class(service_name)
        if service_class is None:
            raise KeyError(f"unknown service: {service_name!r}")
        meta: "ServiceMeta" = service_class.META

        task = asyncio.create_task(
            self._run(log_id, service_class, meta, params)
        )
        self._tasks[log_id] = task
        logger.info(
            "派发采集任务: log_id=%s, service=%s/%s, protocol=%s",
            log_id, meta.facet, service_name,
            "v3_self_managed" if getattr(meta, "self_collect_log", False) else "v2_generator",
        )

        # 完成后自动清理 registry
        task.add_done_callback(lambda t: self._tasks.pop(log_id, None))

    # ═══════════════════════════════════════════════════════════════
    # _run（后台任务执行入口）—— v4 双协议派发
    # ═══════════════════════════════════════════════════════════════

    async def _run(
        self,
        log_id: str,
        service_class: type,
        meta: "ServiceMeta",
        params: dict,
    ) -> None:
        """后台任务执行入口（v4 双协议派发）

        协议检测（meta.self_collect_log）：
            True  → v3 自管协议
                    · 不开 session（service 内部 get_raw_db_context 自己开）
                    · 直接 await svc._run_collect(log_id, params)
                    · 异常路径：_safe_mark_failed 兜底（service 内部通常已 mark_failed）
            False → v2 generator 协议
                    · 开 raw_data session → 实例化 service
                    · mark_running → 迭代 svc._run_collect(params)（yield 批次）
                    · 累计 + update_progress → mark_finished / mark_failed
        """
        from contexts.collect.application.service.manage import CollectLogService

        # ★ 日志服务自管 session、自接全局 redis 单例；无任何注入依赖
        log_service = CollectLogService()

        is_v3 = bool(getattr(meta, "self_collect_log", False))

        if is_v3:
            # ═════════════════════════════════════════════════════
            # v3 自管协议：service 全包，TaskRunner 仅做派发 + 兜底 mark_failed
            # ═════════════════════════════════════════════════════
            try:
                # v3 service 的 session 参数可选（仅 get() 用）；
                # _run_collect 自己开 raw_data session，所以这里不传
                svc = service_class(
                    session=None,
                    log_service=log_service,
                    task_runner=self,
                )
                await svc._run_collect(log_id, params)
            except Exception as e:
                logger.exception(
                    "采集任务（v3）失败: log_id=%s, service=%s, err=%r",
                    log_id, meta.name, e,
                )
                # ★ 兜底：service 内部通常已 mark_failed，
                #   但万一它在 mark_running 之前就异常，log_id 没人记
                await self._safe_mark_failed(
                    log_service, meta.name, log_id, e, 0, 0,
                )
            return

        # ═════════════════════════════════════════════════════════════
        # v2 旧协议（generator + TaskRunner bookkeeping）—— 原逻辑保留
        # ═════════════════════════════════════════════════════════════
        from shared.infrastructure.di.db_session import get_raw_db_context

        # 累计进度（异常路径也用）
        saved_total = 0
        fail_total = 0
        total = 0

        # ★ 独立 raw_data session（采集数据全部在 raw_data_db）
        async with get_raw_db_context() as session:
            try:
                # ★ 实例化 service（v3 统一三参入口：session / log_service / task_runner）
                #     fetcher / repo 由 service 自己的默认构造装填
                svc = service_class(
                    session=session,
                    log_service=log_service,
                    task_runner=self,
                )

                # ★ 1. 标记 running
                await log_service.mark_running(meta.name, log_id)

                # ★ 2. 执行采集（generator 模式；facet/kind 不再传入 —— service 自己从 self.META 拿）
                async for batch in svc._run_collect(params=params):
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
                        service_name=meta.name,
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
                    service_name=meta.name,
                    log_id=log_id,
                    status=status,
                    saved_count=saved_total,
                    fail_count=fail_total,
                )

            except Exception as e:
                logger.exception(
                    "采集任务（v2）失败: log_id=%s, service=%s, err=%r",
                    log_id, meta.name, e,
                )
                # ★ 5. 异常：写 failed（log_service 自开新 session，一定干净）
                await self._safe_mark_failed(
                    log_service, meta.name, log_id, e, saved_total, fail_total,
                )

    @staticmethod
    async def _safe_mark_failed(
        log_service,
        service_name: str,
        log_id: str,
        error: Exception,
        saved_count: int,
        fail_count: int,
    ) -> None:
        """mark_failed 兜底包装

        ★ Step 8 修正：mark_failed 失败绝不能逃逸。
        逃逸会让 get_raw_db_context.__aexit__ 在异常态再抛，
        掩盖真实错误，日志卡在 running 无人知晓。
        """
        try:
            await log_service.mark_failed(
                service_name=service_name,
                log_id=log_id,
                error=str(error),
                saved_count=saved_count,
                fail_count=fail_count,
            )
        except Exception as e2:
            # 兜底：连日志都写不进去时，只记录，不再抛出
            logger.error(
                "mark_failed 写入失败（log_id=%s, service=%s）: %r",
                log_id, service_name, e2,
            )

    # ═══════════════════════════════════════════════════════════════
    # 辅助方法（admin / debug 用）
    # ═══════════════════════════════════════════════════════════════

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


# ── CatalogService 单例（复用 service 索引，不维护第二份 registry） ──
#     dispatch() 通过 _catalog.get_class(name) 查 class + META
#     CatalogService 启动时已反射 28 个 service，路由表 100% 覆盖
from contexts.collect.application.service.manage import CatalogService

_catalog = CatalogService()


__all__ = ["CollectTaskRunner", "get_collect_task_runner"]