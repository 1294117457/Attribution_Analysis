"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from contexts.data.application.port.base import DataPort
from shared.interface.validators import Symbol
from contexts.data.application.port.types import ListStatus, SymbolParams, TradeDateParams


class StockInfoBO(BaseModel):
    """股票信息业务对象（字段对齐 Tushare stock_basic）"""

    symbol: str = Field(..., description="股票代码（6位）")
    ts_code: Optional[str] = Field(None, description="Tushare 统一代码")
    name: str = Field("", description="股票名称")
    area: Optional[str] = Field(None, description="地域")
    industry: Optional[str] = Field(None, description="行业")
    market: Optional[str] = Field(None, description="市场类型")
    exchange: Optional[str] = Field(None, description="交易所 SSE/SZSE/BSE")
    list_date: Optional[date] = Field(None, description="上市日期")
    delist_date: Optional[date] = Field(None, description="退市日期")
    list_status: Optional[str] = Field("L", description="上市状态 L/D/P")
    is_hs: Optional[str] = Field("N", description="沪深港通 N/H/S")
    act_name: Optional[str] = Field(None, description="实控人名称")
    act_ent_type: Optional[str] = Field(None, description="实控人企业性质")

    def to_entity(self, id: int = 0) -> "StockInfo":
        """转换为领域实体"""
        from contexts.market.domain.stock_info.entity import StockInfo
        return StockInfo.create(
            id=id,
            symbol=self.symbol,
            name=self.name,
            industry=self.industry,
            market=self.market,
            area=self.area,
            exchange=self.exchange,
            list_date=self.list_date,
            delist_date=self.delist_date,
            list_status=self.list_status,
            is_hs=self.is_hs,
            act_name=self.act_name,
            act_ent_type=self.act_ent_type,
            ts_code=self.ts_code,
        )


