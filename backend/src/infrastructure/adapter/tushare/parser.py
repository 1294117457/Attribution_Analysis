"""Tushare K 线解析器

将 tushare `pro.daily()` 返回的 DataFrame 转换为 KlineBO 列表。

Tushare 字段说明:
- trade_date: YYYYMMDD 字符串
- vol:        成交量（手）
- amount:     成交额（千元），需 *1000 转换为元
- pct_chg:    涨跌幅（%），保留 2 位小数
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

import pandas as pd

from domain.kline.schemas import KlineBO


class TushareKlineParser:
    """Tushare K 线数据解析器"""

    def parse(self, df: pd.DataFrame, symbol: str) -> list[KlineBO]:
        """解析 Tushare DataFrame → KlineBO 列表"""
        if df is None or df.empty:
            return []

        results = []
        for _, row in df.iterrows():
            try:
                kline = self._parse_row(row, symbol)
                if kline is not None:
                    results.append(kline)
            except (KeyError, ValueError, TypeError):
                continue
        return results

    def _parse_row(self, row: pd.Series, symbol: str) -> Optional[KlineBO]:
        trade_date = self._parse_date(row["trade_date"])
        if trade_date is None:
            return None

        # Tushare 的 amount 单位是「千元」→ 转为「元」
        amount_kilo = row.get("amount")
        amount_yuan = float(amount_kilo) * 1000.0 if pd.notna(amount_kilo) else 0.0

        volume_raw = row.get("vol")
        volume = int(volume_raw) if pd.notna(volume_raw) else 0

        pct_chg = row.get("pct_chg")
        change_pct: Optional[float] = (
            float(pct_chg) if pd.notna(pct_chg) else None
        )

        return KlineBO(
            symbol=symbol,
            name="",
            trade_date=trade_date,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=volume,
            amount=amount_yuan,
            change_pct=change_pct,
        )

    @staticmethod
    def _parse_date(value) -> Optional[date]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        s = str(value).strip()
        for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None
