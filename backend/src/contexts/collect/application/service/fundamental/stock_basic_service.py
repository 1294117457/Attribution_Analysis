"""StockBasicService：股票基本信息 service（FULL_REFRESH — 事务 DELETE+INSERT 整组覆盖）

v4 自管协议（2026-10-20）：
    - collect()      HTTP 入口：asyncio.create_task(run_collect(params))，立即返回 { status: "pending" }
                     不再暴露 log_id 前端，前端按 service_name 查日志列表
    - run_collect() 后台全生命周期：create_pending → mark_running → fetch → save
                     → update_progress → mark_finished/mark_failed
                     日志在 run_collect 内部生成，不透出任何边界

设计原则：
    - collect() 真·零状态：只派发，不写任何 DB
    - 日志生命周期全在 run_collect() 内部，与业务逻辑同生同死
    - log_id 仅内部使用，DB 表 join 用（前端不感知）

params 约定：
  - list_status  默认 "L"，可选 "D"/"P"
  - concurrency  没用（fetcher 是顺序循环 3 个交易所）；保留字段以兼容 UI

session 由 DI 工厂注入（get_raw_db，采集库 fundamental_stock_basic），透传给 StockInfoRepository.replace_all()。
但 run_collect 自己再开 raw_data session（覆盖写入走采集库）。
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.fetcher.fundamental.StockBasicTushareFetcher import (
    StockBasicTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
    StockInfoRepository,
)

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService

logger = logging.getLogger(__name__)


def _stock_basic_to_dict(bo) -> dict:
    """StockInfoBO → dict（与 StockBasicDB.__table__.columns 对齐）"""
    return {
        "symbol": bo.symbol,
        "ts_code": bo.ts_code,
        "name": bo.name,
        "fullname": getattr(bo, "fullname", None),
        "enname": getattr(bo, "enname", None),
        "cnspell": getattr(bo, "cnspell", None),
        "area": bo.area,
        "industry": bo.industry,
        "market": bo.market,
        "exchange": bo.exchange,
        "list_date": bo.list_date,
        "delist_date": bo.delist_date,
        "list_status": bo.list_status or "L",
        "is_hs": bo.is_hs or "N",
        "act_name": bo.act_name,
        "act_ent_type": bo.act_ent_type,
        "curr_type": getattr(bo, "curr_type", None),
    }


class StockBasicService:
    """股票基本信息 service（FULL_REFRESH：同 list_status 子集整组覆盖）"""

    META = ServiceMeta(
        name="stock_basic",
        facet="fundamental",
        label="股票基本信息",
        description="全 A 股基本信息（Tushare stock_basic；每次整组覆盖同 list_status 子集）",
        kind=ServiceKind.FULL_REFRESH,
        concurrency=1,
    )

    def __init__(
        self,
        log_service: "CollectLogService",
        session: AsyncSession | None = None,  # 仅 get() 实时查询用；run_collect 自己开
        fetcher: StockBasicTushareFetcher | None = None,
        stock_repo: StockInfoRepository | None = None,
    ) -> None:
        self._session = session  # 仅 get() 用
        self._log_service = log_service
        self._fetcher = fetcher or StockBasicTushareFetcher()
        self._stock_repo = stock_repo or StockInfoRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 入口：只管派发，立即返回

        流程：
            1. asyncio.create_task(run_collect(params))  ← 派发后台
            2. return { status: "pending" }             ← 前端按 service_name 查日志

        ★ 不返回 log_id：前端按 /collect/logs/stock_basic 查日志列表，
          无需知道内部 log_id。派发即完成，不等待结果。
        """
        norm = self._normalize_params(params)
        asyncio.create_task(self.run_collect(norm))
        return {"status": "pending"}

    @staticmethod
    def _normalize_params(params: dict) -> dict:
        """剥掉 mode / 空字符串 / 空数组，只留业务字段"""
        cleaned: dict = {}
        for k, v in (params or {}).items():
            if k in ("mode",):
                continue
            if v in (None, "", [], {}):
                continue
            cleaned[k] = v
        return cleaned

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（全生命周期）
    # ═══════════════════════════════════════════════════════════════

    async def run_collect(self, params: dict) -> None:
        """FULL_REFRESH 后台全生命周期

        包揽：
            1. create_pending（生成 log_id）
            2. mark_running
            3. 限流 + fetch
            4. 事务内 DELETE + INSERT（replace_all）
            5. update_progress（终态 → 100%）
            6. mark_finished / mark_failed

        ★ log_id 仅内部使用，不透出任何边界。
        ★ 异常处理：mark_failed 用独立 session（与 raw_data session 隔离）。
        """
        norm = self._normalize_params(params)
        list_status = str(norm.get("list_status") or "L").upper()

        # 1. 创建日志（拿到内部 log_id）
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=norm,
            trigger_source="manual",
        )

        # 2. 开 raw_data session（采集数据 100% 在 raw_data_db）
        from shared.infrastructure.di.db_session import get_raw_db_context
        async with get_raw_db_context() as session:
            try:
                await self._log_service.mark_running(self.META.name, log_id)

                # 3. 限流 + fetch（可能耗时 5-30s）
                bos = await self._fetcher.fetch(list_status=list_status)
                total = len(bos)

                # 4. 事务内 DELETE + INSERT
                if total == 0:
                    saved_count = await self._stock_repo.replace_all(
                        rows=[], list_status=list_status, session=session,
                    )
                    message = f"无数据，list_status={list_status}"
                else:
                    rows = [_stock_basic_to_dict(b) for b in bos]
                    saved_count = await self._stock_repo.replace_all(
                        rows=rows, list_status=list_status, session=session,
                    )
                    message = f"list_status={list_status}, 覆盖写入 {saved_count} 行"

                # 5. 进度（终态 → 100%）
                await self._log_service.update_progress(
                    service_name=self.META.name,
                    log_id=log_id,
                    progress=100,
                    saved_count=saved_count,
                    fail_count=0,
                    total_count=total,
                )

                # 6. 终态：success（FULL_REFRESH 是原子操作，要么全成功要么全失败）
                await self._log_service.mark_finished(
                    service_name=self.META.name,
                    log_id=log_id,
                    status="success",
                    saved_count=saved_count,
                    fail_count=0,
                )
                logger.info(
                    "stock_basic 完成: log_id=%s, %s",
                    log_id, message,
                )

            except Exception as e:
                logger.exception("stock_basic 采集失败: %r", e)
                # ★ 标记失败用独立 session（与 raw_data session 隔离）
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
    # 入口 C：实时查询（前端 GET 试查用）
    # ═══════════════════════════════════════════════════════════════

    async def get(self, symbol: str) -> Optional[dict]:
        return await self._stock_repo.find(str(symbol).zfill(6), self._session)


__all__ = ["StockBasicService"]
