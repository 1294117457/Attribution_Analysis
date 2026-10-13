"""声明式采集任务：DeclarativeCollectTask + 单元规划器

任务只声明"取哪份数据（port）/ 单元怎么列（planner）/ 已有单元查哪一列 / 写哪个仓储"，
取数、限频、重试、取消等待全部由 DataGateway 与横向装饰器负责。

配套设计文档：docs/backend-docs/dev/step5/02底层采集优化/04-采集任务改造.md
"""
from __future__ import annotations

from typing import Any, ClassVar, Protocol

from sqlalchemy import select

from application.port.data.base import DataPort
from infrastructure.adapter.data import get_data_gateway
from infrastructure.adapter.collect.base import (
    BaseCollectTask,
    UnitResult,
    UnitTally,
    existing_dates,
    existing_symbols,
    resolve_trade_dates,
)
from infrastructure.persistence.connection import AsyncSessionLocal


# ═══════════════════════════════════════════════════════════════════════════════
# 单元规划器
# ═══════════════════════════════════════════════════════════════════════════════


class UnitPlanner(Protocol):
    async def units(self, params: dict, column: Any) -> list[str]: ...

    async def existing(self, column: Any, units: list[str]) -> set[str]: ...


class TradeDatePlanner:
    """trade_date / start_date+end_date / days → 交易日（YYYYMMDD）"""

    async def units(self, params: dict, column: Any) -> list[str]:
        return resolve_trade_dates(params)

    async def existing(self, column: Any, units: list[str]) -> set[str]:
        return await existing_dates(column, units)


class SymbolPlanner:
    """symbol 指定单只；否则全部上市股票；only_missing 且 column 非空时跳过已有的；limit 截断"""

    async def units(self, params: dict, column: Any) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        from infrastructure.persistence.models.stock_info import StockInfoDB

        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                select(StockInfoDB.symbol)
                .where(StockInfoDB.list_status == "L")
                .order_by(StockInfoDB.symbol)
            )
            symbols = [r[0] for r in rows.all()]
            if params.get("only_missing") and column is not None:
                existing = {r[0] for r in (await session.execute(select(column).distinct())).all()}
                symbols = [s for s in symbols if s not in existing]
        limit = params.get("limit")
        return symbols[: int(limit)] if limit else symbols

    async def existing(self, column: Any, units: list[str]) -> set[str]:
        return await existing_symbols(column, units)


class ConceptPlanner:
    """有效概念的 index_code；limit 截断"""

    async def units(self, params: dict, column: Any) -> list[str]:
        from infrastructure.persistence.repositories.concept_repository import ConceptRepoImpl

        async with AsyncSessionLocal() as session:
            concepts = await ConceptRepoImpl(session).list_active_concepts()
        codes = [index_code for _, index_code, _ in concepts]
        limit = params.get("limit")
        return codes[: int(limit)] if limit else codes

    async def existing(self, column: Any, units: list[str]) -> set[str]:
        return await existing_symbols(column, units)


# ═══════════════════════════════════════════════════════════════════════════════
# DeclarativeCollectTask
# ═══════════════════════════════════════════════════════════════════════════════


class DeclarativeCollectTask(BaseCollectTask):
    port: ClassVar[type[DataPort]]
    planner: ClassVar[UnitPlanner]
    existing_column: ClassVar[Any] = None     # None 表示不做增量跳过
    repo: ClassVar[type]                      # 有 save_batch(entities) 的 RepoImpl
    unit_word: ClassVar[str] = "单元"
    empty_word: ClassVar[str] = "无数据"

    def __init_subclass__(cls, **kw: Any) -> None:
        super().__init_subclass__(**kw)
        port = cls.__dict__.get("port")
        if port is not None:
            for attr in ("facet", "sub_facet", "label", "description"):
                if attr not in cls.__dict__:
                    setattr(cls, attr, getattr(port, attr))

    def build_params(self, unit: str, params: dict) -> dict:
        """单元 + 任务参数 → Port 参数；默认 {port.unit: unit}"""
        return {self.port.unit: unit}

    @property
    def _column(self) -> Any:
        """ORM 列是描述符，经实例访问会被当成映射对象取值，必须从类上读"""
        return type(self).existing_column

    async def list_units(self, params: dict) -> list[str]:
        return await self.planner.units(params, self._column)

    async def existing_units(self, units: list[str], params: dict) -> set[str]:
        column = self._column
        if column is None:
            return set()
        return await self.planner.existing(column, units)

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        result = await get_data_gateway().fetch(self.port, self.build_params(unit, params))
        if not result.items:
            return UnitResult(success=True, detail=unit, skipped=True)
        async with AsyncSessionLocal() as session:
            saved = await self.repo(session).save_batch([b.to_entity() for b in result.items])
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, t: UnitTally) -> str:
        return f"完成: {self.unit_word} {t.success}（{self.empty_word} {t.skip}），失败 {t.fail}；写入 {t.saved} 条"


__all__ = [
    "ConceptPlanner",
    "DeclarativeCollectTask",
    "SymbolPlanner",
    "TradeDatePlanner",
    "UnitPlanner",
]
