"""数据源注册中心（L1）

管理「数据源名 → DataSourceAPI 实例」的映射关系。

与老 FetcherRegistry（按 Protocol 类型注册）的区别：
  - 老：protocol type → instance（如 KlineFetcher → TushareFetcher 实例）
  - 新：source_name（字符串）→ instance（如 "Tushare" → TushareAPI 实例）

启动期（lifespan）一次性注册，运行期只读——因此不需要写锁。
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from application.port.data_source_api import DataSourceAPI

logger = logging.getLogger(__name__)


class DataSourceRegistry:
    """数据源注册中心

    集中管理「数据源名 → DataSourceAPI 实例/工厂」的映射。
    """

    def __init__(self) -> None:
        self._providers: dict[str, DataSourceAPI] = {}
        self._factories: dict[str, Callable[[], DataSourceAPI]] = {}
        self._lock = threading.Lock()

    # ── 注册（启动期调用）─────────────────────────────────

    def register_instance(self, name: str, instance: DataSourceAPI) -> None:
        """注册单例实例

        Args:
            name: 数据源名（如 "Tushare" / "Adata-THS" / "Pytdx"）
            instance: DataSourceAPI 实现
        """
        with self._lock:
            self._providers[name] = instance
        logger.info(
            "注册数据源: %s ← %s (methods=%s)",
            name,
            type(instance).__name__,
            instance.available_methods,
        )

    def register_factory(self, name: str, factory: Callable[[], DataSourceAPI]) -> None:
        """注册工厂函数（适用于有状态或需并发隔离的数据源）"""
        with self._lock:
            self._factories[name] = factory
        logger.info("注册数据源工厂: %s", name)

    # ── 查询（运行期调用）─────────────────────────────────

    def get(self, name: str) -> DataSourceAPI:
        """获取已注册的单例实例

        Raises:
            KeyError: 未注册该数据源
        """
        if name not in self._providers:
            raise KeyError(
                f"未注册数据源 {name!r}，请检查 setup_default_data_sources() 是否已调用"
            )
        return self._providers[name]

    def create(self, name: str) -> DataSourceAPI:
        """创建新实例（供并发池使用）"""
        if name in self._factories:
            return self._factories[name]()
        if name in self._providers:
            logger.debug("工厂未注册，降级取单例: %s", name)
            return self._providers[name]
        raise KeyError(
            f"未注册数据源 {name!r} 的工厂，且无单例可降级"
        )

    def has(self, name: str) -> bool:
        return name in self._providers or name in self._factories

    def list_sources(self) -> list[str]:
        """列出所有已注册的数据源名（供 API/UI 用）"""
        return list(self._providers.keys())

    def list_methods(self, name: str) -> list[str]:
        """列出某数据源支持的所有方法（供 Pipeline 配置校验用）"""
        if name not in self._providers:
            return []
        return self._providers[name].available_methods

    def validate_method(self, source: str, method: str) -> bool:
        """校验某数据源是否支持某方法"""
        if source not in self._providers:
            return False
        return method in self._providers[source].available_methods

    def __repr__(self) -> str:
        return f"DataSourceRegistry(sources={list(self._providers.keys())})"


# ═══════════════════════════════════════════════════════════════════════
# 全局注册中心（模块单例）
# ═══════════════════════════════════════════════════════════════════════

_registry: DataSourceRegistry | None = None


def get_data_source_registry() -> DataSourceRegistry:
    """获取全局数据源注册中心（延迟初始化）"""
    global _registry
    if _registry is None:
        _registry = DataSourceRegistry()
    return _registry


def setup_default_data_sources() -> DataSourceRegistry:
    """应用启动时调用：注册默认数据源

    在 main.py 的 lifespan 中调用。

    注册策略：
    - TushareAPI：无状态（内部持有 pro_api 实例），单例
    - AdataAPI：单例（adata 内部已做池化）
    - PytdxAPI：单例（PytdxFetcher 内部维护 TCP 连接，复用连接更好）
    """
    reg = get_data_source_registry()

    # ── TushareAPI ──
    from infrastructure.adapter.data_source import TushareAPI

    reg.register_instance("Tushare", TushareAPI())

    # ── AdataAPI ──
    from infrastructure.adapter.data_source import AdataAPI

    try:
        reg.register_instance("Adata-THS", AdataAPI())
    except Exception as e:
        logger.warning("AdataAPI 注册失败: %s", e)

    # ── PytdxAPI ──
    from infrastructure.adapter.data_source import PytdxAPI

    reg.register_instance("Pytdx", PytdxAPI())

    return reg


__all__ = [
    "DataSourceRegistry",
    "get_data_source_registry",
    "setup_default_data_sources",
]
