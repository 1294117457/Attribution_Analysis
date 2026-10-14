"""cap_top_list BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapTopListBO → CapTopList
from contexts.market.domain.cap_top_list.entity import CapTopList

def cap_top_list_bo_to_entity(bo) -> "CapTopList":
    return CapTopList(**bo.model_dump())

