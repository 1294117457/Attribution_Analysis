"""市场交易时段领域服务（跨聚合根的纯算法）

业务规则（领域知识）：
- 交易时段定义为工作日 09:25–11:30、13:00–15:00（节假日按工作日处理）
- 非交易时段缓存应缓存到下次开盘（午休→13:00，收盘后→下个工作日 09:25）
- 这些规则是金融市场的领域知识，与具体技术实现无关

按 DDD.md §3.2：跨聚合根的纯算法放在 `domain/service/`。
- 无 IO、无状态变更
- 不依赖任何外部 SDK
- 可独立单测
"""
from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo


# 上海 A 股市场时区（领域常量）
class MarketTimeZone:
    """市场时区（Asia/Shanghai）"""

    VALUE = ZoneInfo("Asia/Shanghai")


# 交易时段定义（领域常量）
_MORNING_SESSION = (time(9, 25), time(11, 30))   # 上午盘
_AFTERNOON_SESSION = (time(13, 0), time(15, 0))  # 下午盘


def market_now() -> datetime:
    """获取当前市场时间（带时区）"""
    return datetime.now(MarketTimeZone.VALUE)


def is_trading_time(now: Optional[datetime] = None) -> bool:
    """判断是否处于交易时段

    业务规则：
    - 工作日 09:25–11:30、13:00–15:00 为交易时段
    - 节假日按工作日处理（即周末不计入）

    Args:
        now: 待判断的时间；None 时取当前市场时间

    Returns:
        True 表示处于交易时段
    """
    now = (now or market_now()).astimezone(MarketTimeZone.VALUE)
    if now.weekday() >= 5:
        return False
    t = now.time()
    return (
        _MORNING_SESSION[0] <= t < _MORNING_SESSION[1]
        or _AFTERNOON_SESSION[0] <= t < _AFTERNOON_SESSION[1]
    )


def ttl_for(ttl_trading: int, now: Optional[datetime] = None) -> int:
    """根据交易时段决定缓存 TTL

    业务规则：
    - 交易时段：使用 ttl_trading
    - 非交易时段：缓存到下一个开盘时刻

    Args:
        ttl_trading: 交易时段下的 TTL 秒数
        now: 当前时间；None 时取当前市场时间

    Returns:
        建议的 Redis TTL 秒数
    """
    now = (now or market_now()).astimezone(MarketTimeZone.VALUE)
    if is_trading_time(now):
        return ttl_trading

    t = now.time()
    if now.weekday() < 5 and t < _MORNING_SESSION[0]:
        # 当天开盘前（00:00 - 09:25）
        target = now.replace(hour=9, minute=25, second=0, microsecond=0)
    elif now.weekday() < 5 and _MORNING_SESSION[1] <= t < _AFTERNOON_SESSION[0]:
        # 午休（11:30 - 13:00）
        target = now.replace(hour=13, minute=0, second=0, microsecond=0)
    else:
        # 收盘后/周末 → 下个工作日开盘
        day = now + timedelta(days=1)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        target = day.replace(hour=9, minute=25, second=0, microsecond=0)
    return max(ttl_trading, int((target - now).total_seconds()))


class MarketSessionService:
    """市场交易时段领域服务（OO 封装，保留旧 API 兼容性）

    推荐使用本服务类（OO 调用）而非散落的函数式 API，
    便于测试 mock 与依赖注入。

    使用示例：
        svc = MarketSessionService()
        ttl = svc.ttl_for(ttl_trading=15)
        if svc.is_trading_time():
            ...
    """

    def market_now(self) -> datetime:
        return market_now()

    def is_trading_time(self, now: Optional[datetime] = None) -> bool:
        return is_trading_time(now)

    def ttl_for(self, ttl_trading: int, now: Optional[datetime] = None) -> int:
        return ttl_for(ttl_trading, now)
