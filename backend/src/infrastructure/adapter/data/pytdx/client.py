"""PytdxClient：通达信行情连接 + 同步调用转异步

TdxHq_API 单连接非线程安全，线程池并发调用必须串行（threading.Lock）。
"""
from __future__ import annotations

import asyncio
import logging
from threading import Lock
from typing import Any, Callable

from application.port.data.base import SourceUnavailable

logger = logging.getLogger(__name__)

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
        from tdxpy.hq import TdxHq_API  # 未安装时由 setup_data 捕获

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
                    logger.info("连接通达信服务器成功: %s:%s", host, port)
                    return
            except Exception as e:
                logger.warning("连接 %s:%s 失败: %s", host, port, e)
        raise SourceUnavailable("无法连接任何通达信服务器")

    async def run(self, fn: Callable[[Any], Any]) -> Any:
        """在线程池中持锁执行 fn(api)"""

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


__all__ = ["PytdxClient", "TDX_HOSTS"]
