"""股票信息聚合根"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from domain.base import AggregateRoot
from domain.stock_info.value_objects import Industry, Market


@dataclass
class StockInfo(AggregateRoot):
    """股票信息聚合根

    字段对齐 Tushare stock_basic。
    """

    id: int
    symbol: str
    name: str

    # 业务字段
    industry: Optional[Industry] = None
    market: Optional[Market] = None
    area: Optional[str] = None
    exchange: Optional[str] = None  # SSE / SZSE / BSE

    # 时间
    list_date: Optional[date] = None
    delist_date: Optional[date] = None
    list_status: Optional[str] = None  # L / D / P

    # 沪深港通
    is_hs: Optional[str] = None  # N / H / S

    # 股本
    total_shares: Optional[int] = None

    # 实控人
    act_name: Optional[str] = None
    act_ent_type: Optional[str] = None

    # Tushare 标识
    ts_code: Optional[str] = None

    created_at: Optional[date] = None
    updated_at: Optional[date] = None

    def __post_init__(self):
        AggregateRoot.__init__(self)

    @classmethod
    def create(
        cls,
        symbol: str,
        name: str,
        industry: Optional[str] = None,
        market: Optional[str] = None,
        area: Optional[str] = None,
        exchange: Optional[str] = None,
        list_date: Optional[date] = None,
        delist_date: Optional[date] = None,
        list_status: Optional[str] = None,
        is_hs: Optional[str] = None,
        total_shares: Optional[int] = None,
        act_name: Optional[str] = None,
        act_ent_type: Optional[str] = None,
        ts_code: Optional[str] = None,
        id: int = 0,
    ) -> StockInfo:
        return cls(
            id=id,
            symbol=symbol,
            name=name,
            industry=Industry(industry) if industry else None,
            market=Market.from_market_type(market) if market else None,
            area=area,
            exchange=exchange,
            list_date=list_date,
            delist_date=delist_date,
            list_status=list_status or "L",
            is_hs=is_hs or "N",
            total_shares=total_shares,
            act_name=act_name,
            act_ent_type=act_ent_type,
            ts_code=ts_code,
        )

    def update_name(self, name: str) -> None:
        self.name = name

    def update_industry(self, industry: str) -> None:
        self.industry = Industry(industry)
