"""采集器协议（按数据类型拆分）

协议放置在 infrastructure 层是务实选择：
- 消费方（application / route）依赖协议
- 实现方（infrastructure/collectors/*）实现协议
- 不追求严格 DDD 的"由消费方定义接口"，以避免循环依赖

已定义的小协议：
- KlineFetcher          — 日K线采集
- MinuteKlineFetcher   — 分钟K线采集
- StockBasicFetcher     — 股票基本信息采集
- DailyBasicFetcher    — 日频估值采集
- ConceptFetcher       — 概念板块采集（预留，AKShare 实现）
"""

from __future__ import annotations

import inspect
from typing import Any, Protocol, TypeVar, runtime_checkable

from infrastructure.collectors.interfaces import CollectParams

P = TypeVar("P")

# ═══════════════════════════════════════════════════════════════════════
# 协议定义
# ═══════════════════════════════════════════════════════════════════════


@runtime_checkable
class KlineFetcher(Protocol):
    """日K线采集协议"""

    def fetch(self, params: CollectParams) -> list[Any]:
        """采集 K 线，返回 KlineBO 列表"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称，如 'Tushare'"""
        ...


@runtime_checkable
class MinuteKlineFetcher(Protocol):
    """分钟K线采集协议

    参数签名中提供了默认值，兼容 PytdxFetcher 的实际签名。
    """

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
        name: str = "",
    ) -> list[Any]:
        """异步采集分钟 K 线，返回 MinuteKlineBO 列表"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称，如 'Pytdx'"""
        ...


@runtime_checkable
class StockBasicFetcher(Protocol):
    """股票基本信息采集协议"""

    def fetch_stock_basic(self, params: CollectParams) -> list[Any]:
        """采集股票基本信息，返回 StockInfoBO 列表"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...


@runtime_checkable
class DailyBasicFetcher(Protocol):
    """日频估值指标采集协议"""

    def fetch_daily_basic(self, trade_date: str) -> list[Any]:
        """采集日频估值，返回 FinDailyBasicBO 列表

        Args:
            trade_date: YYYYMMDD 格式日期
        """
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...


@runtime_checkable
class ConceptFetcher(Protocol):
    """概念板块采集协议（预留，AKShare 实现）"""

    def fetch_concept_list(self) -> list[Any]:
        """获取概念板块列表"""
        ...

    def fetch_concept_stocks(self, concept_name: str) -> list[Any]:
        """获取概念板块成分股"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...


# ═══════════════════════════════════════════════════════════════════════
# 签名校验工具（补充 @runtime_checkable 的盲区）
# ═══════════════════════════════════════════════════════════════════════


def _check_protocol_signature(
    instance: object,
    protocol: type,
    method_name: str,
) -> None:
    """比对实例方法与协议方法的参数签名

    @runtime_checkable 只检查方法是否存在，不检查签名和默认值。
    本函数检查关键方法的参数列表，防止注册时放行签名不兼容的实现。

    注意：只比对参数名列表（忽略 self/cls），暂不比对默认值，
    因为 Python 允许实现类提供比协议更宽松的默认值。
    Property 不参与签名比对（inspect.signature 不支持 property 对象）。
    """
    proto_method = getattr(protocol, method_name, None)
    instance_method = getattr(instance, method_name, None)

    # property 跳过（inspect.signature 不支持 property 对象）
    if isinstance(proto_method, property) or isinstance(instance_method, property):
        return

    if proto_method is None or instance_method is None:
        return  # 方法不存在时不报错，由 @runtime_checkable 兜底

    proto_sig = inspect.signature(proto_method)
    try:
        instance_sig = inspect.signature(instance_method)
    except (ValueError, TypeError):
        # 内置方法或无法反射时跳过
        return

    proto_params = list(proto_sig.parameters.keys())
    instance_params = list(instance_sig.parameters.keys())

    # 忽略 self/cls（协议定义不含 self，实现含 self），对齐后再比较
    if proto_params and proto_params[0] in ("self", "cls"):
        proto_params = proto_params[1:]
    if instance_params and instance_params[0] in ("self", "cls"):
        instance_params = instance_params[1:]

    if proto_params != instance_params:
        raise TypeError(
            f"{type(instance).__name__}.{method_name} 参数列表 {instance_params} "
            f"与协议 {protocol.__name__}.{method_name} 要求 {proto_params} 不匹配"
        )


def validate_protocol_implementation(
    instance: object,
    protocol: type[P],
) -> None:
    """校验实例是否完整实现了给定协议的所有方法签名

    在 registry.register_instance() / register_factory() 内部调用，
    也可在测试中单独使用。
    """
    for attr_name in dir(protocol):
        if attr_name.startswith("_"):
            continue
        attr = getattr(protocol, attr_name)
        if callable(attr) or isinstance(attr, property):
            _check_protocol_signature(instance, protocol, attr_name)
