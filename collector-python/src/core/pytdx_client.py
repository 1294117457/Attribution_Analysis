"""Pytdx Client（通达信，step7 简化）

TdxHq_API 单连接非线程安全，线程池并发调用必须串行（threading.Lock）。

Pytdx 客户端单例：每个进程只 new 一次。

使用：
    from core.pytdx_client import get_pytdx_client
    client = get_pytdx_client()
    data = await client.run(lambda api: api.get_minute_time_data(...))
"""
from __future__ import annotations

import asyncio
import logging
from threading import Lock
from typing import Any, Callable

from core.errors import SourceUnavailable

logger = logging.getLogger(__name__)

TDX_HOSTS = [
    ("shtdx.gtjas.com", 7709),      # ★ 实测可返回 K 线（jstdx 虽能连上但行情为空）
    ("jstdx.gtjas.com", 7709),
    ("sztdx.gtjas.com", 7709),
    ("180.153.18.170", 7709),
    ("60.12.136.250", 7709),
    ("115.238.56.198", 7709),
    ("218.75.126.9", 7709),
    ("119.147.212.81", 7709),
]

# ★ 连续多少次「连上但返回空数据」后判定该服务器不可用并切换
EMPTY_RESPONSE_THRESHOLD = 2


def _is_empty(result: Any) -> bool:
    """判空（兼容 DataFrame / list / None / dict）。

    ⚠️ 不能直接用 ``if not result:`` —— DataFrame 的真值是歧义的，
      会抛 ``ValueError: The truth value of a DataFrame is ambiguous``。
    """
    if result is None:
        return True
    empty = getattr(result, "empty", None)
    if empty is not None:
        return bool(empty)
    try:
        return len(result) == 0
    except TypeError:
        return False


class PytdxClient:
    def __init__(self) -> None:
        from tdxpy.hq import TdxHq_API
        self._api_cls = TdxHq_API
        self._api = None
        self._connected = False
        self._lock = Lock()
        # ★ 当前正在使用的服务器下标（换主机时递增）
        self._host_idx = 0
        # ★ 连续「连接成功但取不到数据」的次数 → 达到阈值就换主机
        self._empty_streak = 0

    @property
    def api(self):
        if self._api is None:
            self._api = self._api_cls(heartbeat=True, auto_retry=True)
        return self._api

    def mark_disconnected(self) -> None:
        self._connected = False

    def mark_empty_response(self) -> None:
        """记录一次「连上了但没数据」。

        ★ ★ 为什么需要这个：通达信有多家镜像站，部分站点**能建立 TCP 连接
          也能正常应答协议**（get_security_count 返回 27784），但**行情类接口
          一律返回空**（实测 jstdx.gtjas.com 就是这种）。

          原实现只在「连接失败」时才换主机 → 永远卡在这个空站上，
          用户表现为「分 K 线查询永远返回 0 行，没有任何报错」。
          → 连续空响应达到阈值 → 判定该站不可用。

        ★ 这里**不**直接换主机 —— 换主机由 ``run_with_failover`` 统一负责，
          否则会与它重复轮转（一次失败跳 2 家，快速耗尽候选列表）。
        """
        self._empty_streak += 1
        if self._empty_streak >= EMPTY_RESPONSE_THRESHOLD:
            logger.warning("通达信服务器连续 %d 次返回空数据（判定为不可用）",
                           self._empty_streak)

    def mark_data_ok(self) -> None:
        """收到有效数据 → 重置空响应计数。"""
        self._empty_streak = 0

    def _rotate_host(self) -> None:
        """切换到下一个服务器（并断开当前连接）。"""
        try:
            if self._api is not None:
                self._api.disconnect()
        except Exception:
            pass
        self._connected = False
        self._empty_streak = 0
        self._host_idx = (self._host_idx + 1) % len(TDX_HOSTS)

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

        # ★ 从当前下标开始轮询所有服务器（换主机后从这里继续）
        n = len(TDX_HOSTS)
        for i in range(n):
            idx = (self._host_idx + i) % n
            host, port = TDX_HOSTS[idx]
            try:
                if api.connect(host, port, time_out=5):
                    self._connected = True
                    self._host_idx = idx
                    self._empty_streak = 0
                    logger.info("连接通达信服务器成功: %s:%d", host, port)
                    return
            except Exception as e:
                logger.warning("连接 %s:%d 失败: %s", host, port, e)
        raise SourceUnavailable("无法连接任何通达信服务器")

    async def run(self, fn: Callable[[Any], Any]) -> Any:
        def locked():
            with self._lock:
                self._ensure_connected()
                return fn(self.api)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, locked)

    async def run_with_failover(
        self,
        fn: Callable[[Any], Any],
        *,
        max_hosts: int = 4,
    ) -> Any:
        """执行 fn；若返回**空结果**则换服务器重试。

        ★ 解决「空站」问题：某些通达信镜像能连上、能应答协议，
          但行情接口一律返回空（实测 jstdx.gtjas.com）。
          → 一次取不到就换下一家，最多试 max_hosts 家。

        ★ 注意：只有「连上但结果为空」才换主机；抛异常照常向上抛。
        ★ ⚠️ 判空**不能**用 ``if result:`` —— fn 可能返回 DataFrame，
          它的真值是歧义的（``ValueError: The truth value of a DataFrame
          is ambiguous``）→ 统一用 _is_empty() 判定。
        """
        last_exc: Exception | None = None
        result = None
        for attempt in range(max_hosts):
            try:
                result = await self.run(fn)
            except Exception as e:  # noqa: BLE001
                last_exc = e
                self._rotate_host()
                continue
            if not _is_empty(result):
                self.mark_data_ok()
                return result
            # 空结果 → 换一家
            logger.info("通达信服务器返回空结果，切换下一家重试（第 %d 次）",
                        attempt + 1)
            self._rotate_host()
        if last_exc is not None:
            raise last_exc
        return result

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


__all__ = ["PytdxClient", "TDX_HOSTS", "get_pytdx_client"]
