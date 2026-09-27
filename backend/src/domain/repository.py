"""领域层 - 仓储接口基类

按 DDD.md §3.1：repository 接口定义在 domain 层，由 infrastructure 实现。
"按 (symbol, trade_date) 维度采集"是一类高频查询，
对 19 个 cap_* / base_* / fin_* / mkt_* 的仓储抽象出统一接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Generic, Optional, TypeVar


T = TypeVar("T")  # 实体类型


class BaseSymboledDatedRepository(ABC, Generic[T]):
    """按 (symbol, trade_date) 维度采集的仓储接口基类

    Generic[T]：子类声明时指定实体类，避免每个都重写类型签名。

    默认提供三个标准方法（子类不重写也能满足 interface）：
    - save(entity) -> entity
    - save_batch(entities) -> int
    - find_by_symbol(symbol, start_date, end_date) -> list[T]
    """

    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def save_batch(self, entities: list[T]) -> int: ...

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[T]: ...
