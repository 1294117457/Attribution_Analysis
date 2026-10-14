"""base_name_change BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# BaseNameChangeBO → BaseNameChange
from contexts.market.domain.base_name_change.entity import BaseNameChange

def base_name_change_bo_to_entity(bo) -> "BaseNameChange":
    return BaseNameChange(**bo.model_dump())

