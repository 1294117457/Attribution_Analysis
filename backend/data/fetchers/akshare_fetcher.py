"""AkShare 数据获取"""

import akshare as ak
import pandas as pd
from datetime import date
from typing import Optional

from data.schemas import StockKline, StockInfo
from data.parsers.kline_parser import KlineParser


class AkShareFetcher:
    """AkShare 数据获取器"""

    def __init__(self):
        self.parser = KlineParser()

    def get_kline(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        adjust: str = "qfq",
    ) -> list[StockKline]:
        """
        获取股票 K 线数据

        Args:
            symbol: 股票代码，如 "000001"
            start_date: 开始日期
            end_date: 结束日期
            adjust: 复权类型，"qfq" 前复权，"hfq" 后复权，"" 不复权

        Returns:
            list[StockKline]
        """
        try:
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=adjust,
            )
            return self.parser.parse_kline_df(df, symbol)
        except Exception as e:
            raise RuntimeError(f"获取股票 {symbol} K 线失败: {e}")

    def get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            StockInfo 或 None
        """
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            info = dict(zip(df["Item"], df["Content"]))

            return StockInfo(
                symbol=symbol,
                name=info.get("股票简称", ""),
                industry=info.get("行业", None),
                market=info.get("上市时间", None),
            )
        except Exception:
            return None

    def get_stock_name(self, symbol: str) -> str:
        """
        获取股票名称

        Args:
            symbol: 股票代码

        Returns:
            股票名称
        """
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return row.iloc[0]["名称"]
        except Exception:
            pass
        return ""

    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型，默认 "A股"

        Returns:
            DataFrame
        """
        try:
            return ak.stock_zh_a_spot_em()
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}")
