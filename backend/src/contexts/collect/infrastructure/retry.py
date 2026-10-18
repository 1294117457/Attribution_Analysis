"""retry — 重试机制（infrastructure 实现，替代旧 RetryDecorator）

两类使用方式：

1. 装饰器式：@retry_on_rate_limited(retries=2)
       装饰 fetcher / service 的方法

2. 函数式：fetch_with_retry(lambda: fetcher.fetch(...), retries=2)
       包裹一个 0 参 lambda 调 fetcher

两者都捕获 port 契约级 RateLimited 后按 retry_after 退避重试。
"""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Awaitable, Callable, TypeVar

from contexts.collect.application.port.errors import RateLimited

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════
# 1. 装饰器：用于 service 入口方法
# ═══════════════════════════════════════════════════════════════


def retry_on_rate_limited(retries: int = 2) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """装饰器：捕获 RateLimited 后退避 retries 次"""

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            last_err: RateLimited | None = None
            for attempt in range(retries + 1):
                try:
                    return await fn(*args, **kwargs)
                except RateLimited as e:
                    last_err = e
                    if attempt < retries:
                        logger.debug(
                            "rate_limited, retry %d/%d after %.1fs",
                            attempt + 1, retries, e.retry_after,
                        )
                        await asyncio.sleep(e.retry_after)
                        continue
                    raise
            if last_err is not None:
                raise last_err
            raise RuntimeError("unreachable")

        return wrapper

    return decorator


# ═══════════════════════════════════════════════════════════════
# 2. 函数式：用于 0 参 lambda 包裹 fetcher.fetch()
# ═══════════════════════════════════════════════════════════════


async def fetch_with_retry(
    fn: Callable[[], Awaitable[list]],
    retries: int = 2,
) -> list:
    """调 fn()，捕获 RateLimited 后退避重试；返回 list

    兼容历史使用方式：service.collect 里写
        await fetch_with_retry(lambda: self._fetcher.fetch(...))
    """
    last_err: RateLimited | None = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except RateLimited as e:
            last_err = e
            if attempt < retries:
                await asyncio.sleep(e.retry_after)
                continue
            raise
    if last_err is not None:
        raise last_err
    return []


__all__ = ["fetch_with_retry", "retry_on_rate_limited"]
