"""通用数据采集器"""

from data.interfaces.fetcher import FetcherProtocol, CollectParams
from data.schemas.base import BaseData


class Collector:
    """通用采集器，只依赖 FetcherProtocol，不感知具体数据源或数据类型

    组合方式（在 Service 层装配）：
        collector = Collector(AkShareFetcher(DailyKline))
        collector = Collector(TushareFetcher(DailyKline))
    """

    def __init__(self, fetcher: FetcherProtocol):
        self.fetcher = fetcher

    def collect(self, params: CollectParams) -> list[BaseData]:
        """执行采集"""
        return self.fetcher.fetch(params)
