"""
AkShare 数据采集客户端。
封装所有数据获取逻辑，供 scripts/collect_data.py 调用。
"""

from typing import Optional
import time

import akshare as ak
import pandas as pd


class AkShareClient:
    """AkShare 数据采集客户端"""

    def __init__(self, request_delay: float = 1.0):
        """
        Args:
            request_delay: 请求间隔（秒），避免请求过快被封
        """
        self.request_delay = request_delay

    def fetch_klines(self, code: str, start_date: str = "20200101", end_date: str = "20500101", adjust: str = "qfq") -> list[dict]:
        """
        获取 A 股日 K 线数据（前复权）。

        Args:
            code: 股票代码，如 "600519"
            start_date: 开始日期，格式 YYYYMMDD，如 "20200101"
            end_date: 结束日期，格式 YYYYMMDD
            adjust: 复权类型，"qfq"=前复权，"hfq"=后复权，""=不复权

        Returns:
            list[dict]: K 线数据列表，每条包含标准字段
        """
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust=adjust)

        if df is None or df.empty:
            return []

        result = []
        for _, row in df.iterrows():
            trade_date = row["日期"]
            # 转换日期格式：2024/01/01 → 2024-01-01
            if isinstance(trade_date, str):
                date_str = trade_date.replace("/", "-")
            else:
                date_str = str(trade_date)[:10]

            result.append({
                "code": code,
                "date": date_str,
                "open": float(row["开盘"]),
                "high": float(row["最高"]),
                "low": float(row["最低"]),
                "close": float(row["收盘"]),
                "volume": float(row["成交量"]),
                "amount": float(row["成交额"]),
                "change_pct": float(row["涨跌幅"]) if pd.notna(row["涨跌幅"]) else None,
                "turnover_rate": float(row["换手率"]) if "换手率" in row and pd.notna(row["换手率"]) else None,
            })

        time.sleep(self.request_delay)
        return result

    def fetch_batch(self, stocks: list[tuple[str, str]], start_date: str = "20200101", end_date: str = "20500101") -> dict[str, list[dict]]:
        """
        批量采集多只股票数据。

        Args:
            stocks: 股票列表，格式 [(代码, 名称), ...]
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: {代码: K线数据列表}
        """
        results = {}
        for code, name in stocks:
            klines = self.fetch_klines(code, start_date, end_date)
            # 注入股票名称
            for kline in klines:
                kline["name"] = name
            results[code] = klines
        return results

    def fetch_stock_info(self, code: str) -> Optional[dict]:
        """
        获取股票基本信息（名称、上市日期等）。

        Args:
            code: 股票代码

        Returns:
            dict 或 None
        """
        try:
            df = ak.stock_individual_info_em(symbol=code)
            if df is None or df.empty:
                return None

            info = {}
            for _, row in df.iterrows():
                info[row["item"]] = row["value"]

            time.sleep(self.request_delay)
            return info
        except Exception:
            return None


# 全局单例
_client: Optional[AkShareClient] = None


def get_client(request_delay: float = 1.0) -> AkShareClient:
    """获取 AkShare 客户端单例"""
    global _client
    if _client is None:
        _client = AkShareClient(request_delay)
    return _client


def fetch_klines(code: str, start_date: str = "20200101", end_date: str = "20500101") -> list[dict]:
    """便捷函数：获取单只股票 K 线"""
    return get_client().fetch_klines(code, start_date, end_date)
