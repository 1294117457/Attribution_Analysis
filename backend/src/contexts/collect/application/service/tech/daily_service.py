"""DailyService — 日 K 线采集 service

v12 重构（2026-10-27）—— 只保留时间范围采集：
    - 删除 ts_code 单股分支（唯一调用方 StockInfoService / stock_pool 已下线）
    - 删除 _list_days（自然日展开内联进 run_collect）
    - 删除 _collect_range / _collect_all_days（并发恒为 1，改为线性 for 循环）
    - 删除 _save（commit/rollback 交给 get_raw_db_context）
    - 单元结果改用 DailyFetcherResult model（替代裸元组，修掉解包崩溃）
    - 每个采集单元一个独立事务（get_raw_db_context）
    - 进度口径统一为「已处理单元数 / 总单元数」
    - 入库逻辑在 repo（_to_row 映射 + upsert），service 只调 repo 接口

日志生命周期：
    1. log_util.create()          → 建日志（DB init + Redis init）
    2. log_util.update_status()   → 改状态（只写 Redis）
    3. log_util.update_progress() → 采集过程中的实时进度（只写 Redis）
    4. log_util.update()          → 终态（写 DB + 清 Redis）

★ 采集数据的 session 由 _collect_by_date 内部自开（get_raw_db_context），
  采集数据在 raw_data_db、日志在 attribution_db，两者物理隔离互不干扰。
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, timedelta

from contexts.collect.application.bo.tech import DailyFetcherResult
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
from shared.infrastructure.di.db_session import get_raw_db_context
from shared.infrastructure.log_util import log_util

logger = logging.getLogger(__name__)


def _elapsed_ms(started_at: float) -> int:
    """从 monotonic 起点算已耗时（毫秒）

    ★ 用 time.monotonic() 而非 datetime.now()：
      后者受系统时钟调整影响（NTP 校时可能让耗时为负）。
    """
    return int((time.monotonic() - started_at) * 1000)


class DailyService:
    """日 K 线采集服务（按时间范围采集全市场）"""

    META = ServiceMeta(
        name="daily",
        facet="tech",
        label="日 K 线",
        description="Tushare pro.daily 日 K 线（按时间范围采集）",
        kind=ServiceKind.INCREMENTAL,
        concurrency=1,
    )

    def __init__(
        self,
        fetcher: DailyTushareFetcher | None = None,
        kline_repo: DailyKlineRepository | None = None,
    ) -> None:
        self._fetcher = fetcher or DailyTushareFetcher()
        self._kline_repo = kline_repo or DailyKlineRepository()
        # ★ 强引用后台任务：asyncio 只持弱引用，
        #   没有这个 set 的话 task 可能在执行中被 GC 掉
        self._tasks: set[asyncio.Task] = set()

    # ═══════════════════════════════════════════════════════════════
    # collect —— HTTP 入口（派发后台任务，立即返回）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, req: DailyCollectRequest) -> None:
        """派发采集任务（入参校验已在 DTO 完成，立即返回）

        ★ 与 FastAPI 的 HTTP 生命周期解耦：
          本方法只做两件事 —— 建日志 + 派发 task，不持有任何请求级资源。
        """
        task = asyncio.create_task(self.run_collect(req))
        # ★ 保活：事件循环只对 task 持弱引用，不存起来可能被 GC
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # ═══════════════════════════════════════════════════════════════
    # run_collect —— 后台执行（日志的主要使用地）
    # ═══════════════════════════════════════════════════════════════

    async def run_collect(self, req: DailyCollectRequest) -> None:
        """后台执行：建日志 → 逐日采集 → 实时进度 → 终态

        ★ 异常路径必须保证日志落到终态，否则会留下卡在 init 的孤儿日志。
        """
        log_id = await log_util.create(
            service_name=self.META.name,
            category=self.META.facet,
            action=self.META.kind.value,
            meta=req.model_dump(exclude_none=True, mode="json"),
            trigger_source="manual",
        )
        started_at = time.monotonic()

        try:
            # ── 1. 标记 running（只写 Redis）──
            await log_util.update_status(
                log_id,
                service_name=self.META.name,
                status="running",
            )

            # ── 2. 展开时间范围为自然日列表 ──
            days: list[date] = []
            cur = req.start_date
            while cur <= req.end_date:
                days.append(cur)
                cur += timedelta(days=1)

            if not days:
                await log_util.update(
                    log_id,
                    service_name=self.META.name,
                    status="failed",
                    progress=0,
                    error=(
                        f"{req.start_date} ~ {req.end_date}"
                        " 区间为空，请检查日期范围"
                    ),
                    duration_ms=_elapsed_ms(started_at),
                )
                return

            total = len(days)
            ok_total = 0
            fail_total = 0
            saved_total = 0
            processed = 0

            # ── 3. 逐日采集（线性循环，每个自然日一个独立事务）──
            for i, day in enumerate(days, start=1):
                result = await self._collect_by_date(day)

                if result.ok:
                    ok_total += 1
                if result.fail:
                    fail_total += 1
                saved_total += result.rows
                processed = i

                # 实时进度（只写 Redis；失败不中断采集）
                await log_util.update_progress(
                    log_id,
                    service_name=self.META.name,
                    progress=int(i / total * 100),
                    saved_count=ok_total,
                    fail_count=fail_total,
                    total_count=total,
                )

            # ── 4. 终态（写 DB + 清 Redis）──
            # 按成功单元数判定终态，不用入库行数
            if fail_total == 0:
                status = "success"
            elif ok_total == 0:
                status = "failed"
            else:
                status = "partial_fail"

            await log_util.update(
                log_id,
                service_name=self.META.name,
                status=status,
                # 进度口径统一为「已处理单元数 / 总单元数」
                progress=int(processed / total * 100),
                saved_count=ok_total,
                fail_count=fail_total,
                duration_ms=_elapsed_ms(started_at),
            )
            logger.info(
                "daily 完成: log_id=%s, status=%s, rows=%d, ok=%d,"
                " fail=%d, units=%d",
                log_id, status, saved_total, ok_total, fail_total, total,
            )

        except Exception as e:
            logger.exception("daily 采集失败: %r", e)
            # 兜底：日志必须落终态，否则留下卡在 init 的孤儿日志
            try:
                await log_util.update(
                    log_id,
                    service_name=self.META.name,
                    status="failed",
                    progress=0,
                    error=str(e)[:500],
                    duration_ms=_elapsed_ms(started_at),
                )
            except Exception as e2:
                logger.error(
                    "log_util.update 失败（log_id=%s）: %r", log_id, e2,
                )

    # ═══════════════════════════════════════════════════════════════
    # 采集内部实现
    # ═══════════════════════════════════════════════════════════════

    async def _collect_by_date(self, day: date) -> DailyFetcherResult:
        """采集单个自然日 → DailyFetcherResult

        链路：fetcher 取数 → KlineBO → repo.save(BO, session)

        ★ 事务边界由本方法决定（每个自然日一个事务），
          但 commit/rollback 的执行交给 get_raw_db_context() ——
          service 里不出现任何 commit()/rollback() 调用。
        """
        try:
            klines = await self._retry(
                lambda: self._fetcher.fetch_by_date(day),
            )
        except Exception as e:
            logger.exception("daily %s 失败: %r", day, e)
            return DailyFetcherResult(
                trade_date=day, rows=0, ok=False, fail=1, error=str(e),
            )

        if not klines:
            # 查不到数据 ≠ 失败（周末/节假日/停牌）
            return DailyFetcherResult(
                trade_date=day, rows=0, ok=False, fail=0,
            )

        # ── 入库：事务边界在本方法，commit/rollback 由 context manager 负责 ──
        async with get_raw_db_context() as session:
            saved = await self._kline_repo.save_klines(klines, session)

        return DailyFetcherResult(
            trade_date=day, rows=saved, ok=True, fail=0,
        )

    async def _retry(self, call):
        """最多重试 3 次；前两次失败等待 1 秒

        ★ 只管重试，不管事务 —— 事务由 get_raw_db_context() 统一处理。
          这里不碰 session（fetch 阶段还没进事务）。
        """
        for attempt in range(3):
            try:
                return await call()
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    raise


__all__ = ["DailyService"]
