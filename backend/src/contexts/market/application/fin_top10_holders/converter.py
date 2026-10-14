"""fin_top10_holders BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# FinTop10HoldersBO → FinTop10Holders
from contexts.market.domain.fin_top10_holders.entity import FinTop10Holders

def fin_top10_holders_bo_to_entity(bo) -> "FinTop10Holders":
    return FinTop10Holders(**bo.model_dump())

