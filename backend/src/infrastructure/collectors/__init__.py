"""采集器模块（ACL 防腐层）

主要导出：
- CollectParams        — 通用采集参数
- FetcherProtocol      — 过渡态超级协议（deprecated，推荐用小协议）
- KlineFetcher         — 日K线采集协议
- MinuteKlineFetcher   — 分钟K线采集协议
- StockBasicFetcher    — 股票基本信息采集协议
- DailyBasicFetcher    — 日频估值采集协议
- ConceptFetcher       — 概念板块采集协议（AKShare 实现）
- get_registry         — 获取全局注册中心
- setup_default_registry — 启动时注册默认数据源

路由层使用示例：
    from infrastructure.collectors import KlineFetcher, get_registry
    fetcher: KlineFetcher = get_registry().get(KlineFetcher)

Service 层使用示例：
    from infrastructure.collectors import KlineFetcher
    async def collect(self, fetcher: KlineFetcher):
        ...
"""

from infrastructure.collectors.interfaces import CollectParams, FetcherProtocol
from infrastructure.collectors.protocols import (
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
    DailyBasicFetcher,
    ConceptFetcher,
)
from infrastructure.collectors.registry import (
    get_registry,
    setup_default_registry,
)

__all__ = [
    "CollectParams",
    "FetcherProtocol",
    "KlineFetcher",
    "MinuteKlineFetcher",
    "StockBasicFetcher",
    "DailyBasicFetcher",
    "ConceptFetcher",
    "get_registry",
    "setup_default_registry",
]
