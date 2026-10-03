"""数据源注册中心（application 层抽象）

集中管理「协议类型 → 采集器实例/工厂」的映射关系。

设计约束（DDD.md §2.2 / §4）：
- application 层只持有抽象协议 + 注册中心，不依赖任何具体 SDK
- 不在本文件 import `infrastructure.*` 或 `route.*` —— 具体实现由 lifespan / DI 注入
- 仅暴露「按协议注册 / 获取实例」两个动作

实际实例注入由 `infrastructure.config.di.setup_default_registry(...)` 完成。
"""
from __future__ import annotations

import logging
import threading
from typing import Callable, TypeVar

from application.port.collector_port import (
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
    DailyBasicFetcher,
    FinReportFetcher,
    ConceptFetcher,
    validate_protocol_implementation,
)

logger = logging.getLogger(__name__)

P = TypeVar("P")


class FetcherRegistry:
    """数据源注册中心 — 协议 → 实例/工厂的映射"""

    def __init__(self) -> None:
        self._providers: dict[type, object] = {}
        self._factories: dict[type, Callable[[], object]] = {}
        self._lock = threading.Lock()

    # ── 注册（启动期调用）─────────────────────────────────

    def register_instance(self, protocol: type[P], instance: P) -> None:
        """注册单例实例（适用于无状态或内部已做池化的采集器）"""
        validate_protocol_implementation(instance, protocol)
        with self._lock:
            self._providers[protocol] = instance
        logger.info("注册单例: %s ← %s", protocol.__name__, type(instance).__name__)

    def register_factory(self, protocol: type[P], factory: Callable[[], P]) -> None:
        """注册工厂函数（适用于有状态或需并发隔离的采集器）"""
        with self._lock:
            self._factories[protocol] = factory
        logger.info("注册工厂: %s", protocol.__name__)

    # ── 查询（运行期调用）─────────────────────────────────

    def get(self, protocol: type[P]) -> P:
        """获取已注册的单例实例；未注册则抛 KeyError"""
        if protocol not in self._providers:
            raise KeyError(
                f"未注册 {protocol.__name__} 的单例实例，"
                f"请检查 setup_default_registry() 是否已调用"
            )
        return self._providers[protocol]  # type: ignore[return-value]

    def create(self, protocol: type[P]) -> P:
        """创建新实例（供并发池使用）；未注册工厂则降级取单例"""
        if protocol in self._factories:
            return self._factories[protocol]()  # type: ignore[return-value]
        if protocol in self._providers:
            logger.debug("工厂未注册，降级取单例: %s", protocol.__name__)
            return self._providers[protocol]  # type: ignore[return-value]
        raise KeyError(
            f"未注册 {protocol.__name__} 的工厂，且无单例可降级，"
            f"请检查 setup_default_registry()"
        )

    def has(self, protocol: type) -> bool:
        """查询某协议是否已注册（单例或工厂）"""
        return protocol in self._providers or protocol in self._factories

    def __repr__(self) -> str:
        return (
            f"FetcherRegistry("
            f"providers={list(k.__name__ for k in self._providers.keys())}, "
            f"factories={list(k.__name__ for k in self._factories.keys())})"
        )


# ── 全局注册中心（模块单例）─────────────────────────────────

_registry: FetcherRegistry | None = None


def get_registry() -> FetcherRegistry:
    """获取全局注册中心（延迟初始化）"""
    global _registry
    if _registry is None:
        _registry = FetcherRegistry()
    return _registry


# ── 协议类型 re-export（方便 DI / 外部 import）─────────────────

__all__ = [
    "FetcherRegistry",
    "get_registry",
    "KlineFetcher",
    "MinuteKlineFetcher",
    "StockBasicFetcher",
    "DailyBasicFetcher",
    "FinReportFetcher",
    "ConceptFetcher",
]