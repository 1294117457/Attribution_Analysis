"""数据源注册中心

集中管理「协议类型 → 采集器实例/工厂」的映射关系。

设计约束：
- 启动期（lifespan）一次性注册，运行期只读——因此不需要写锁
- create() 返回工厂函数而非实例，由调用方决定何时创建
- 对外暴露的数据结构仅为 Protocol → instance / factory 的映射，不暴露具体类名
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, TypeVar

from infrastructure.collectors.protocols import (
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
    DailyBasicFetcher,
    ConceptFetcher,
    validate_protocol_implementation,
)

logger = logging.getLogger(__name__)

P = TypeVar("P")


class FetcherRegistry:
    """数据源注册中心

    集中管理「协议类型 → 采集器实例/工厂」的映射关系。
    """

    def __init__(self) -> None:
        # _providers: Protocol type → singleton instance
        self._providers: dict[type, object] = {}
        # _factories: Protocol type → factory callable
        self._factories: dict[type, Callable[[], object]] = {}
        self._lock = threading.Lock()

    # ── 注册（启动期调用）─────────────────────────────────

    def register_instance(self, protocol: type[P], instance: P) -> None:
        """注册单例实例（适用于无状态或内部已做池化的采集器）

        Args:
            protocol: 协议类型（如 KlineFetcher）
            instance: 满足该协议的具体实例
        """
        validate_protocol_implementation(instance, protocol)
        with self._lock:
            self._providers[protocol] = instance
        logger.info("注册单例: %s ← %s", protocol.__name__, type(instance).__name__)

    def register_factory(self, protocol: type[P], factory: Callable[[], P]) -> None:
        """注册工厂函数（适用于有状态或需并发隔离的采集器）

        Args:
            protocol: 协议类型
            factory: 返回满足协议的实例的可调用对象（无参数）
        """
        with self._lock:
            self._factories[protocol] = factory
        logger.info("注册工厂: %s", protocol.__name__)

    # ── 查询（运行期调用）─────────────────────────────────

    def get(self, protocol: type[P]) -> P:
        """获取已注册的单例实例

        Raises:
            KeyError: 未注册该协议的实现
        """
        if protocol not in self._providers:
            raise KeyError(
                f"未注册 {protocol.__name__} 的单例实例，"
                f"请检查 setup_default_registry() 是否已调用"
            )
        return self._providers[protocol]  # type: ignore[return-value]

    def create(self, protocol: type[P]) -> P:
        """创建新实例（供并发池使用）

        必须先调用 register_factory() 注册工厂，否则降级取单例。

        Raises:
            KeyError: 未注册该协议的工厂，且无单例可降级
        """
        if protocol in self._factories:
            return self._factories[protocol]()  # type: ignore[return-value]
        # 降级：从 providers 取单例（要求实现类无状态或内部已做池化）
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


def setup_default_registry() -> FetcherRegistry:
    """应用启动时调用：注册默认数据源

    在 main.py 的 lifespan 中调用。

    注册策略说明：
    - TushareFetcher：无状态（内部持有一个 pro_api 实例，requests.Session 线程安全），
      适合单例注册；但在 collect_task.py 的高并发池场景下，每次 create() 会拿到同一实例，
      若 Tushare 有连接数限制应改用 register_factory()
    - PytdxFetcher：内部维护 TCP 连接（有状态），适合 register_factory() 每次创建新连接；
      但分钟K线是透传不落库、QPS 低，用 register_instance() 单例也可接受

    调用示例（main.py lifespan）：
        from infrastructure.collectors.registry import setup_default_registry
        setup_default_registry()
    """
    reg = get_registry()

    # ── KlineFetcher ─────────────────────────────────────
    # 路由层单例（低并发）
    from infrastructure.collectors.tushare import TushareFetcher
    from domain.kline.schemas import KlineBO

    tushare_singleton = TushareFetcher(KlineBO)
    reg.register_instance(KlineFetcher, tushare_singleton)

    # 后台并发池工厂（高并发，每 worker 新实例）
    # 当前 TushareFetcher 内部 pro_api 线程安全，单例够用；
    # 若后续出现连接数瓶颈，改为 factory 模式
    reg.register_factory(KlineFetcher, lambda: TushareFetcher(KlineBO))

    # ── StockBasicFetcher ─────────────────────────────────
    # 与 KlineFetcher 共用同一 TushareFetcher 实例（source_name = "Tushare"）
    reg.register_instance(StockBasicFetcher, tushare_singleton)
    reg.register_factory(StockBasicFetcher, lambda: TushareFetcher(KlineBO))

    # ── DailyBasicFetcher ─────────────────────────────────
    reg.register_instance(DailyBasicFetcher, tushare_singleton)
    reg.register_factory(DailyBasicFetcher, lambda: TushareFetcher(KlineBO))

    # ── MinuteKlineFetcher ────────────────────────────────
    # PytdxFetcher 有状态（维护 TCP 连接），单例复用连接
    # 若未来需要并发隔离分钟K线采集，可改为 register_factory(PytdxFetcher)
    from infrastructure.collectors.pytdx import PytdxFetcher

    pytdx_fetcher = PytdxFetcher()
    reg.register_instance(MinuteKlineFetcher, pytdx_fetcher)
    reg.register_factory(MinuteKlineFetcher, PytdxFetcher)

    return reg
