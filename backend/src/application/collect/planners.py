"""单元规划器：纯函数规划 + 端口查询

规划器从 ctx 取端口，不再接收 ORM 列；已有单元的查询统一走 raw_store.existing。
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

from application.collect.task import resolve_trade_dates

if TYPE_CHECKING:
    from application.collect.context import CollectContext
    from application.collect.declarative import DeclarativeCollectTask

logger = logging.getLogger(__name__)


class UnitPlanner(Protocol):
    async def units(self, task: "DeclarativeCollectTask", params: dict) -> list[str]: ...


class TradeDatePlanner:
    """trade_date / start_date+end_date / days → 交易日（YYYYMMDD）"""

    async def units(self, task: "DeclarativeCollectTask", params: dict) -> list[str]:
        return resolve_trade_dates(params)


class SymbolPlanner:
    """symbol 指定单只；否则全部上市股票；only_missing 且 task.incremental 时跳过已有的；limit 截断"""

    async def units(self, task: "DeclarativeCollectTask", params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        symbols = await task.ctx.stocks.list_symbols("L")
        if params.get("only_missing") and task.incremental:
            existing = await task.ctx.raw_store.existing(task.port, None)
            symbols = [s for s in symbols if s not in existing]
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols


__all__ = [
    "SymbolPlanner",
    "TradeDatePlanner",
    "UnitPlanner",
]
