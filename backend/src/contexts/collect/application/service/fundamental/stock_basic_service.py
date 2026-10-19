"""StockBasicService：股票基本信息 service（FULL_REFRESH — 事务 DELETE+INSERT 整组覆盖）

v2（2026-10-19）改造：
  - kind = FULL_REFRESH（每次"全市场最新"覆盖式刷新）
  - collect()      编排入口：建日志 + 派发后台任务，立即返回 { log_id, status }
  - _run_collect() 后台执行：fetch + replace_all(事务 DELETE+INSERT)
  - get()          实时查询：单只 symbol 信息（DB 读，不发 tushare）

params 约定：
  - list_status  默认 "L"，可选 "D"/"P"
  - concurrency  没用（fetcher 是顺序循环 3 个交易所）；保留字段以兼容 UI

session 由 DI 工厂注入（get_db，业务库 stock_info），透传给 StockInfoRepository.replace_all()。
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, TYPE_CHECKING, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from contexts.collect.application.service.base import (
    ServiceKind,
    ServiceMeta,
)
from contexts.collect.infrastructure.cache.rate_limit import check
from contexts.collect.infrastructure.fetcher.fundamental.StockBasicTushareFetcher import (
    StockBasicTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories.stock_info_repo import (
    StockInfoRepository,
)

if TYPE_CHECKING:
    from contexts.collect.application.service.manage import CollectLogService
    from contexts.collect.infrastructure.adapter.background import CollectTaskRunner

logger = logging.getLogger(__name__)


def _stock_basic_to_dict(bo) -> dict:
    """StockInfoBO → dict（与 StockInfoDB.__table__.columns 对齐）"""
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
    )

    def __init__(
        self,
        session: AsyncSession,
        log_service: "CollectLogService",
        task_runner: "CollectTaskRunner",
        fetcher: StockBasicTushareFetcher | None = None,
        stock_repo: StockInfoRepository | None = None,
    ) -> None:
        self._session = session
        self._log_service = log_service
        self._task_runner = task_runner
        self._fetcher = fetcher or StockBasicTushareFetcher()
        self._stock_repo = stock_repo or StockInfoRepository()

    # ═══════════════════════════════════════════════════════════════
    # 入口 A：HTTP 触发（Route 层调）
    # ═══════════════════════════════════════════════════════════════

    async def collect(self, params: dict) -> dict:
        """HTTP 触发入口：编排（不执行实际采集）

        流程：
            1. log_service.create_pending() ← 创建日志（落库 + Redis）
            2. task_runner.dispatch()      ← 派发后台任务
            3. dispatch 失败 → mark_failed() ← 回滚日志
            4. return { log_id, status }

        Returns:
            { log_id, status }
        """
        # 0. 规范化入参（剥掉 mode / 空值 / 非业务字段）
        norm = self._normalize_params(params)

        # 1. 创建日志
        log_id = await self._log_service.create_pending(
            service_name=self.META.name,
            facet=self.META.facet,
            kind=self.META.kind.value,
            params=norm,
            trigger_source="manual",
        )

        # 2. 派发后台任务
        try:
            self._task_runner.dispatch(
                log_id=log_id,
                service_name=self.META.name,
                service_class=type(self),
                facet=self.META.facet,
                kind=self.META.kind.value,
                params=norm,
            )
        except Exception as e:
            logger.exception(f"派发采集任务失败: {e}")
            await self._log_service.mark_failed(
                service_name=self.META.name,
                log_id=log_id,
                error=f"派发失败: {e}",
            )
            raise

        return {"log_id": log_id, "status": "pending"}

    @staticmethod
    def _normalize_params(params: dict) -> dict:
        """剥掉 mode / 空字符串 / 空数组，只留业务字段"""
        cleaned: dict = {}
        for k, v in (params or {}).items():
            if k in ("mode",):  # 旧字段直接丢
                continue
            if v in (None, "", [], {}):
                continue
            cleaned[k] = v
        return cleaned

    # ═══════════════════════════════════════════════════════════════
    # 入口 B：后台执行（TaskRunner 调）
    # ═══════════════════════════════════════════════════════════════

    async def _run_collect(
        self,
        params: dict,
        session: AsyncSession,
        log_id: str,
        *,
        facet: str = "",
        kind: str = "full_refresh",
    ) -> AsyncGenerator[dict, None]:
        """FULL_REFRESH 后台任务执行入口

        流程：
            1. fetch 全市场（list_status 子集）
            2. 事务内 DELETE 该 list_status 子集 + INSERT 新行
            3. yield 进度（TaskRunner 消费）

        ★ session 用法：
            - 外部传入的 session 是 attribution_db（业务库，由 TaskRunner.get_db_context 建）
              仅用作 log_service 写 collect_logs
            - 写 stock_info 必须用 raw_data_db 独立 session（StockInfoDB 在采集库）
        """
        norm = self._normalize_params(params)
        list_status = str(norm.get("list_status") or "L").upper()

        # 1. 限流
        await check(self.META.rate_limit)

        # 2. fetch（可能耗时 5-30s）
        try:
            bos = await self._fetcher.fetch(list_status=list_status)
        except Exception as e:
            logger.exception("stock_basic fetch 失败: %r", e)
            yield {
                "saved": 0,
                "fail": 1,
                "total": 1,
                "skip": 0,
                "message": f"fetch 失败: {e}",
            }
            return

        total = len(bos)
        if total == 0:
            # 没有数据：建 raw 库独立 session，DELETE 旧子集
            try:
                from shared.infrastructure.di.db_session import get_raw_db_context
                async with get_raw_db_context() as raw_session:
                    await self._stock_repo.replace_all(
                        rows=[], list_status=list_status, session=raw_session,
                    )
            except Exception as e:
                logger.exception("stock_basic empty replace_all 失败: %r", e)
                yield {
                    "saved": 0, "fail": 1, "total": 0, "skip": 0,
                    "message": f"empty replace_all 失败: {e}",
                }
                return
            yield {
                "saved": 0,
                "fail": 0,
                "total": 0,
                "skip": 0,
                "message": f"无数据，list_status={list_status}",
            }
            return

        # 3. 事务内 DELETE + INSERT（用 raw 库独立 session）
        rows = [_stock_basic_to_dict(b) for b in bos]
        try:
            from shared.infrastructure.di.db_session import get_raw_db_context
            async with get_raw_db_context() as raw_session:
                saved = await self._stock_repo.replace_all(
                    rows=rows, list_status=list_status, session=raw_session,
                )
        except Exception as e:
            logger.exception("stock_basic replace_all 失败: %r", e)
            yield {
                "saved": 0,
                "fail": 1,
                "total": total,
                "skip": 0,
                "message": f"replace_all 失败: {e}",
            }
            return

        yield {
            "saved": saved,
            "fail": 0,
            "total": total,
            "skip": 0,
            "message": f"list_status={list_status}, 覆盖写入 {saved} 行",
        }

    # ═══════════════════════════════════════════════════════════════
    # 入口 C：实时查询（前端 GET 试查用）
    # ═══════════════════════════════════════════════════════════════

    async def get(self, symbol: str) -> Optional[dict]:
        return await self._stock_repo.find(str(symbol).zfill(6), self._session)


__all__ = ["StockBasicService"]
