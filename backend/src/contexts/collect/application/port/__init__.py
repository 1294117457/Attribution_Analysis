"""application.collect.port — 对外抽象契约

一个 port 是一份契约，下面几样都属于契约：
  - 接口 / Protocol
  - 参数类型（XxxParams）
  - port 契约级错误（RateLimited / SourceUnavailable）

业务级异常放在 `contexts.collect.domain.exceptions`。
限流 / 重试这种**机制**实现放在 `infrastructure.cache.rate_limit / retry`（装饰器）。

⚠️ SchedulerPort 已在 step7 拆分中移至 `contexts.scheduler.application.port`，
   collect 模块不再持有调度相关契约。
"""
from __future__ import annotations

from contexts.collect.application.port.errors import (
    RateLimited,
    SourceUnavailable,
)
from contexts.collect.application.port.params import (
    EmptyParams,
    IndexCodeParams,
    ListStatus,
    MinuteKlineParams,
    StockBasicParams,
    SymbolParams,
    TradeDateParams,
)

__all__ = [
    # port 契约级错误
    "RateLimited", "SourceUnavailable",
    # 参数类型
    "ListStatus", "EmptyParams", "IndexCodeParams", "MinuteKlineParams",
    "StockBasicParams", "SymbolParams", "TradeDateParams",
]
