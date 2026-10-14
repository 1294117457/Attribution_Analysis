"""cap_margin_detail BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapMarginDetailBO → CapMarginDetail
from contexts.market.domain.cap_margin_detail.entity import CapMarginDetail

def cap_margin_detail_bo_to_entity(bo) -> "CapMarginDetail":
    return CapMarginDetail(**bo.model_dump())

