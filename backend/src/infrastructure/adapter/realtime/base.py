"""实时接口基类与交易时段工具

实时接口 = 页面当前要看的数据：按需请求数据源，结果只写 Redis，不入库、不建任务记录。
缓存 / 单飞 / 限流 / 降级 / 统计由 application.service.realtime_app_service 统一处理，
子类只描述「缓存键、怎么取、失败怎么降级」。

配套设计文档：docs/dev/step2/04采集管理优化/06实时数据接口.md §3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, time, timedelta
from typing import Any, ClassVar, Optional
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("Asia/Shanghai")

_MORNING = (time(9, 25), time(11, 30))
_AFTERNOON = (time(13, 0), time(15, 0))


def market_now() -> datetime:
    return datetime.now(MARKET_TZ)


def is_trading_time(now: Optional[datetime] = None) -> bool:
    """工作日 09:25–11:30、13:00–15:00（节假日按工作日处理）"""
    now = (now or market_now()).astimezone(MARKET_TZ)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return _MORNING[0] <= t < _MORNING[1] or _AFTERNOON[0] <= t < _AFTERNOON[1]


def ttl_for(ttl_trading: int, now: Optional[datetime] = None) -> int:
    """交易时段返回 ttl_trading；其余时段缓存到下一次开盘（午休到 13:00，收盘后到下个工作日 09:25）"""
    now = (now or market_now()).astimezone(MARKET_TZ)
    if is_trading_time(now):
        return ttl_trading

    t = now.time()
    if now.weekday() < 5 and t < _MORNING[0]:
        target = now.replace(hour=9, minute=25, second=0, microsecond=0)
    elif now.weekday() < 5 and _MORNING[1] <= t < _AFTERNOON[0]:
        target = now.replace(hour=13, minute=0, second=0, microsecond=0)
    else:
        day = now + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        target = day.replace(hour=9, minute=25, second=0, microsecond=0)
    return max(ttl_trading, int((target - now).total_seconds()))


class BaseRealtimeQuery(ABC):
    """实时接口基类（与 BaseCollectTask 共用目录元数据字段）"""

    name: ClassVar[str] = ""
    facet: ClassVar[str] = ""
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""
    sort_order: ClassVar[int] = 100
    # 同源限流分组：ths / tdx
    source: ClassVar[str] = ""
    source_label: ClassVar[str] = ""
    # 交易时段缓存秒数
    ttl_trading: ClassVar[int] = 15
    # 采集管理页展示：谁在调用本接口
    consumers: ClassVar[tuple[str, ...]] = ()
    # 采集管理「试查」的默认参数
    sample_params: ClassVar[dict] = {}

    def normalize(self, params: dict) -> dict:
        """校验 / 规范化参数；非法时抛 ValueError"""
        return dict(params)

    @abstractmethod
    def cache_key(self, params: dict) -> str: ...

    @abstractmethod
    async def fetch(self, params: dict) -> Any:
        """请求数据源，返回可 JSON 序列化的结果；空数据返回 None，失败抛异常"""

    async def fallback(self, params: dict) -> Any:
        """数据源失败时的降级结果（会标记 stale）；默认无"""
        return None


__all__ = ["BaseRealtimeQuery", "MARKET_TZ", "is_trading_time", "market_now", "ttl_for"]
