"""AkShare 数据解析器

将 AkShare 返回的 DataFrame 转换为 KlineBO 列表。
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd

from domain.kline.schemas import KlineBO


class KlineParser:
    """K 线数据解析器"""

    # AkShare 列名映射
    _COL_MAP = {
        "日期": "trade_date",
        "开盘": "open",
        "最高": "high",
        "最低": "low",
        "收盘": "close",
        "成交量": "volume",
        "成交额": "amount",
        "涨跌幅": "change_pct",
    }

    def parse(self, df: pd.DataFrame, symbol: str) -> list[KlineBO]:
        """解析 DataFrame → KlineBO 列表"""
        if df is None or df.empty:
            return []

        df = df.rename(columns=self._COL_MAP)
        results = []
        for _, row in df.iterrows():
            try:
                kline = self._parse_row(row, symbol)
                results.append(kline)
            except (KeyError, ValueError, TypeError):
                # 单行失败不影响其他行
                continue
        return results

    def _parse_row(self, row: pd.Series, symbol: str) -> KlineBO:
        trade_date = self._parse_date(row["trade_date"])
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])
        close_price = float(row["close"])
        volume = int(row["volume"])
        amount = float(row["amount"])
        change_pct = row.get("change_pct")
        if pd.isna(change_pct) or change_pct == "--":
            change_pct = None
        else:
            change_pct = float(change_pct)

        return KlineBO(
            symbol=symbol,
            name="",
            trade_date=trade_date,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            amount=amount,
            change_pct=change_pct,
        )

    def _parse_date(self, value) -> date:
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        # 兜底使用 pandas
        return pd.to_datetime(value).date()
