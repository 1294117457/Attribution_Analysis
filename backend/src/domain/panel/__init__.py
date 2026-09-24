"""面板（Panel）上下文

跨聚合根的"列表面板视图"值对象与组合仓储归此处。
不归属 stock_info / kline / fin_daily_basic / fin_report 任一聚合根。
"""

from domain.panel.repository import StockPanelComposeRepository
from domain.panel.value_objects import StockPanelRow

__all__ = [
    "StockPanelComposeRepository",
    "StockPanelRow",
]