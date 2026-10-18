"""采集 service 抽象（step7 重构）

替代旧 BaseCollectTask / CollectService 模式：
- 不再有"task" 概念
- 每个 service 实现 collect() 即可（统一入口，HTTP 和调度都调它）
- 限流/并发/缓存/入库全部在 service 内自决
- fetcher 只负责调 SDK

替代历史：
  - 原 BaseCollectTask（task.py）           ← 删
  - 原 CollectRunner.execute               ← 删
  - 原 CollectManageService                ← 删
  - 原 5 装饰器（Metrics/Retry/Throttle/Cache/Validate） ← 删

参考文档：docs/backend-docs/dev/step7/01采集重构/01-精简方案总览.md §1
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Optional, Protocol

# 业务级异常从 domain；port 契约错误（限流/源不可用）仍从 port
from contexts.collect.application.port.errors import RateLimited, SourceUnavailable
from contexts.collect.domain import InvalidParams, NotSupported


@dataclass(frozen=True)
class CollectResult:
    """一次采集执行的结果——调度日志和 HTTP 返回都用这个"""
    total: int = 0
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "success": self.success,
            "fail": self.fail,
            "skip": self.skip,
            "saved": self.saved,
            "message": self.message,
        }


# ═══════════════════════════════════════════════════════════════════════
# Protocol
# ═══════════════════════════════════════════════════════════════════════


class CollectService(Protocol):
    """采集 service 抽象接口

    约束：
      ① name 必须全局唯一（用于 schedule.service_name 关联，见 scheduler 模块）
      ② facet 必须是 tech / capital / fundamental / news / sentiment 之一
      ③ collect(params) 是统一入口：调度（scheduler 模块）和 HTTP 都调这个
      ④ DEFAULT_PARAMS 用于 params 为空时的兜底
      ⑤ RATE_LIMIT 用于 service 内部的限流（RedisCache.rate_limit 滑动窗口）
         格式: (source, max_count, window_seconds) 或 None
      ⑥ CONCURRENCY 用于 service 内部的并发（asyncio.Semaphore 容量）

    可选方法（用于实时查询）：
      get(...) → list[dict] | dict :  HTTP GET 入口（不走 collect）
    """
    name: ClassVar[str]
    facet: ClassVar[str]
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    DEFAULT_PARAMS: ClassVar[dict] = {}
    RATE_LIMIT: ClassVar[Optional[tuple[str, int, int]]] = None
    CONCURRENCY: ClassVar[int] = 1

    async def collect(self, params: dict) -> CollectResult:
        ...


__all__ = [
    "CollectResult", "CollectService",
    "RateLimited", "SourceUnavailable", "InvalidParams", "NotSupported",
    "list_all_a_symbols",
    "list_all_concept_codes",
]


# ═══════════════════════════════════════════════════════════════════════
# 共享 helper：拉全 A 股票代码（list_status=L）— 多个 service 的"全量模式"用
# ═══════════════════════════════════════════════════════════════════════

async def list_all_a_symbols() -> list[str]:
    """从 tushare stock_basic 拉全 A 股票代码（list_status=L，6 位补零）

    用途：service.collect() 在 symbols 为空时（前端"全量采集"）走默认拉全 A。
    返回 [] 时表示 tushare 拉失败，调用方应给出明确错误。
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from contexts.collect.infrastructure.connect.tushare_client import (
            get_tushare_client,
        )
        from contexts.collect.infrastructure.parser.tushare import rows
        c = get_tushare_client()
        df = await c.query("stock_basic", list_status="L", fields="symbol")
        return [str(r["symbol"]).zfill(6) for r in rows(df) if r.get("symbol")]
    except Exception as e:
        logger.warning("list_all_a_symbols 失败: %r", e)
        return []


async def list_all_concept_codes() -> list[str]:
    """从 concept 表（concept_list 入库）拉全部 index_code

    用途：concept_members / concept_index_daily 全量模式。
    """
    import logging
    logger = logging.getLogger(__name__)
    try:
        from sqlalchemy import select
        from shared.infrastructure.connection.db_factory import db_session_factory
        from contexts.concept.infrastructure.persistence.models.concept import ConceptDB
        async with db_session_factory() as session:
            rows_db = (await session.execute(
                select(ConceptDB.index_code)
            )).scalars().all()
            return [str(c) for c in rows_db if c]
    except Exception as e:
        logger.warning("list_all_concept_codes 失败: %r", e)
        return []

