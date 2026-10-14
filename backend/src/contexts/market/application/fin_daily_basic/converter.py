"""fin_daily_basic BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# FinDailyBasicBO → FinDailyBasic
from contexts.market.domain.fin_daily_basic.entity import FinDailyBasic

def fin_daily_basic_bo_to_entity(bo) -> "FinDailyBasic":
    return FinDailyBasic(**bo.model_dump())

