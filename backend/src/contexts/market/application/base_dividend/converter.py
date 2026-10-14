"""base_dividend BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# BaseDividendBO → BaseDividend
from contexts.market.domain.base_dividend.entity import BaseDividend

def base_dividend_bo_to_entity(bo) -> "BaseDividend":
    return BaseDividend(**bo.model_dump())

