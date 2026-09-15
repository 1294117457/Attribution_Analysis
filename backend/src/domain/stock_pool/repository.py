"""操作池 - 仓储接口"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from domain.stock_pool.entity import StockPool
from domain.stock_pool.value_objects import PoolMember


@runtime_checkable
class StockPoolRepository(Protocol):
    """操作池仓储接口"""

    # ── 池 CRUD ─────────────────────────────────────────────────────────────

    async def create(self, pool: StockPool) -> StockPool: ...

    async def find_by_id(self, pool_id: int) -> Optional[StockPool]: ...

    async def find_by_id_with_members(self, pool_id: int) -> Optional[StockPool]: ...

    async def find_all(
        self,
        include_archived: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[StockPool]: ...

    async def find_by_default(self) -> Optional[StockPool]: ...

    async def update(self, pool: StockPool) -> StockPool: ...

    async def delete(self, pool_id: int) -> bool: ...

    # ── 成员管理 ─────────────────────────────────────────────────────────────

    async def add_member(
        self, pool_id: int, symbol: str, memo: str = ""
    ) -> PoolMember: ...

    async def add_members_batch(
        self, pool_id: int, symbols: list[str]
    ) -> tuple[list[str], list[str]]: ...

    async def remove_member(self, pool_id: int, symbol: str) -> bool: ...

    async def remove_members_batch(
        self, pool_id: int, symbols: list[str]
    ) -> int: ...

    async def clear_members(self, pool_id: int) -> int: ...

    async def update_member_memo(
        self, pool_id: int, symbol: str, memo: str
    ) -> bool: ...

    async def list_members(
        self,
        pool_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PoolMember]: ...

    async def count_members(self, pool_id: int) -> int: ...

    # ── 反向查询 ─────────────────────────────────────────────────────────────

    async def find_pools_by_symbol(self, symbol: str) -> list[StockPool]: ...


@runtime_checkable
class PoolOperationRepository(Protocol):
    """池操作记录仓储接口"""

    async def create(
        self,
        pool_id: int,
        operation_type: str,
        params: dict,
    ) -> int: ...

    async def find_by_id(self, op_id: int) -> Optional[dict]: ...

    async def list_by_pool(
        self,
        pool_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> list[dict]: ...

    async def update_status(
        self,
        op_id: int,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> bool: ...

    async def update_progress(
        self,
        op_id: int,
        done: int,
        total: int,
        failed: int = 0,
    ) -> bool: ...

    async def update_result(
        self, op_id: int, result_summary: dict
    ) -> bool: ...
