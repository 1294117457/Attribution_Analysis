"""采集用例的 IO 端口（6 个）+ 端口数据契约

每个方法是一个独立事务，实现内部自开 session、自 commit（README §4.2）。
参数和返回值只用 Port / BO / 基本类型 / 本文件内的 dataclass，不出现 ORM。

配套设计文档：docs/backend-docs/dev/step5/03collect优化/02-端口与基础设施实现.md
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel

from contexts.data.application.port.base import DataPort
from contexts.data.application.port.concept import (
    ConceptIndexTHBO,
    ConceptListBO,
    ConceptOfStockBO,
    ConceptSnapshotBO,
)


# ═══════════════════════════════════════════════════════════════════════════════
# RawDataStorePort
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class RawDataStorePort(Protocol):
    """原始数据入库：14 张表统一入口，以 Port 名为键（不是表名）"""

    def supports(self, port: type[DataPort]) -> bool:
        """该 Port 是否配置了入库映射（启动期校验用）"""

    async def save(self, port: type[DataPort], items: list[BaseModel]) -> int:
        """写入一批 BO，返回写入条数（语义与现在各 RepoImpl.save_batch 一致）"""

    async def existing(self, port: type[DataPort], units: list[str] | None) -> set[str]:
        """库中已有数据的单元。

        units 为交易日（YYYYMMDD）或股票代码，取决于该表的增量列；
        units=None 表示返回全部已有单元（SymbolPlanner 的 only_missing 用）。
        """


# ═══════════════════════════════════════════════════════════════════════════════
# StockUniversePort
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class StockUniversePort(Protocol):
    """股票范围与日 K 覆盖（采集专用只读查询，自开 session）"""

    async def list_symbols(
        self, list_status: str = "L", exchanges: list[str] | None = None,
    ) -> list[str]:
        """按代码升序"""

    async def list_dates(self, symbols: list[str]) -> dict[str, date | None]:
        """上市日期（日 K 窗口裁剪：起点不早于上市日）"""

    async def kline_coverage(self, symbols: list[str]) -> dict[str, tuple[date, date]]:
        """每只股票库中日 K 的 (最早日期, 最新日期)；无数据的不出现在结果里"""


# ═══════════════════════════════════════════════════════════════════════════════
# ConceptStorePort
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class ConceptStorePort(Protocol):
    """概念采集读写（写侧只在采集任务用）"""

    # 清单
    async def list_active_concepts(self) -> list[tuple[int, str, str]]: ...   # [(id, index_code, name)]
    async def count_active(self) -> int: ...
    async def upsert_concepts(self, bos: list[ConceptListBO]) -> dict[str, int]: ...  # {index_code: id}
    async def deactivate_missing(self, keep_index_codes: list[str]) -> int: ...
    # 成分股
    async def count_members(self, concept_id: int) -> int: ...
    async def replace_members(
        self, concept_id: int, symbols: list[str],
    ) -> tuple[int, int]: ...   # (新增, 移除)
    # 指数日 K
    async def get_max_trade_dates(self) -> dict[str, date]: ...
    async def upsert_index_th(self, bos: list[ConceptIndexTHBO]) -> int: ...
    # 入选理由
    async def member_symbols(self, only_missing_reason: bool) -> list[str]: ...
    async def update_reasons(self, symbol: str, items: list[ConceptOfStockBO]) -> int:
        """返回更新条数"""
    # 快照
    async def active_index_codes(self) -> list[str]: ...
    async def add_snapshot(
        self, index_code: str, snap: ConceptSnapshotBO, trade_time: datetime,
    ) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
# CollectTaskStorePort
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CollectTaskRecord:
    """任务行数据契约（应用层类型，infra 用 ORM 转换）"""

    id: int
    task_type: str
    trigger_type: str
    status: str
    params: dict
    total_count: int
    success_count: int
    fail_count: int
    skip_count: int


@runtime_checkable
class CollectTaskStorePort(Protocol):
    """采集任务行（sys_collect_tasks）的读写"""

    async def has_running(self, task_type: str) -> bool: ...
    async def mark_running_as_failed(
        self, task_type: str, reason: str,
    ) -> list[int]:
        """把 task_type 下所有 running 标 failed（启动崩溃/进程被杀 等孤儿）

        返回被修改的任务 id 列表；调用方通常是新建任务前的"业务级懒清理"。
        """
    async def create(
        self, *, task_type: str, trigger: str, params: dict, total: int,
        plan_run_id: int | None, plan_first: bool,
    ) -> int: ...
    async def get(self, task_id: int) -> CollectTaskRecord | None: ...
    async def finish(
        self, task_id: int, *, status: str, success: int, fail: int, skip: int,
        message: str, duration_ms: int | None = None, total_count: int | None = None,
    ) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════════
# CollectProgressPort
# ═══════════════════════════════════════════════════════════════════════════════


@runtime_checkable
class CollectProgressPort(Protocol):
    """采集进度（Redis `collect:progress:{task_id}`）"""

    async def init(self, task_id: int, total: int) -> None:
        """写 total/done/success/fail/skip/status=running/current，TTL 86400"""
    async def set_total(self, task_id: int, total: int) -> None: ...

    async def step(
        self, task_id: int, label: str, *, success: bool, skipped: bool,
    ) -> None:
        """done+1、success/fail(+skip)+1、current=label"""
    async def set_status(self, task_id: int, status: str) -> None: ...


__all__ = [
    "CollectProgressPort",
    "CollectTaskRecord",
    "CollectTaskStorePort",
    "ConceptStorePort",
    "RawDataStorePort",
    "StockUniversePort",
]
