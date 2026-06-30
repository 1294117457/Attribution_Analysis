"""AkShare 数据获取客户端"""

import akshare as ak
import pandas as pd
from datetime import date, timedelta
from typing import Optional

from data.schemas import StockKline


class AkShareClient:
    """AkShare 数据客户端"""

    def __init__(self):
        self.session = None  # 可复用 session

    def get_stock_kline(
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
        # 格式化日期
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        try:
            # 调用 AkShare 获取数据
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                start_date=start_str,
                end_date=end_str,
                adjust=adjust,
            )

            # 转换 DataFrame 为 list[StockKline]
            return self._parse_dataframe(df, symbol)

        except Exception as e:
            raise RuntimeError(f"获取股票 {symbol} 数据失败: {e}")

    def get_stock_name(self, symbol: str) -> str:
        """
        获取股票名称

        Args:
            symbol: 股票代码

        Returns:
            股票名称
        """
        try:
            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return row.iloc[0]["名称"]
        except Exception:
            pass

        return ""

    def get_stock_info(self, symbol: str) -> Optional[dict]:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            dict 或 None
        """
        try:
            df = ak.stock_individual_info_em(symbol=symbol)
            info = dict(zip(df["Item"], df["Content"]))
            return info
        except Exception:
            return None

    def get_stock_list(self, market: str = "A股") -> pd.DataFrame:
        """
        获取股票列表

        Args:
            market: 市场类型，默认 "A股"

        Returns:
            DataFrame
        """
        try:
            df = ak.stock_zh_a_spot_em()
            return df
        except Exception as e:
            raise RuntimeError(f"获取股票列表失败: {e}")

    def _parse_dataframe(self, df: pd.DataFrame, symbol: str) -> list[StockKline]:
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
                # 获取日期
                raw_date = row["日期"]
                if isinstance(raw_date, str):
                    kline_date = date.fromisoformat(raw_date)
                else:
                    kline_date = pd.to_datetime(raw_date).date()

                # 获取涨跌幅
                change_pct = row.get("涨跌幅")
                if change_pct == "--":
                    change_pct = None

                kline = StockKline(
                    symbol=symbol,
                    name="",  # 名称单独获取
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

            except Exception as e:
                # 跳过解析失败的行
                continue

        return klines
