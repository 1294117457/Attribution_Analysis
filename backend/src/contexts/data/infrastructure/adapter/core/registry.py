"""DataPortRegistry：注册表式工厂（一个 Port → 多个 Adapter）

register 时沿 MRO 找到 DataPort 的直接子类，即为该 Adapter 所属的 Port（自动归类）。
注册表里存的是套好横向装饰器的实例。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from contexts.data.application.port.base import PORT_META_FIELDS, DataPort
from contexts.data.infrastructure.adapter.core.base import AdapterBase
from contexts.data.infrastructure.adapter.core.decorators import THROTTLE_GROUPS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _Entry:
    raw: Any          # 原始 Adapter（读实现方属性）
    wrapped: Any      # 装饰器链包装后的实例（实际调用）


def port_of(adapter_cls: type) -> type[DataPort]:
    """沿 MRO 找 DataPort 的直接子类"""
    for klass in adapter_cls.__mro__:
        if klass is DataPort:
            continue
        if any(base is DataPort or getattr(base, "__origin__", None) is DataPort
               for base in klass.__dict__.get("__orig_bases__", klass.__bases__)):
            return klass
    raise TypeError(f"{adapter_cls.__name__} 未继承任何 XxxPort")


def _disabled_tools() -> set[str]:
    from shared.infrastructure.config.settings import get_settings
    raw = get_settings().DATA_SOURCE_DISABLED or ""
    return {t.strip() for t in raw.split(",") if t.strip()}


class DataPortRegistry:
    def __init__(self) -> None:
        self._ports: dict[str, type[DataPort]] = {}
        self._entries: dict[type[DataPort], list[_Entry]] = {}

    def register(self, adapter: DataPort, *, wrap: Callable[[DataPort], Any]) -> None:
        cls = type(adapter)
        port = port_of(cls)
        self._validate(cls, port)
        existing = self._ports.get(port.name)
        if existing is not None and existing is not port:
            raise ValueError(f"Port 名称 {port.name} 重复：{existing.__name__} / {port.__name__}")
        entries = self._entries.setdefault(port, [])
        if any(e.raw.tool == adapter.tool for e in entries):
            raise ValueError(f"{port.name} 下 tool={adapter.tool} 重复注册")
        self._ports[port.name] = port
        entries.append(_Entry(raw=adapter, wrapped=wrap(adapter)))
        entries.sort(key=lambda e: e.raw.priority)

    @staticmethod
    def _validate(cls: type, port: type[DataPort]) -> None:
        if not issubclass(cls, AdapterBase):
            raise TypeError(f"{cls.__name__} 必须继承 AdapterBase")
        if not cls.tool or not cls.origin:
            raise TypeError(f"{cls.__name__} 未填写 tool / origin")
        if cls.throttle_group not in THROTTLE_GROUPS:
            raise ValueError(
                f"{cls.__name__}.throttle_group={cls.throttle_group!r} 未定义，可选 {list(THROTTLE_GROUPS)}"
            )
        for klass in cls.__mro__:
            if klass is port:
                break
            overridden = [f for f in PORT_META_FIELDS if f in klass.__dict__]
            if overridden:
                raise TypeError(f"{cls.__name__} 不允许覆盖 Port 元数据: {overridden}")
        for f in ("name", "label", "facet", "Params", "Item"):
            if not hasattr(port, f):
                raise TypeError(f"{port.__name__} 未声明 {f}")

    def port(self, name: str) -> type[DataPort]:
        port = self._ports.get(name)
        if port is None:
            raise KeyError(f"未知数据接口: {name}")
        return port

    def find_port(self, name: str) -> Optional[type[DataPort]]:
        return self._ports.get(name)

    def ports(self) -> list[type[DataPort]]:
        return list(self._ports.values())

    def adapters(self, port: type[DataPort]) -> list[Any]:
        """按 priority 升序，已过滤 DATA_SOURCE_DISABLED"""
        disabled = _disabled_tools()
        return [e.wrapped for e in self._entries.get(port, []) if e.raw.tool not in disabled]

    def raw_adapters(self, port: type[DataPort]) -> list[Any]:
        disabled = _disabled_tools()
        return [e.raw for e in self._entries.get(port, []) if e.raw.tool not in disabled]

    def summary(self) -> dict[str, list[str]]:
        return {p.name: [e.raw.tool for e in self._entries.get(p, [])] for p in self._ports.values()}


_registry: Optional[DataPortRegistry] = None


def get_data_port_registry() -> DataPortRegistry:
    global _registry
    if _registry is None:
        _registry = DataPortRegistry()
    return _registry


__all__ = ["DataPortRegistry", "get_data_port_registry", "port_of"]
