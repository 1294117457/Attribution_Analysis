"""cap_block_trade BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# CapBlockTradeBO → CapBlockTrade
from contexts.market.domain.cap_block_trade.entity import CapBlockTrade

def cap_block_trade_bo_to_entity(bo) -> "CapBlockTrade":
    return CapBlockTrade(**bo.model_dump())

