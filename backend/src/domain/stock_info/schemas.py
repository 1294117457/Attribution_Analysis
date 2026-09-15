"""股票信息领域 Schema（BO/VO）"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from domain.stock_info.entity import StockInfo


class StockInfoBO(BaseModel):
    """股票信息业务对象（采集层产出 → 应用层）

    字段对齐 Tushare stock_basic。
    """

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

    def to_entity(self, id: int = 0) -> StockInfo:
        """转换为领域实体"""
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
            ts_code=self.ts_code,
        )


class StockInfoVO(BaseModel):
    """股票信息视图对象（API 出参）"""

    symbol: str
    ts_code: Optional[str] = None
    name: Optional[str] = None
    area: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    exchange: Optional[str] = None
    list_date: Optional[str] = None
    delist_date: Optional[str] = None
    is_hs: Optional[str] = None
    list_status: Optional[str] = None
    total_shares: Optional[int] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_entity(cls, entity: StockInfo) -> "StockInfoVO":
        return cls(
            symbol=entity.symbol,
            ts_code=entity.ts_code,
            name=entity.name,
            area=entity.area,
            industry=entity.industry.name if entity.industry else None,
            market=entity.market.name if entity.market else None,
            exchange=entity.exchange,
            list_date=_fmt_date(entity.list_date),
            delist_date=_fmt_date(entity.delist_date),
            is_hs=entity.is_hs,
            list_status=entity.list_status,
            total_shares=entity.total_shares,
        )


class StockListItemVO(BaseModel):
    """股票列表项（含 K 线统计）"""

    symbol: str
    name: Optional[str] = None
    industry: Optional[str] = None
    market: Optional[str] = None
    record_count: int = 0
    kline_start: Optional[date] = None
    kline_end: Optional[date] = None


class StockMetaVO(BaseModel):
    """股票元数据（用于前端筛选下拉）"""

    industries: list[str] = Field(default_factory=list)
    markets: list[str] = Field(default_factory=list)
    exchanges: list[str] = Field(default_factory=list)


class SyncResultVO(BaseModel):
    """同步结果"""

    synced_count: int
    inserted: int = 0
    updated: int = 0
    message: str = ""


def _fmt_date(d: Optional[date]) -> Optional[str]:
    if d is None:
        return None
    return d.strftime("%Y%m%d")
