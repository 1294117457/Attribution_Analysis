"""采集 service 抽象

v4 自管协议（2026-10-20）：
    - 移除 CollectTaskSpec 和 self_collect_log 机制
    - collect() 简化为：asyncio.create_task(run_collect(params)) + return {"status": "pending"}
    - run_collect(params) 包揽全生命周期：create_pending → mark_running → fetch → save
      → update_progress → mark_finished/mark_failed
    - log_id 不透出任何边界，前端按 service_name 查日志列表

历史：
    - v1: BaseCollectTask 模式（含 AOP 装饰器）
    - v2: ServiceKind / ServiceMeta 统一元数据
    - v3: TaskRunner 统一派发 + CollectTaskSpec
    - v4: 移除 TaskRunner，日志全生命周期收拢到 run_collect()
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, ClassVar, Protocol

from contexts.collect.application.port.errors import RateLimited, SourceUnavailable
from contexts.collect.domain import InvalidParams, NotSupported


# ═══════════════════════════════════════════════════════════════════════
# ServiceMeta：统一元数据
# ═══════════════════════════════════════════════════════════════════════


class ServiceKind(Enum):
    """采集服务类型，决定 UI 展示和触发方式"""
    INCREMENTAL = "incremental"     # 增量入库，需要时间范围（如日K）
    FULL_REFRESH = "full_refresh"  # 全量覆盖，无时间范围（如股票基本信息）
    REALTIME = "realtime"          # 实时查询，不入库（如分K）


@dataclass
class ServiceMeta:
    """采集 service 的统一元数据

    用于替代散落的 class 属性（name/facet/label），
    统一在 META 类属性中声明。

    字段说明：
      name        全局唯一标识（对应 fetcher 的索引 key）
      facet       大类：tech / capital / fundamental / news / sentiment
      label       前端展示名称
      description 描述（可选）
      kind        采集行为类型（决定 UI 展示）
      rate_limit  限速配置：(source, count, window)，None 表示不限制
      concurrency 并发上限（asyncio.Semaphore 容量）
    """
    # ── 标识 ──────────────────────────────────────
    name: str                                       # 全局唯一标识
    facet: str                                      # 大类（tech / capital / fundamental / news / sentiment）
    label: str = ""                                 # 前端展示名
    description: str = ""                            # 描述（可选）

    # ── 采集行为 ──────────────────────────────────
    kind: ServiceKind = ServiceKind.INCREMENTAL

    # ── 运行时配置 ────────────────────────────────
    rate_limit: tuple[str, int, int] | None = None  # (source, count, window)
    concurrency: int = 1                             # 并发上限

    # ── 自动派生 ──────────────────────────────────
    @property
    def path(self) -> str:
        return f"/collect/{self.facet}/{self.name}"

    @property
    def query_path(self) -> str | None:
        return f"/collect/query/{self.name}"

    @property
    def supports_query(self) -> bool:
        return self.kind == ServiceKind.REALTIME


@dataclass(frozen=True)
class CollectResult:
    """一次采集执行的结果——同步模式下用（仅 REALTIME 兼容保留）"""
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
    """采集 service 抽象接口（v4 自管协议）

    所有 service 必须：
      1. 声明 META: ClassVar[ServiceMeta]
      2. 实现 collect(params) → dict（HTTP 编排入口：派发后台，立即返回）
      3. 实现 run_collect(params) → None（后台全生命周期，自己管日志）

    collect() 约定：
        - 只管派发：asyncio.create_task(self.run_collect(params))
        - 立即返回：{"status": "pending"}
        - 不写任何 DB，不返回 log_id
        - 前端按 service_name 查日志列表，不依赖 log_id

    run_collect(params) 约定：
        - 第一步：log_id = await self._log_service.create_pending(...)
        - 全流程：create_pending → mark_running → 限流 → fetch → save
          → update_progress（多次）→ mark_finished/mark_failed
        - log_id 仅内部使用，不透出任何边界
        - 异常：捕获后 mark_failed（独立 session），不 re-raise

    可选：
      - get(**kwargs) → list[dict] | dict   （REALTIME service 的实时查询入口）
    """
    META: ClassVar[ServiceMeta]

    async def collect(self, params: dict) -> dict:
        """HTTP 编排入口：派发后台任务，立即返回

        Returns:
            {"status": "pending"}  ← 派发即完成，前端按 service_name 查日志
        """

    def run_collect(self, params: dict) -> Any:
        """后台全生命周期（内部包含 create_pending / mark_running / mark_finished 等）"""

    async def get(self, **kwargs: Any) -> Any:
        """实时查询入口（仅 REALTIME service 实现）"""
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

    用途：service.run_collect() 在 symbols 为空时（前端"全量采集"）走默认拉全 A。
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
        from shared.infrastructure.connection.db_factory import raw_session_factory
        from contexts.concept.infrastructure.persistence.models.concept import (
            ConceptsDB,
        )
        async with raw_session_factory() as session:
            rows_db = (await session.execute(
                select(ConceptsDB.index_code)
            )).scalars().all()
            return [str(c) for c in rows_db if c]
    except Exception as e:
        logger.error("list_all_concept_codes 失败（抛出让上层感知）: %r", e)
        raise
