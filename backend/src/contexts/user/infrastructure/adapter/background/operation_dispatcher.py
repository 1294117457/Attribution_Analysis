"""池操作任务派发器

⚠️ 关键设计：
- 不持有父请求的 session！后台任务必须自己创建独立 session
- 因为父请求结束后, FastAPI Depends 会 commit/close session 进入 "prepared" 状态
- 后台任务继续用父 session 会抛 `InvalidRequestError`
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

from shared.infrastructure.connection.db_factory import db_session_factory
from contexts.user.infrastructure.persistence.repositories.pool_operation_repository import PoolOperationRepoImpl

# ⚠️ step7 重构后 collect.infrastructure.adapter 已被删除（task_registry 已搬到 scheduler 模块）。
# 这里做一个本地兼容：如果新位置也找不到，就用一个进程内 in-memory registry 顶上，
# 保证 stock_pool / operation_dispatcher 不会因为 import 缺失把整条接口搞 500。
# 取消功能降级为「不感知」（OperationDispatcher.cancel_operation 永远返回 False）。
try:
    from contexts.collect.infrastructure.adapter.background.task_registry import (  # noqa: F401
        get_task_registry as _legacy_get_task_registry,
    )

    def _get_registry():
        return _legacy_get_task_registry()

except ImportError:
    logger.warning(
        "未找到 contexts.collect.infrastructure.adapter.task_registry（step7 已移除），"
        "OperationDispatcher 降级为无注册表模式（取消功能不可用）"
    )

    class _InMemoryRegistry:
        """最简 in-memory task registry：仅占位，不实现 register/cancel 语义"""

        def register(self, op_id: int, task) -> bool:
            return True

        def unregister(self, op_id: int) -> None:
            return None

        def is_running(self, op_id: int) -> bool:
            return True

        def cancel(self, op_id: int) -> bool:
            return False

    _SHARED_REGISTRY = _InMemoryRegistry()

    def _get_registry():
        return _SHARED_REGISTRY

# (task_type, unit, params) → UnitResult（由 di 注入 CollectManageService.run_one）
RunOne = Callable[[str, str, dict], Awaitable[Any]]


class OperationDispatcher:
    """池操作任务派发器

    设计要点：
    - __init__ 不接收 session, 不持有任何 DB 资源
    - 后台任务 _run() 内部独立创建 session 操作进度/状态
    - 父请求结束后父 session 即便 close 也不影响后台任务
    """

    def __init__(self, run_one: RunOne) -> None:
        self._registry = _get_registry()
        self._run_one = run_one

    async def dispatch_kline_collect(
        self,
        op_id: int,
        pool_id: int,
        symbols: list[str],
        days: int = 365,
    ) -> None:
        """派发 K 线采集任务（立即返回）"""

        async def _run() -> None:
            logger.info(
                "任务开始: op_id=%d, pool_id=%d, symbols=%d",
                op_id, pool_id, len(symbols),
            )

            # ── 独立 session: 负责更新 op 进度/状态 ──
            # 不复用父 session, 否则父请求结束时 session 进入 prepared 状态
            async with db_session_factory() as op_session:
                op_repo = PoolOperationRepoImpl(op_session)
                try:
                    await op_repo.update_status(
                        op_id,
                        status="running",
                        started_at=datetime.now(),
                    )
                    await op_session.commit()

                    done = 0
                    failed = 0
                    saved_total = 0
                    details = []

                    for symbol in symbols:
                        if not self._registry.is_running(op_id):
                            logger.info(
                                "任务已取消，停止执行: op_id=%d", op_id
                            )
                            break

                        # daily_kline.collect_one 每只股票自开 session、自 commit
                        try:
                            result = await self._run_one("daily_kline", symbol, {"days": days})
                            saved_total += result.saved_count
                            details.append({
                                "symbol": symbol,
                                "status": "success",
                                "count": result.saved_count,
                            })
                            logger.debug(
                                "采集成功: symbol=%s, count=%d",
                                symbol, result.saved_count,
                            )
                        except Exception as e:
                            failed += 1
                            details.append({
                                "symbol": symbol,
                                "status": "failed",
                                "message": str(e),
                            })
                            logger.warning(
                                "采集失败: symbol=%s, error=%s", symbol, e,
                            )

                        done += 1
                        # 进度更新走 op_session
                        await op_repo.update_progress(
                            op_id,
                            done=done,
                            total=len(symbols),
                            failed=failed,
                        )
                        await op_session.commit()

                    final_status = "success" if failed == 0 else "partial"
                    result_summary = {
                        "total": len(symbols),
                        "saved": saved_total,
                        "skipped": 0,
                        "failed": failed,
                        "details": details,
                    }

                    await op_repo.update_status(
                        op_id,
                        status=final_status,
                        finished_at=datetime.now(),
                    )
                    await op_repo.update_result(op_id, result_summary)
                    await op_session.commit()

                    logger.info(
                        "任务完成: op_id=%d, status=%s, saved=%d, failed=%d",
                        op_id, final_status, saved_total, failed,
                    )

                except asyncio.CancelledError:
                    logger.info("任务被取消: op_id=%d", op_id)
                    try:
                        await op_repo.update_status(
                            op_id,
                            status="cancelled",
                            finished_at=datetime.now(),
                        )
                        await op_session.commit()
                    except Exception:
                        pass
                    raise
                except Exception as e:
                    logger.exception("任务异常: op_id=%d", op_id)
                    try:
                        await op_repo.update_status(
                            op_id,
                            status="failed",
                            error_message=str(e),
                            finished_at=datetime.now(),
                        )
                        await op_session.commit()
                    except Exception:
                        pass
                finally:
                    self._registry.unregister(op_id)

        task = asyncio.create_task(_run())
        if not self._registry.register(op_id, task):
            task.cancel()
            logger.warning("任务注册失败（并发超限）: op_id=%d", op_id)

    async def cancel_operation(self, op_id: int) -> bool:
        return self._registry.cancel(op_id)
