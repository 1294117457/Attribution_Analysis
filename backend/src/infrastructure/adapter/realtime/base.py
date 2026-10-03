"""实时接口协议基类与目录元数据字段

实时接口 = 页面当前要看的数据：按需请求数据源，结果只写 Redis，不入库、不建任务记录。
缓存 / 单飞 / 限流 / 降级 / 统计由 infrastructure.adapter.realtime.framework.RealtimeQueryFramework 统一处理，
子类只描述「缓存键、怎么取、失败怎么降级」。

交易时段相关领域规则位于 `domain.service.market_session`（DDD.md §3.2 — 跨聚合根领域服务）。
本模块只负责实时接口基类，不再 re-export 领域符号。

配套设计文档：docs/dev/step2/04采集管理优化/06实时数据接口.md §3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar


class BaseRealtimeQuery(ABC):
    """实时接口基类（与 BaseCollectTask 共用目录元数据字段）

    子类契约：
    - cache_key(params)  —— 计算缓存键（领域行为）
    - fetch(params)       —— 请求数据源，返回可 JSON 序列化的结果（基础设施）
    - normalize(params)   —— 校验 / 规范化参数（领域行为）
    - fallback(params)    —— 数据源失败时的降级结果（领域降级策略，可选）
    """

    name: ClassVar[str] = ""
    facet: ClassVar[str] = ""
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""
    sort_order: ClassVar[int] = 100
    # 同源限流分组：ths / tdx
    source: ClassVar[str] = ""
    source_label: ClassVar[str] = ""
    # 交易时段缓存秒数
    ttl_trading: ClassVar[int] = 15
    # 采集管理页展示：谁在调用本接口
    consumers: ClassVar[tuple[str, ...]] = ()
    # 采集管理「试查」的默认参数
    sample_params: ClassVar[dict] = {}

    def normalize(self, params: dict) -> dict:
        """校验 / 规范化参数；非法时抛 ValueError"""
        return dict(params)

    @abstractmethod
    def cache_key(self, params: dict) -> str: ...

    @abstractmethod
    async def fetch(self, params: dict) -> Any:
        """请求数据源，返回可 JSON 序列化的结果；空数据返回 None，失败抛异常"""

    async def fallback(self, params: dict) -> Any:
        """数据源失败时的降级结果（会标记 stale）；默认无"""
        return None


__all__ = ["BaseRealtimeQuery"]