"""数据端口根约束：DataPort / DataCommand / DataResult / 错误类型 / DataGatewayPort

三层结构（docs/backend-docs/dev/step5/02底层采集优化/01-核心骨架.md）：
- DataPort                       第一层：根约束
- XxxPort(DataPort[P, R])        第二层：接口约束，声明"取什么"（元数据 + Params + Item）
- XxxAdapter(XxxPort, AdapterBase)  第三层：infrastructure 中的底层实现

本模块不依赖 infrastructure / route。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, ClassVar, Generic, Optional, Protocol, TypeVar

from pydantic import BaseModel

P = TypeVar("P", bound=BaseModel)
R = TypeVar("R", bound=BaseModel)


# ═══════════════════════════════════════════════════════════════════════════════
# 调用策略 / 缓存策略
# ═══════════════════════════════════════════════════════════════════════════════


class CallPolicy(StrEnum):
    COLLECT = "collect"     # 采集：限频时等待重试，不走缓存
    QUERY = "query"         # 查询：限频不等待；Port 声明了 cache 时走缓存


@dataclass(frozen=True)
class CachePolicy:
    ttl_trading: int                     # 交易时段缓存秒数；非交易时段由 market_session.ttl_for 决定
    consumers: tuple[str, ...] = ()      # 采集管理页展示：谁在调用本接口


# ═══════════════════════════════════════════════════════════════════════════════
# 错误分类（底层实现只抛这几种，Gateway 按类型决定是否换源）
# ═══════════════════════════════════════════════════════════════════════════════


class DataError(Exception):
    """数据端口错误基类"""

    # Gateway 换源失败时填入各实现的 (source, error)，供 HTTP 错误响应回显
    attempts: list[tuple[str, str]] = []


class InvalidParams(DataError, ValueError):
    """参数不合法：不重试、不换源"""


class NotSupported(DataError, ValueError):
    """该实现不支持这组参数（或没有可用实现）：跳过，试下一个"""


class RateLimited(DataError, RuntimeError):
    """数据源限频：COLLECT 等待后重试，QUERY 直接抛"""

    def __init__(self, message: str = "", retry_after: float = 60.0):
        super().__init__(message)
        self.retry_after = retry_after


class SourceUnavailable(DataError, RuntimeError):
    """网络错误、超时、SDK 异常：短退避重试，仍失败则换源"""


# ═══════════════════════════════════════════════════════════════════════════════
# DataPort（第一层：根约束）
# ═══════════════════════════════════════════════════════════════════════════════

# 由第二层 XxxPort 填写、第三层 Adapter 不允许覆盖的字段
PORT_META_FIELDS: tuple[str, ...] = (
    "name", "label", "facet", "sub_facet", "description",
    "Params", "Item", "unit", "cache", "sample_params", "sort_order",
)


class DataPort(Generic[P, R], ABC):
    name: ClassVar[str]                     # 全局唯一，如 "moneyflow"
    label: ClassVar[str]
    facet: ClassVar[str]                    # tech / capital / fundamental / news
    sub_facet: ClassVar[str] = ""
    description: ClassVar[str] = ""
    Params: ClassVar[type[BaseModel]]       # 参数模型：校验 + JSON Schema
    Item: ClassVar[type[BaseModel]]         # 返回的 BO 类型
    unit: ClassVar[str] = "none"            # 采集单元维度：symbol / trade_date / index_code / none
    cache: ClassVar[Optional[CachePolicy]] = None   # 声明后即为"实时接口"
    sample_params: ClassVar[dict] = {}      # 采集管理"试查"的默认参数
    sort_order: ClassVar[int] = 100         # 目录排序

    def supports(self, params: P) -> bool:
        """该实现不支持这组参数时返回 False（Gateway 跳过，不算失败）"""
        return True

    @abstractmethod
    async def fetch(self, params: P) -> list[R]: ...


# ═══════════════════════════════════════════════════════════════════════════════
# 命令 / 结果 / 目录
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DataCommand:
    name: str                               # XxxPort.name
    params: dict = field(default_factory=dict)
    source: Optional[str] = None            # 指定 Adapter.tool
    policy: CallPolicy = CallPolicy.COLLECT


@dataclass
class DataResult(Generic[R]):
    items: list[R]
    source: str                             # 实际返回数据的实现；缓存命中时为写缓存时的来源
    latency_ms: int = 0
    cached: bool = False
    fetched_at: Optional[datetime] = None
    attempts: list[tuple[str, str]] = field(default_factory=list)   # 换源前失败的 (source, error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [i.model_dump(mode="json") for i in self.items],
            "source": self.source,
            "cached": self.cached,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "latency_ms": self.latency_ms,
            "attempts": [list(a) for a in self.attempts],
        }


@dataclass(frozen=True)
class AdapterInfo:
    tool: str
    origin: str
    origin_label: str
    priority: int


@dataclass(frozen=True)
class PortInfo:
    name: str
    label: str
    facet: str
    sub_facet: str
    description: str
    unit: str
    realtime: bool
    sort_order: int
    sample_params: dict
    params_schema: dict
    item_schema: dict
    adapters: tuple[AdapterInfo, ...]
    ttl_trading: Optional[int] = None
    consumers: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "facet": self.facet,
            "sub_facet": self.sub_facet,
            "description": self.description,
            "unit": self.unit,
            "realtime": self.realtime,
            "params_schema": self.params_schema,
            "item_schema": self.item_schema,
            "adapters": [a.__dict__ for a in self.adapters],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 统一入口端口
# ═══════════════════════════════════════════════════════════════════════════════


class DataGatewayPort(Protocol):
    async def fetch(
        self, port: type[DataPort[P, R]], params: P | dict, *,
        source: Optional[str] = None, policy: CallPolicy = CallPolicy.COLLECT,
    ) -> DataResult[R]: ...

    async def fetch_many(
        self, port: type[DataPort[P, R]], params_list: list[P | dict], *,
        policy: CallPolicy = CallPolicy.COLLECT,
    ) -> list[DataResult[R] | Exception]: ...

    async def invoke(self, cmd: DataCommand) -> DataResult: ...

    async def invoke_many(self, cmds: list[DataCommand]) -> list[DataResult | Exception]: ...

    def catalog(self) -> list[PortInfo]: ...

    def is_realtime(self, name: str) -> bool: ...

    async def stats(self, name: str, days: int = 1) -> list[dict]: ...


__all__ = [
    "AdapterInfo",
    "CachePolicy",
    "CallPolicy",
    "DataCommand",
    "DataError",
    "DataGatewayPort",
    "DataPort",
    "DataResult",
    "InvalidParams",
    "NotSupported",
    "PORT_META_FIELDS",
    "PortInfo",
    "RateLimited",
    "SourceUnavailable",
]
