"""声明式采集任务：DeclarativeCollectTask

只声明"取哪份数据（port）/ 单元怎么列（planner）/ 是否增量（incremental）"；
取数、限频、重试、取消等待全部由 DataGateway 与横向装饰器负责。
ORM / Repo 全部隐藏在 infrastructure.persistence.collect.raw_store。
"""
from __future__ import annotations

from typing import Any, ClassVar

from contexts.collect.application.collect.planners import UnitPlanner
from contexts.collect.application.collect.task import BaseCollectTask, UnitResult, UnitTally
from contexts.data.application.port.base import DataPort


class DeclarativeCollectTask(BaseCollectTask):
    """声明式采集任务基类"""

    port: ClassVar[type[DataPort]]
    planner: ClassVar[UnitPlanner]
    incremental: ClassVar[bool] = True      # 原 existing_column is not None
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

    async def list_units(self, params: dict) -> list[str]:
        return await self.planner.units(self, params)

    async def existing_units(self, units: list[str], params: dict) -> set[str]:
        if not self.incremental:
            return set()
        return await self.ctx.raw_store.existing(self.port, units)

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        result = await self.ctx.gateway.fetch(self.port, self.build_params(unit, params))
        if not result.items:
            return UnitResult(success=True, detail=unit, skipped=True)
        saved = await self.ctx.raw_store.save(self.port, result.items)
        return UnitResult(success=True, detail=unit, saved_count=saved)

    def summary_message(self, t: UnitTally) -> str:
        return f"完成: {self.unit_word} {t.success}（{self.empty_word} {t.skip}），失败 {t.fail}；写入 {t.saved} 条"


__all__ = ["DeclarativeCollectTask"]
