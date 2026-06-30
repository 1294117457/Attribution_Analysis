"""K 线数据解析"""

import pandas as pd
from datetime import date
from data.schemas import StockKline


class KlineParser:
    """K 线数据解析器"""

    def parse_kline_df(self, df: pd.DataFrame, symbol: str) -> list[StockKline]:
        """
        解析 DataFrame 为 StockKline 列表

        Args:
            df: AkShare 返回的 DataFrame
            symbol: 股票代码

        Returns:
            list[StockKline]
        """
        klines = []

        for _, row in df.iterrows():
            try:
                raw_date = row["日期"]
                if isinstance(raw_date, str):
                    kline_date = date.fromisoformat(raw_date)
                else:
                    kline_date = pd.to_datetime(raw_date).date()

                change_pct = row.get("涨跌幅")
                if change_pct == "--":
                    change_pct = None

                kline = StockKline(
                    symbol=symbol,
                    name="",
                    date=kline_date,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=int(row["成交量"]),
                    amount=float(row["成交额"]),
                    change_pct=float(change_pct) if change_pct else None,
                )
                klines.append(kline)

            except Exception:
                continue

        return klines
