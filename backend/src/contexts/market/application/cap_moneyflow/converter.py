"""cap_moneyflow BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapMoneyflowBO → CapMoneyflow
from contexts.market.domain.cap_moneyflow.entity import CapMoneyflow

def cap_moneyflow_bo_to_entity(bo) -> "CapMoneyflow":
    return CapMoneyflow(**bo.model_dump())

