"""数据采集服务"""

from datetime import date, timedelta
from typing import Optional

from data.akshare_client import AkShareClient
from data.schemas import StockKline


class DataService:
    """数据服务"""

    def __init__(self):
        self.client = AkShareClient()

    def collect_stock(
        self,
        symbol: str,
        days: int = 365,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[StockKline]:
        """
        采集股票数据

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

        # 获取股票名称
        name = self.client.get_stock_name(symbol)

        # 获取 K 线数据
        klines = self.client.get_stock_kline(symbol, start_date, end_date)

        # 补充股票名称
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
                klines = self.collect_stock(symbol, days)
                results[symbol] = klines
            except Exception as e:
                print(f"采集 {symbol} 失败: {e}")
                results[symbol] = []

        return results
