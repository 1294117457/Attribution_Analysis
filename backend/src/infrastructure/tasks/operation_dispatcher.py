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

from infrastructure.database.connection import AsyncSessionLocal
from infrastructure.repositories.pool_operation_repository import PoolOperationRepoImpl
from infrastructure.tasks.registry import get_task_registry

logger = logging.getLogger(__name__)


class OperationDispatcher:
    """池操作任务派发器

    设计要点：
    - __init__ 不接收 session, 不持有任何 DB 资源
    - 后台任务 _run() 内部独立创建 session 操作进度/状态
    - 父请求结束后父 session 即便 close 也不影响后台任务
    """

    def __init__(self) -> None:
        self._registry = get_task_registry()

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
            async with AsyncSessionLocal() as op_session:
                op_repo = PoolOperationRepoImpl(op_session)
                try:
                    await op_repo.update_status(
                        op_id,
                        status="running",
                        started_at=datetime.now(),
                    )
                    await op_session.commit()

                    from application.kline_service import KlineAppService
                    from infrastructure.collectors import get_registry
                    from infrastructure.collectors.protocols import KlineFetcher
                    from application.dto.kline import KlineCollectRequest

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

                        # 每只股票用独立 session, 避免长事务
                        async with AsyncSessionLocal() as task_session:
                            try:
                                kline_service = KlineAppService(session=task_session)
                                fetcher = get_registry().create(KlineFetcher)
                                request = KlineCollectRequest(
                                    symbol=symbol,
                                    days=days,
                                )
                                result = await kline_service.collect(
                                    request=request,
                                    fetcher=fetcher,
                                )
                                await task_session.commit()
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
                                await task_session.rollback()
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
