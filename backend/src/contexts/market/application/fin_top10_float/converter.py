"""fin_top10_float BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# FinTop10FloatHoldersBO → FinTop10Float
from contexts.market.domain.fin_top10_float.entity import FinTop10Float

def fin_top10_float_holders_bo_to_entity(bo) -> "FinTop10Float":
    return FinTop10Float(**bo.model_dump())

