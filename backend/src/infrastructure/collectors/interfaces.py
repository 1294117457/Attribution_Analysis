"""采集器接口定义

ACL（Anti-Corruption Layer）防腐层对外的统一接口。
所有数据源适配器必须实现 FetcherProtocol。

⚠️ 重构说明（2026-09-24）：
- FetcherProtocol 已从「联合超级协议」降级为「过渡态抽象基类」
- 推荐使用 protocols.py 中的小协议：KlineFetcher / MinuteKlineFetcher / StockBasicFetcher / DailyBasicFetcher / ConceptFetcher
- 不再使用「KlineFetcher + StockBasicFetcher + DailyBasicFetcher 联合继承」——
  那样会使只实现了部分能力的 PytdxFetcher 通过 isinstance，但实际调用会失败，
  造成类型系统与运行时行为不一致
- 过渡态 FetcherProtocol 只作为向后兼容的类型注解使用，完成迁移后将被删除
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from datetime import date
from typing import Any, Optional


@dataclass
class CollectParams:
    """通用采集参数"""

    symbol: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 30
    adjust: str = "qfq"
    list_status: str = "L"  # 上市状态（L/D/P）


class FetcherProtocol:
    """⚠️ 已废弃：请使用拆分后的各小协议

    本类不再继承 Protocol，直接重写方法签名（默认抛 NotImplementedError）。
    新代码应直接依赖 protocols.py 中的小协议（KlineFetcher 等）。

    使用示例：
        # 旧代码（仍兼容）
        async def collect(self, fetcher: FetcherProtocol):
            data = fetcher.fetch(params)

        # 新代码（推荐）
        from infrastructure.collectors.protocols import KlineFetcher
        async def collect(self, fetcher: KlineFetcher):
            data = fetcher.fetch(params)
    """

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        warnings.warn(
            f"{cls.__name__} 继承了废弃的 FetcherProtocol，"
            "请改用 KlineFetcher / MinuteKlineFetcher / StockBasicFetcher 等小协议",
            DeprecationWarning,
            stacklevel=2,
        )

    def fetch(self, params: CollectParams) -> list[Any]:
        raise NotImplementedError(
            "FetcherProtocol 已废弃，请改用 KlineFetcher.fetch()"
        )

    def fetch_stock_basic(self, params: CollectParams) -> list[Any]:
        raise NotImplementedError(
            "FetcherProtocol 已废弃，请改用 StockBasicFetcher.fetch_stock_basic()"
        )

    def fetch_daily_basic(self, trade_date: str) -> list[Any]:
        raise NotImplementedError(
            "FetcherProtocol 已废弃，请改用 DailyBasicFetcher.fetch_daily_basic()"
        )

    @property
    def source_name(self) -> str:
        raise NotImplementedError(
            "FetcherProtocol 已废弃，请改用对应小协议的 source_name 属性"
        )


__all__ = ["CollectParams", "FetcherProtocol"]
