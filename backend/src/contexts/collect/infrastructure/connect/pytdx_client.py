"""Pytdx Client（通达信，step7 简化）

TdxHq_API 单连接非线程安全，线程池并发调用必须串行（threading.Lock）。

Pytdx 客户端单例：每个进程只 new 一次。

使用：
    from contexts.collect.infrastructure.connect.pytdx_client import get_pytdx_client
    client = get_pytdx_client()
    data = await client.run(lambda api: api.get_minute_time_data(...))
"""
from __future__ import annotations

import asyncio
import logging
from threading import Lock
from typing import Any, Callable

from contexts.collect.application.service.base import SourceUnavailable
from shared.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

# 限流键：所有通达信请求共享同一配额
RATE_LIMIT_KEY = "collect:rl:pytdx"

TDX_HOSTS = [
    ("jstdx.gtjas.com", 7709),
    ("shtdx.gtjas.com", 7709),
    ("sztdx.gtjas.com", 7709),
    ("180.153.18.170", 7709),
    ("60.12.136.250", 7709),
    ("115.238.56.198", 7709),
    ("218.75.126.9", 7709),
    ("119.147.212.81", 7709),
]


class PytdxClient:
    def __init__(self) -> None:
        from tdxpy.hq import TdxHq_API
        self._api_cls = TdxHq_API
        self._api = None
        self._connected = False
        self._lock = Lock()

    @property
    def api(self):
        if self._api is None:
            self._api = self._api_cls(heartbeat=True, auto_retry=True)
        return self._api

    def mark_disconnected(self) -> None:
        self._connected = False

    def _ensure_connected(self) -> None:
        api = self.api
        if self._connected:
            try:
                if api.get_security_count(0) is not None:
                    return
            except Exception:
                pass
            self._connected = False
            logger.info("通达信连接已断开，尝试重连...")

        for host, port in TDX_HOSTS:
            try:
                if api.connect(host, port, time_out=5):
                    self._connected = True
                    logger.info("连接通达信服务器成功: %s:%d", host, port)
                    return
            except Exception as e:
                logger.warning("连接 %s:%d 失败: %s", host, port, e)
        raise SourceUnavailable("无法连接任何通达信服务器")

    async def _acquire(self) -> None:
        """按 .env 配置申请一次通达信配额。

        默认关闭（PYTDX_RATE_LIMIT_COUNT=0）—— 公网行情无公开配额文档，
        真正的闸门是下面的 threading.Lock。压测被断连时把 COUNT 调大即可。
        """
        from contexts.collect.infrastructure.cache.rate_limit import acquire
        s = get_settings()
        await acquire(
            key=RATE_LIMIT_KEY,
            max_count=s.PYTDX_RATE_LIMIT_COUNT,
            window_seconds=s.PYTDX_RATE_LIMIT_WINDOW,
        )

    async def run(self, fn: Callable[[Any], Any]) -> Any:
        # 限流放在 Lock 之外：不要让等待配额的时间占住串行槽
        await self._acquire()

        def locked():
            with self._lock:
                self._ensure_connected()
                return fn(self.api)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, locked)

    def disconnect(self) -> None:
        with self._lock:
            if self._api is not None and self._connected:
                try:
                    self._api.disconnect()
                except Exception:
                    pass
                self._connected = False


# ═══════════════════════════════════════════════════════════════
# 模块级单例
# ═══════════════════════════════════════════════════════════════

_pytdx_client: PytdxClient | None = None


def get_pytdx_client() -> PytdxClient:
    """获取 Pytdx 客户端单例（lazy init）"""
    global _pytdx_client
    if _pytdx_client is None:
        _pytdx_client = PytdxClient()
    return _pytdx_client


__all__ = ["RATE_LIMIT_KEY", "PytdxClient", "TDX_HOSTS", "get_pytdx_client"]
