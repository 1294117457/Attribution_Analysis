"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol
from contexts.data.application.port.types import ListStatus, SymbolParams, TradeDateParams
from contexts.market.domain.entities.base_name_change.entity import BaseNameChange


class BaseNameChangeBO(BaseModel):
    symbol: str
    name: str
    start_date: date
    end_date: Optional[date] = None
    ann_date: Optional[date] = None
    change_reason: Optional[str] = None








    def to_entity(self) -> "BaseNameChange":
        """BO -> Entity 便利方法（委托 from_bo）"""
        return BaseNameChange.from_bo(self)


    @classmethod
    def from_entity(cls, entity) -> "BaseNameChangeBO":
        """从 Entity 构造 BO（Application 接受 Domain 的 Entity）

        利用 BO 的 model_fields 判断哪些字段是必需的；
        Entity 中为 None 的字段会跳过（让 BO 用默认值）。
        """
        kwargs = {}
        for fname, field in cls.model_fields.items():
            if fname == "symbol":
                kwargs[fname] = entity.symbol
                continue
            if not hasattr(entity, fname):
                continue
            value = getattr(entity, fname)
            # 如果字段是必需的且 Entity 值为 None，则跳过（BO 会有默认值）
            if value is None and field.is_required():
                continue
            kwargs[fname] = value
        return cls(**kwargs)