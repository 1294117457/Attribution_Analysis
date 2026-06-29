"""
AkShare 数据采集客户端。
封装 AkShare 接口调用。
"""

from typing import Optional
import time

import akshare as ak
import pandas as pd

from app.modules.collector.schemas import KLineRecord, StockInfo
from app.modules.config import CollectorConfig


class AkShareClient:
    """AkShare 数据采集客户端"""

    def __init__(self, config: Optional[CollectorConfig] = None):
        self.config = config or CollectorConfig()

    def fetch_klines(
        self,
        code: str,
        start_date: str = "20200101",
        end_date: str = "20500101",
        adjust: str = "qfq",
    ) -> list[KLineRecord]:
        """
        获取 A 股日 K 线数据（前复权）。

        Args:
            code: 股票代码，如 "600519"
            start_date: 开始日期，格式 YYYYMMDD
            end_date: 结束日期，格式 YYYYMMDD
            adjust: 复权类型，"qfq"=前复权，"hfq"=后复权，""=不复权

        Returns:
            list[KLineRecord]: K 线数据列表
        """
        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )

            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                trade_date = row["日期"]
                if isinstance(trade_date, str):
                    date_str = trade_date.replace("/", "-")
                else:
                    date_str = str(trade_date)[:10]

                result.append(KLineRecord(
                    code=code,
                    name="",
                    date=date_str,
                    open=float(row["开盘"]),
                    high=float(row["最高"]),
                    low=float(row["最低"]),
                    close=float(row["收盘"]),
                    volume=float(row["成交量"]),
                    amount=float(row["成交额"]),
                    change_pct=float(row["涨跌幅"]) if pd.notna(row.get("涨跌幅")) else None,
                    turnover_rate=float(row["换手率"]) if "换手率" in row and pd.notna(row.get("换手率")) else None,
                ))

            time.sleep(self.config.request_delay)
            return result

        except Exception as e:
            raise RuntimeError(f"获取K线失败 {code}: {e}")

    def fetch_stock_info(self, code: str) -> Optional[StockInfo]:
        """
        获取股票基本信息。

        Args:
            code: 股票代码

        Returns:
            StockInfo 或 None
        """
        try:
            df = ak.stock_individual_info_em(symbol=code)
            if df is None or df.empty:
                return None

            info = {}
            for _, row in df.iterrows():
                info[row["item"]] = row["value"]

            time.sleep(self.config.request_delay)

            return StockInfo(
                code=code,
                name=info.get("股票简称", ""),
                industry=info.get("行业", None),
                market=info.get("市场", None),
                list_date=info.get("上市时间", None),
            )

        except Exception:
            return None

    def get_index_components(self, index_code: str) -> list[tuple[str, str]]:
        """
        获取指数成分股列表。

        Args:
            index_code: 指数代码
                - "000300": 沪深300
                - "000905": 中证500

        Returns:
            list[tuple[code, name]]: [(代码, 名称), ...]
        """
        try:
            df = ak.index_zh_index_stock_cons(symbol=index_code)
            if df is None or df.empty:
                return []

            result = []
            for _, row in df.iterrows():
                result.append((str(row["品种代码"]), str(row["品种名称"])))

            time.sleep(self.config.request_delay)
            return result

        except Exception:
            return []

    def get_index_list(self) -> list[dict]:
        """获取主要指数列表"""
        try:
            df = ak.stock_zh_index_spot_em()
            if df is None or df.empty:
                return []

            # 筛选主要指数
            major_indices = ["沪深300", "中证500", "中证1000", "创业板指", "科创50"]
            result = []

            for _, row in df.iterrows():
                name = str(row.get("名称", ""))
                if name in major_indices:
                    result.append({
                        "code": str(row.get("代码", "")),
                        "name": name,
                    })

            return result

        except Exception:
            return []
