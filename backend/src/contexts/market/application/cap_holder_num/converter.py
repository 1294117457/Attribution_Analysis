"""cap_holder_num BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapHolderNumBO → CapHolderNum
from contexts.market.domain.cap_holder_num.entity import CapHolderNum

def cap_holder_num_bo_to_entity(bo) -> "CapHolderNum":
    return CapHolderNum(**bo.model_dump())

