"""Fetcher 抽象基类（step7 重构）

替代旧 XxxTushareAdapter(XxxPort, AdapterBase, TushareAdapterBase) 多重继承：
- 只继承 BaseFetcher
- 不再有 XxxPort 抽象、AdapterBase 抽象
- fetch(**params) -> list[BaseModel]，直接接受 kwargs
- 唯一职责：调 SDK 拿数据

fetcher 不知道：限流、并发、缓存、入库、重试

参考文档：docs/backend-docs/dev/step7/01采集重构/01-精简方案总览.md §5
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel


class BaseFetcher(ABC):
    """Fetcher 抽象基类

    命名：业务名 + 数据源 + Fetcher
    例：DailyTushareFetcher / ConceptListAdataFetcher / MinutePytdxFetcher
        （业务概念在目录下唯一时可剥，如 Daily / Minute 已隐含 K 线）

    唯一职责：调 SDK 拿数据，返回 list[BO]
    不限流、不并发、不缓存、不入库——这些在 service 里做
    """
    # 数据源标识：'tushare' / 'adata' / 'pytdx' / 'eastmoney' / ...
    source: ClassVar[str] = ""
    # 业务类型标识：'daily_kline' / 'stock_basic' / ...
    fetcher_type: ClassVar[str] = ""
    # 元数据（可选，用于 admin 展示）
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    async def fetch(self, **params) -> list[BaseModel]:
        """调 SDK 拿数据，返回 list[BO]（Pydantic BaseModel 子类）

        入参直接 kwargs，service 负责类型校验和默认值填充。
        """
        ...


__all__ = ["BaseFetcher"]
