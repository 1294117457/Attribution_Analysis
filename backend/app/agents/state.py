"""Agent 状态定义"""

from typing import TypedDict, List, Optional, Literal
from datetime import date


class AttributionState(TypedDict, total=False):
    """归因分析 Agent 状态"""

    # 输入
    symbol: str
    name: str
    start_date: date
    end_date: date

    # 中间状态
    klines: Optional[List[dict]]
    news: Optional[List[dict]]
    indicators: Optional[dict]
    anomaly: Optional[dict]
    attribution_result: Optional[dict]

    # 输出
    report: Optional[str]
    confidence: Optional[float]
    error: Optional[str]


class AnomalyState(TypedDict, total=False):
    """异常检测 Agent 状态"""

    symbol: str
    start_date: date
    end_date: date

    klines: Optional[List[dict]]
    indicators: Optional[dict]
    anomalies: List[dict]
    is_anomaly: bool
    report: Optional[str]
    error: Optional[str]
