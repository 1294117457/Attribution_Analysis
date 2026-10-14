"""stock_info BO → Entity 转换器（step7-e 自动生成）"""
from __future__ import annotations


# StockInfoBO → StockInfo
from contexts.market.domain.stock_info.entity import StockInfo

def stock_info_bo_to_entity(bo) -> "StockInfo":
    return StockInfo.create(

        symbol=bo.symbol,
        name=bo.name,
        industry=bo.industry,
        market=bo.market,
        area=bo.area,
        exchange=bo.exchange,
        list_date=bo.list_date,
        delist_date=bo.delist_date,
        list_status=bo.list_status,
        is_hs=bo.is_hs,
        act_name=bo.act_name,
        act_ent_type=bo.act_ent_type,
        ts_code=bo.ts_code,
    )

