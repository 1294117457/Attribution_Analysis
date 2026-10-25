from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.fetcher.tech.DailyTushareFetcher import (
    DailyTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories.tech import (
    DailyKlineRepository,
)
from contexts.collect.interface.dto.request.daily import DailyCollectRequest

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService

logger = logging.getLogger(__name__)


class DailyService:
    """日 K 线采集服务"""

    META = ServiceMeta(
        name="daily",
        facet="tech",
        label="日 K 线",
        description="Tushare pro.daily 日 K 线",
        kind=ServiceKind.INCREMENTAL,
        concurrency=1,
    )

    DEFAULT_SYMBOL_SPAN_DAYS = 365

    def __init__(
        self,
        log_service: "CollectLogService",
        fetcher: DailyTushareFetcher | None = None,
        kline_repo: DailyKlineRepository | None = None,
    ) -> None:
        self._log_service = log_service
        self._fetcher = fetcher or DailyTushareFetcher()
        self._kline_repo = kline_repo or DailyKlineRepository()

    async def collect(self, req: DailyCollectRequest) -> None:
        """派发采集任务（入参校验已在 DTO 完成，立即返回）"""
        asyncio.create_task(self.run_collect(req))

    async def run_collect(self, req: DailyCollectRequest) -> None:
        """后台执行：建日志 → 展开单元 → 并发采集 → 终态"""
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=req.model_dump(exclude_none=True, mode="json"),
            trigger_source="manual",
        )

        from shared.infrastructure.di.db_session import get_raw_db_context
        async with get_raw_db_context() as session:
            try:
                await self._log_service.mark_running(
                    self.META.name, log_id,
                )

                if req.ts_code:
                    # 路径 A：指定单股 → 一次调用覆盖整个区间，不展开单元
                    rows, ok = await self._collect_by_symbol(req, session)
                    results = [(rows, ok, 0)]
                    total = 1
                else:
                    # 路径 B：全市场 → 按自然日展开成多个单元
                    days = self._list_days(
                        req.start_date, req.end_date,
                    )
                    if not days:
                        await self._log_service.mark_failed(
                            service_name=self.META.name,
                            log_id=log_id,
                            error=(
                                f"{req.start_date} ~ {req.end_date}"
                                " 区间为空，请检查日期范围"
                            ),
                        )
                        return

                    total = len(days)
                    results = await self._collect_all_days(days, session)

                ok_total = sum(1 for _, ok, _ in results if ok)
                fail_total = sum(f for _, _, f in results)
                saved_total = sum(r for r, _, _ in results)

                # 分母只算查到数据的单元（周末/停牌等空返回不占分母）
                progress = (
                    min(100, int(ok_total / total * 100))
                    if total > 0 else 0
                )
                await self._log_service.update_progress(
                    service_name=self.META.name,
                    log_id=log_id,
                    progress=progress,
                    saved_count=ok_total,
                    fail_count=fail_total,
                    total_count=total,
                )

                # 按成功单元数判定终态，不用入库行数
                if fail_total == 0:
                    status = "success"
                elif ok_total == 0:
                    status = "failed"
                else:
                    status = "partial_fail"

                await self._log_service.mark_finished(
                    service_name=self.META.name,
                    log_id=log_id,
                    status=status,
                    saved_count=ok_total,
                    fail_count=fail_total,
                )
                logger.info(
                    "daily 完成: log_id=%s, status=%s, rows=%d, ok=%d,"
                    " fail=%d, units=%d",
                    log_id, status, saved_total, ok_total, fail_total, total,
                )

            except Exception as e:
                logger.exception("daily 采集失败: %r", e)
                try:
                    await self._log_service.mark_failed(
                        service_name=self.META.name,
                        log_id=log_id,
                        error=str(e),
                    )
                except Exception as e2:
                    logger.error(
                        "mark_failed 失败（log_id=%s）: %r", log_id, e2,
                    )

    @staticmethod
    def _list_days(start: date, end: date) -> list[date]:
        """把 [start, end] 展开成自然日列表（不查交易日历）"""
        days: list[date] = []
        cur = start
        while cur <= end:
            days.append(cur)
            cur += timedelta(days=1)
        return days

    async def _collect_all_days(
        self, days: list[date], session: AsyncSession,
    ) -> list[tuple[int, bool, int]]:
        """按并发上限跑完所有自然日 → [(入库行数, 是否查到, 失败数)]"""
        sem = asyncio.Semaphore(self.META.concurrency)

        async def one(day: date) -> tuple[int, bool, int]:
            async with sem:
                try:
                    rows, ok = await self._collect_by_date(day, session)
                    return rows, ok, 0
                except Exception as e:
                    logger.exception("daily %s 失败: %r", day, e)
                    return 0, False, 1

        return list(await asyncio.gather(
            *(one(d) for d in days),
            return_exceptions=False,
        ))

    async def _collect_by_symbol(
        self, req: DailyCollectRequest, session: AsyncSession,
    ) -> tuple[int, bool]:
        """采集单个 ts_code 的整个区间 → (入库行数, 是否查到)"""
        end = req.end_date or date.today()
        start = (
            req.start_date
            or end - timedelta(days=self.DEFAULT_SYMBOL_SPAN_DAYS)
        )
        klines = await self._retry(
            lambda: self._fetcher.fetch_by_ts_code(
                ts_code=req.ts_code,
                start_date=start,
                end_date=end,
            ),
            session,
        )
        if not klines:
            return 0, False
        return await self._save(klines, session), True

    async def _collect_by_date(
        self, day: date, session: AsyncSession,
    ) -> tuple[int, bool]:
        """采集单个自然日 → (入库行数, 是否查到)"""
        klines = await self._retry(
            lambda: self._fetcher.fetch_by_date(day), session,
        )
        if not klines:
            return 0, False
        return await self._save(klines, session), True

    async def _retry(self, call, session: AsyncSession):
        """最多重试 3 次；前两次失败回滚事务后等待 1 秒"""
        for attempt in range(3):
            try:
                return await call()
            except Exception:
                if attempt < 2:
                    await session.rollback()
                    await asyncio.sleep(1)
                else:
                    raise

    async def _save(self, klines, session: AsyncSession) -> int:
        """入库并提交，返回写入行数"""
        saved = await self._kline_repo.save_klines(klines, session)
        await session.commit()
        return saved


__all__ = ["DailyService"]