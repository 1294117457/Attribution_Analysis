"""DailyService：日 K 线 service（按 symbol 维度批量采集 + DB upsert）

v5 自管协议（2026-10-21）：
    - collect()      HTTP 入口：校验时间参数 → asyncio.create_task(run_collect(norm))，
                     立即返回 { status: "pending" }
                     不暴露 log_id，前端按 service_name 查日志列表
    - run_collect() 后台全生命周期：create_pending → mark_running → fetch → save
                     → update_progress（多次）→ mark_finished/mark_failed
                     日志在 run_collect 内部生成，不透出任何边界

v5 参数契约（本次调整）：
    - collect() 只校验「时间范围」，纯内存、不碰 DB：
      start_date / end_date 必填 + ISO 格式 + start <= end + 跨度上限
    - symbol 固定由 run_collect 从 stock_basic（fundamental_stock_basic，
      list_status='L'）读取，不接受前端指定
    - 因此 params 永远只有两个日期，不会把几千个 symbol 灌进
      collect_logs.params（JSONB，且原样出现在 /collect/logs/* 响应体里）

设计原则：
    - collect() 真·零状态：只校验 + 派发，不写任何 DB
    - 日志生命周期全在 run_collect() 内部，与业务逻辑同生同死
    - create_pending 是 run_collect 的第一件事：之后任何异常都能留下 failed 日志
    - log_id 仅内部使用，DB 表 join 用（前端不感知）

提供：
  - collect(params): HTTP 入口，校验失败抛 InvalidParams（route 层转 400）
  - run_collect(params): 后台全生命周期（见 class docstring）
  - get(...): 从 DB 读（实时查询入口，前端 RealtimePanel 用）

session 由 DI 工厂注入（get_db，写业务库 kline），但 run_collect 自己再开 raw_data session。
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.domain import InvalidParams
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.tech.DailyTushareFetcher import (
    DailyTushareFetcher,
)

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService

logger = logging.getLogger(__name__)


class DailyService:
    """日 K 线采集服务（命名说明：tech/ 下 Daily 唯一指向 K 线，剥 Kline 不歧义）"""

    # service_name 保持 "daily_kline"：URL / DB 前端查询键，不能改
    META = ServiceMeta(
        name="daily_kline",
        facet="tech",
        label="日 K 线",
        description="Tushare pro.daily 日 K 线",
        kind=ServiceKind.INCREMENTAL,
        rate_limit=("tushare", 200, 60),
        concurrency=1,  # AsyncSession 非并发安全，收敛为 1
    )

    #: 时间跨度上限（天）。3 年 ≈ 750 个交易日，全市场约 375 万行。
    #: 需要更长回填时改这一个常量即可。
    MAX_SPAN_DAYS = 1095

    def __init__(
        self,
        log_service: "CollectLogService",
        session: AsyncSession | None = None,  # 仅 get() 实时查询用；run_collect 自己开
        fetcher: DailyTushareFetcher | None = None,
    ) -> None:
        self._session = session  # 仅 get() 用
        self._log_service = log_service
        self._fetcher = fetcher or DailyTushareFetcher()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 入口：校验时间参数 → 派发，立即返回

        流程：
            1. _validate_params(params)                    ← 纯内存校验，不碰 DB
            2. asyncio.create_task(run_collect(norm))     ← 派发后台
            3. return { status: "pending" }               ← 前端按 service_name 查日志

        ★ 校验失败抛 InvalidParams（route 层转 HTTP 400）：
          「请求不合法」不是「采集失败」，不写 collect_logs，
          前端当场拿到错误信息，不必去日志列表里翻一条 failed。

        ★ symbol 不校验也不接受：固定由 run_collect 从 stock_basic 读。

        ★ 不返回 log_id：前端按 /collect/logs/daily_kline 查日志列表，
          无需知道内部 log_id。派发即完成，不等待结果。
        """
        norm = self._validate_params(params)
        asyncio.create_task(self.run_collect(norm))
        return {"status": "pending"}

    @classmethod
    def _validate_params(cls, params: dict) -> dict:
        """校验 + 清洗前端入参（纯内存，不碰 DB）

        通过 → 返回只含 start_date / end_date 的干净 dict
        失败 → 抛 InvalidParams（message 会原样返回给前端）

        校验项：
            - start_date / end_date 必填
            - 必须是 ISO 日期（YYYY-MM-DD）
            - start_date <= end_date
            - 跨度 <= MAX_SPAN_DAYS

        ★ 白名单返回：只吐 start_date / end_date，前端传的 symbols 等字段
          一律丢弃。params 会原样写进 collect_logs.params（JSONB），
          绝不能让几千个 symbol 进去撑爆日志行和列表接口响应体。
        """
        params = params or {}
        raw_start = params.get("start_date")
        raw_end = params.get("end_date")

        missing = [
            name
            for name, v in (("start_date", raw_start), ("end_date", raw_end))
            if v is None or v == ""
        ]
        if missing:
            raise InvalidParams(
                f"缺少必填参数 {'、'.join(missing)}"
                f"（时间范围必传，格式 YYYY-MM-DD）"
            )

        try:
            start = date.fromisoformat(str(raw_start))
            end = date.fromisoformat(str(raw_end))
        except ValueError as e:
            raise InvalidParams(
                f"时间格式错误（需 YYYY-MM-DD）："
                f"start_date={raw_start!r}, end_date={raw_end!r}（{e}）"
            ) from e

        if start > end:
            raise InvalidParams(
                f"start_date（{start}）不能晚于 end_date（{end}）"
            )

        span = (end - start).days
        if span > cls.MAX_SPAN_DAYS:
            raise InvalidParams(
                f"时间跨度过大：{span} 天，超过上限 {cls.MAX_SPAN_DAYS} 天"
            )

        # 返回 ISO 字符串：params 要写进 JSONB，date 对象序列化不了
        return {"start_date": start.isoformat(), "end_date": end.isoformat()}

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（全生命周期）
    # ═══════════════════════════════════════════════════════════════

    async def run_collect(self, params: dict) -> None:
        """INCREMENTAL 后台全生命周期

        包揽：
            1. create_pending（生成 log_id）—— 必须第一件，后面才有地方 mark_failed
            2. 解析时间参数（collect 已校验，这里只做兜底转换）
            3. 从 stock_basic 拉全 A 股代码（list_status='L'）
               —— 拉不到 → mark_failed 直接返回
            4. mark_running
            5. 顺序采集 + _save（每只 commit）+ 实时 update_progress
            6. mark_finished（success / partial_fail / failed）

        ★ 异常处理：
            - 单只 _collect_one 失败仅计入 fail_total（不抛出），继续其它 symbol
            - 外层 try/except 兜底 mark_failed（防日志卡在 running）
        ★ log_id 仅内部使用，不透出任何边界。
        """
        params = params or {}
        sem = asyncio.Semaphore(self.META.concurrency)

        # 1. 创建日志（拿到内部 log_id）
        #    ★ 必须最先做：之后任何异常都才有地方 mark_failed
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=params,
            trigger_source="manual",
        )

        # 2. 开 raw_data session（每只 commit 必须同一 session）
        from shared.infrastructure.di.db_session import get_raw_db_context
        async with get_raw_db_context() as session:
            try:
                # 3. 解析时间参数（collect 已校验，这里只兜底）
                start_date, end_date = self._parse_date_range(params)

                # 4. 拉 symbol（固定从 stock_basic，不接受前端指定）
                symbols = await self._list_all_symbols_via_session(session)
                if not symbols:
                    await self._log_service.mark_failed(
                        service_name=self.META.name,
                        log_id=log_id,
                        error=(
                            "stock_basic 表里没有 list_status='L' 的股票，"
                            "请先执行 stock_basic 采集再跑 daily_kline"
                        ),
                    )
                    return

                total = len(symbols)

                # 5. mark_running
                await self._log_service.mark_running(self.META.name, log_id)

                # 6. 顺序采集（concurrency=1，单只依次执行）
                async def one(symbol: str) -> dict:
                    async with sem:
                        try:
                            saved = await self._collect_one(
                                symbol, start_date, end_date, session,
                            )
                            return {"saved": saved, "fail": 0}
                        except Exception as e:
                            logger.exception(
                                "daily_kline %s 失败: %r", symbol, e,
                            )
                            return {"saved": 0, "fail": 1}

                tasks = [asyncio.create_task(one(s)) for s in symbols]

                saved_total = 0
                fail_total = 0
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    saved_total += result["saved"]
                    fail_total += result["fail"]

                    # 实时进度（每完成一只就更新一次）
                    progress = (
                        min(100, int((saved_total + fail_total) / total * 100))
                        if total > 0 else 0
                    )
                    await self._log_service.update_progress(
                        service_name=self.META.name,
                        log_id=log_id,
                        progress=progress,
                        saved_count=saved_total,
                        fail_count=fail_total,
                        total_count=total,
                    )

                # 7. 终态
                if fail_total == 0:
                    status = "success"
                elif saved_total == 0:
                    status = "failed"
                else:
                    status = "partial_fail"

                await self._log_service.mark_finished(
                    service_name=self.META.name,
                    log_id=log_id,
                    status=status,
                    saved_count=saved_total,
                    fail_count=fail_total,
                )
                logger.info(
                    "daily_kline 完成: log_id=%s, status=%s, saved=%d, fail=%d, total=%d",
                    log_id, status, saved_total, fail_total, total,
                )

            except Exception as e:
                logger.exception("daily_kline 采集失败: %r", e)
                # ★ 兜底 mark_failed（防日志卡在 running）
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

    # ═══════════════════════════════════════════════════════════════
    # 内部方法（业务逻辑，不涉及日志）
    # ═══════════════════════════════════════════════════════════════

    @staticmethod
    def _parse_date_range(params: dict) -> tuple[date, date]:

        start = params.get("start_date")
        end = params.get("end_date")
        if not start or not end:
            raise ValueError("start_date / end_date 必填")
        if isinstance(start, str):
            start = date.fromisoformat(start)
        if isinstance(end, str):
            end = date.fromisoformat(end)
        return start, end

    async def _list_all_symbols_via_session(self, session: AsyncSession) -> list[str]:

        from contexts.market.infrastructure.persistence.models.stock_basic import (
            StockBasicDB,
        )
        rows_db = (
            await session.execute(
                select(StockBasicDB.symbol)
                .where(StockBasicDB.list_status == "L")
                .order_by(StockBasicDB.symbol)
            )
        ).scalars().all()
        return [str(s).zfill(6) for s in rows_db if s]

    async def _collect_one(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        session: AsyncSession,
    ) -> int:
        """采集单只股票的日 K 线（使用外层 session，每只 commit）"""
        await check(self.META.rate_limit)
        for attempt in range(3):
            try:
                klines = await self._fetcher.fetch(
                    symbol=symbol, start_date=start_date, end_date=end_date
                )
                if not klines:
                    return 0
                return await self._save(symbol, klines, session)
            except Exception:
                if attempt < 2:
                    # 重试前必须 rollback —— 事务已 abort，不 rollback
                    # 直接重试只会拿到 InFailedSQLTransactionError
                    await session.rollback()
                    await asyncio.sleep(1)
                else:
                    raise
        return 0

    async def _save(self, symbol: str, klines, session: AsyncSession) -> int:
        """保存 K 线数据到 DB（tech_kline_daily @ raw_data_db）+ 每只 commit"""
        if not klines:
            return 0
        from contexts.market.infrastructure.persistence.models.tech_kline import (
            TechKlineDailyDB,
        )
        # ORM 模型实际列名是 "date"，不是 "trade_date"。
        rows = [
            {
                "symbol": k.symbol, "date": k.trade_date,
                "open": k.open, "high": k.high, "low": k.low, "close": k.close,
                "volume": k.volume, "amount": k.amount,
            }
            for k in klines
        ]
        stmt = pg_insert(TechKlineDailyDB).values(rows)
        # 只能更新 rows 中实际存在的列，否则 UPSERT 会把数据库里
        # name / change_pct 覆盖成 NULL。
        update_cols = {
            c.name: stmt.excluded[c.name]
            for c in [TechKlineDailyDB.open, TechKlineDailyDB.high, TechKlineDailyDB.low,
                      TechKlineDailyDB.close, TechKlineDailyDB.volume, TechKlineDailyDB.amount]
        }
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_=update_cols,
        )
        r = await session.execute(stmt)
        # 每只 commit（失败时 _collect_one 重试回滚整只）
        await session.commit()
        return r.rowcount or 0

    # ── 实时查询：从 DB 读（前端"试查"用）─────────────────────
    async def get(
        self,
        symbol: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 30,
    ) -> list[dict]:
        """实时查询日 K 线（从 DB 读，不发 tushare 请求）"""
        try:
            from contexts.market.infrastructure.persistence.models.tech_kline import (
                TechKlineDailyDB,
            )
        except ImportError:
            logger.debug("tech_kline_daily 表未建，返回空")
            return []
        if self._session is None:
            logger.warning("daily_kline.get() 缺少 session，返回空")
            return []
        stmt = select(TechKlineDailyDB).order_by(TechKlineDailyDB.date.desc())
        if symbol:
            stmt = stmt.where(TechKlineDailyDB.symbol == str(symbol).zfill(6))
        if start_date:
            stmt = stmt.where(TechKlineDailyDB.date >= start_date)
        if end_date:
            stmt = stmt.where(TechKlineDailyDB.date <= end_date)
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "symbol": r.symbol, "trade_date": r.date.isoformat() if r.date else None,
                "open": r.open, "high": r.high, "low": r.low, "close": r.close,
                "volume": r.volume, "amount": r.amount,
            }
            for r in rows
        ]


__all__ = ["DailyService"]
