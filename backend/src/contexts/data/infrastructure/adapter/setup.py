"""装配：创建各数据源 Client、实例化 Adapter、套装饰器、注册进 DataPortRegistry

某个 SDK 未安装 / 未配置时只告警并跳过该数据源，不影响其它数据源与应用启动。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Iterable

from contexts.data.infrastructure.adapter.core.decorators import build_decorators
from contexts.data.infrastructure.adapter.core.registry import DataPortRegistry, get_data_port_registry

logger = logging.getLogger(__name__)

_done = False


def _tushare() -> tuple[Any, Iterable[type]]:
    from infrastructure.adapter.data.tushare import ADAPTERS, TushareClient
    from infrastructure.config.settings import get_settings
    return TushareClient(get_settings().TUSHARE_TOKEN), ADAPTERS


def _adata() -> tuple[Any, Iterable[type]]:
    from infrastructure.adapter.data.adata import ADAPTERS, AdataClient
    return AdataClient(), ADAPTERS


def _pytdx() -> tuple[Any, Iterable[type]]:
    from infrastructure.adapter.data.pytdx import ADAPTERS, PytdxClient
    return PytdxClient(), ADAPTERS


SOURCES: dict[str, Callable[[], tuple[Any, Iterable[type]]]] = {
    "tushare": _tushare,
    "adata": _adata,
    "pytdx": _pytdx,
}


def setup_data(registry: DataPortRegistry | None = None) -> DataPortRegistry:
    """幂等：重复调用直接返回已装配的注册表"""
    global _done
    registry = registry or get_data_port_registry()
    if _done:
        return registry
    for name, make in SOURCES.items():
        try:
            client, adapters = make()
        except Exception as e:
            logger.warning("数据源 %s 不可用，已跳过: %s", name, e)
            continue
        for cls in adapters:
            registry.register(cls(client), wrap=build_decorators)
    _done = True
    for port_name, tools in registry.summary().items():
        logger.info("DataPort %-22s -> %s", port_name, ", ".join(tools))
    return registry


__all__ = ["SOURCES", "setup_data"]
