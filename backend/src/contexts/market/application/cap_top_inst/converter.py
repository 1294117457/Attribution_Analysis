"""cap_top_inst BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapTopInstBO → CapTopInst
from contexts.market.domain.cap_top_inst.entity import CapTopInst

def cap_top_inst_bo_to_entity(bo) -> "CapTopInst":
    return CapTopInst(**bo.model_dump())

