"""kline BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# KlineBO → Kline
from contexts.market.domain.kline.entity import Kline

def kline_bo_to_entity(bo) -> "Kline":
    args = bo.to_entity_args()
    args.pop("source")
    return Kline.create(**args)

