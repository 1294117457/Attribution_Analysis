"""base_adj_factor BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# BaseAdjFactorBO → BaseAdjFactor
from contexts.market.domain.base_adj_factor.entity import BaseAdjFactor

def base_adj_factor_bo_to_entity(bo) -> "BaseAdjFactor":
    return BaseAdjFactor(**bo.model_dump())

