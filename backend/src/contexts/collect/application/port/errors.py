"""port 契约的错误类型（SDK 错误 → port 错误的翻译目标）

调用方需要据此决定「重试 / 换源 / 降级」。

业务级异常（参数/能力合规）已搬到 `contexts.collect.domain.exceptions`。
本文件只保留 port 契约级：
  - RateLimited      数据源限流
  - SourceUnavailable 数据源不可用

分工：
  - SDK 原始异常（aiohttp / tushare） → 在 fetcher/adapter 中翻译为本文件异常
  - 业务规则异常 → 抛 domain.exceptions
"""
from __future__ import annotations


class RateLimited(Exception):
    """数据源限流（service 捕获并 sleep 重试）"""

    def __init__(self, message: str = "", retry_after: float = 60.0) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class SourceUnavailable(Exception):
    """数据源不可用（service 捕获并标记失败）"""
    pass


__all__ = ["RateLimited", "SourceUnavailable"]
