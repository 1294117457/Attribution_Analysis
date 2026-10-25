"""tech 仓储子包：技术面采集所需的持久化操作

- daily_kline_repo     → tech_daily            （K 线 upsert + 查询）
- trade_calendar_repo  → tech_trade_cal        （交易日历读取）
- stock_name_repo      → fundamental_stock_basic（代码 → 名称映射）

统一约定：session 由 service 层持有、以参数传入；repo 不自行开关事务。
"""

from contexts.collect.infrastructure.persistence.repositories.tech.daily_kline_repo import (
    DailyKlineRepository,
)
from contexts.collect.infrastructure.persistence.repositories.tech.stock_name_repo import (
    StockNameRepository,
)
from contexts.collect.infrastructure.persistence.repositories.tech.trade_calendar_repo import (
    TradeCalendarRepository,
)

__all__ = [
    "DailyKlineRepository",
    "StockNameRepository",
    "TradeCalendarRepository",
]