"""bo — 从 contexts/data/application/port 拆出（step7-c）"""
from __future__ import annotations

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from shared.interface.validators import Symbol
from contexts.collect.application.port.params import ListStatus, SymbolParams, TradeDateParams
from contexts.market.domain.entities.stock_info.entity import StockInfo


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

    # §1.1 补 Tushare stock_basic 文档 4 字段
    fullname: Optional[str] = Field(None, description="股票全称")
    enname: Optional[str] = Field(None, description="英文全称")
    cnspell: Optional[str] = Field(None, description="拼音缩写")
    curr_type: Optional[str] = Field(None, description="交易货币")








    def to_entity(self) -> "StockInfo":
        """BO -> Entity 便利方法（委托 from_bo）"""
        return StockInfo.from_bo(self)


    @classmethod
    def from_entity(cls, entity) -> "StockInfoBO":
        """从 Entity 构造 BO（Application 接受 Domain 的 Entity）

        利用 BO 的 model_fields 判断哪些字段是必需的；
        Entity 中为 None 的字段会跳过（让 BO 用默认值）。
        """
        kwargs = {}
        for fname, field in cls.model_fields.items():
            if fname == "symbol":
                kwargs[fname] = entity.symbol
                continue
            if not hasattr(entity, fname):
                continue
            value = getattr(entity, fname)
            # 如果字段是必需的且 Entity 值为 None，则跳过（BO 会有默认值）
            if value is None and field.is_required():
                continue
            kwargs[fname] = value
        return cls(**kwargs)