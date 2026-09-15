"""池操作任务派发器"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from domain.stock_pool.repository import PoolOperationRepository
from infrastructure.repositories.pool_operation_repository import PoolOperationRepoImpl
from infrastructure.repositories.stock_repository import StockRepoImpl
from infrastructure.tasks.registry import get_task_registry

logger = logging.getLogger(__name__)


class OperationDispatcher:
    """池操作任务派发器"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._op_repo: PoolOperationRepository = PoolOperationRepoImpl(session)
        self._stock_repo = StockRepoImpl(session)
        self._registry = get_task_registry()

    async def dispatch_kline_collect(
        self,
        op_id: int,
        pool_id: int,
        symbols: list[str],
        days: int = 365,
        source: Optional[str] = None,
    ) -> None:
        """派发 K 线采集任务（立即返回）"""

        async def _run() -> None:
            logger.info(
                "任务开始: op_id=%d, pool_id=%d, symbols=%d",
                op_id, pool_id, len(symbols),
            )

            try:
                await self._op_repo.update_status(
                    op_id,
                    status="running",
                    started_at=datetime.now(),
                )

                from infrastructure.database.connection import AsyncSessionLocal
                from application.kline_service import KlineAppService
                from infrastructure.collectors.akshare.fetcher import AkShareFetcher
                from application.dto.kline import KlineCollectRequest

                async with AsyncSessionLocal() as task_session:
                    kline_service = KlineAppService(session=task_session)
                    fetcher = AkShareFetcher()

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

                        try:
                            request = KlineCollectRequest(
                                symbol=symbol,
                                days=days,
                            )
                            result = await kline_service.collect(
                                request=request,
                                fetcher=fetcher,
                            )
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
                        await self._op_repo.update_progress(
                            op_id,
                            done=done,
                            total=len(symbols),
                            failed=failed,
                        )

                    status = "success" if failed == 0 else "partial"
                    result_summary = {
                        "total": len(symbols),
                        "saved": saved_total,
                        "skipped": 0,
                        "failed": failed,
                        "details": details,
                    }

                    await self._op_repo.update_status(
                        op_id,
                        status=status,
                        finished_at=datetime.now(),
                    )
                    await self._op_repo.update_result(op_id, result_summary)

                    logger.info(
                        "任务完成: op_id=%d, status=%s, saved=%d, failed=%d",
                        op_id, status, saved_total, failed,
                    )

            except asyncio.CancelledError:
                logger.info("任务被取消: op_id=%d", op_id)
                await self._op_repo.update_status(
                    op_id,
                    status="cancelled",
                    finished_at=datetime.now(),
                )
                raise
            except Exception as e:
                logger.exception("任务异常: op_id=%d", op_id)
                await self._op_repo.update_status(
                    op_id,
                    status="failed",
                    error_message=str(e),
                    finished_at=datetime.now(),
                )
            finally:
                self._registry.unregister(op_id)

        task = asyncio.create_task(_run())
        if not self._registry.register(op_id, task):
            task.cancel()
            logger.warning("任务注册失败（并发超限）: op_id=%d", op_id)

    async def cancel_operation(self, op_id: int) -> bool:
        return self._registry.cancel(op_id)
