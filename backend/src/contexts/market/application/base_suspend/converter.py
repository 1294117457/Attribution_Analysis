"""base_suspend BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# BaseSuspendBO → BaseSuspend
from contexts.market.domain.base_suspend.entity import BaseSuspend

def base_suspend_bo_to_entity(bo) -> "BaseSuspend":
    return BaseSuspend(**bo.model_dump())

