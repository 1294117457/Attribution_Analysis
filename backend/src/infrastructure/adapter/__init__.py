"""采集器模块（ACL 防腐层）

主要导出：
- CollectParams        — 通用采集参数
- KlineFetcher         — 日K线采集协议
- MinuteKlineFetcher   — 分钟K线采集协议
- StockBasicFetcher    — 股票基本信息采集协议
- DailyBasicFetcher    — 日频估值采集协议
- ConceptFetcher       — 概念板块采集协议（Adata · 同花顺实现）
- get_registry         — 获取全局注册中心

注：setup_default_registry 已迁移到 `infrastructure.config.di`，
避免本包对 application.port.registry 产生循环依赖。

路由层使用示例：
    from infrastructure.adapter import KlineFetcher, get_registry
    fetcher: KlineFetcher = get_registry().get(KlineFetcher)

Service 层使用示例：
    from infrastructure.adapter import KlineFetcher
    async def collect(self, fetcher: KlineFetcher):
        ...
"""

from application.port.collector_port import (
    CollectParams,
    ConceptFetcher,
    DailyBasicFetcher,
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
)
from application.port.registry import get_registry

__all__ = [
    "CollectParams",
    "KlineFetcher",
    "MinuteKlineFetcher",
    "StockBasicFetcher",
    "DailyBasicFetcher",
    "ConceptFetcher",
    "get_registry",
]
