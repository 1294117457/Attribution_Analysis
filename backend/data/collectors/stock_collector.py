"""股票数据采集器"""

from datetime import date, timedelta
from typing import Optional

from data.fetchers import AkShareFetcher
from data.schemas import StockKline


class StockCollector:
    """股票数据采集器"""

    def __init__(self):
        self.fetcher = AkShareFetcher()

    def collect(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[StockKline]:
        """
        采集股票 K 线数据

        Args:
            symbol: 股票代码
            days: 采集天数（如果 start_date 未指定）
            start_date: 开始日期（优先使用）
            end_date: 结束日期（默认为今天）

        Returns:
            list[StockKline]
        """
        if end_date is None:
            end_date = date.today()

        if start_date is None:
            start_date = end_date - timedelta(days=days)

        # 获取 K 线数据
        klines = self.fetcher.get_kline(symbol, start_date, end_date)

        # 获取股票名称并补充
        name = self.fetcher.get_stock_name(symbol)
        for kline in klines:
            kline.name = name

        return klines

    def collect_batch(
        self,
        symbols: list[str],
        days: int = 30,
    ) -> dict[str, list[StockKline]]:
        """
        批量采集股票数据

        Args:
            symbols: 股票代码列表
            days: 采集天数

        Returns:
            dict[symbol, list[StockKline]]
        """
        results = {}
        for symbol in symbols:
            try:
                klines = self.collect(symbol, days=days)
                results[symbol] = klines
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = []
        return results
