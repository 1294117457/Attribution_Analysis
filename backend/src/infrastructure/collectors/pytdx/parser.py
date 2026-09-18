"""pytdx 数据解析器：DataFrame → MinuteKlineBO"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class MinuteKlineBO(BaseModel):
    """分钟 K 线业务对象（采集层直接输出）"""

    symbol: str
    name: str = ""
    dt: datetime
    interval: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float


class PytdxKlineParser:
    """将 pytdx get_security_bars 返回的 DataFrame 转为 MinuteKlineBO 列表"""

    @staticmethod
    def parse(
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        name: str = "",
    ) -> list[MinuteKlineBO]:
        if df is None or df.empty:
            return []

        results: list[MinuteKlineBO] = []
        for _, row in df.iterrows():
            try:
                bo = PytdxKlineParser._parse_row(row, symbol, interval, name)
                if bo:
                    results.append(bo)
            except Exception as e:
                logger.warning("跳过无效分钟K线行: %s", e)

        return results

    @staticmethod
    def _parse_row(
        row: pd.Series,
        symbol: str,
        interval: str,
        name: str,
    ) -> Optional[MinuteKlineBO]:
        dt_str = row.get("datetime")
        if not dt_str:
            return None

        dt = datetime.strptime(str(dt_str), "%Y-%m-%d %H:%M")

        open_val = float(row.get("open", 0))
        high_val = float(row.get("high", 0))
        low_val = float(row.get("low", 0))
        close_val = float(row.get("close", 0))
        volume = int(row.get("vol", 0))
        amount = float(row.get("amount", 0))

        if close_val <= 0:
            return None

        return MinuteKlineBO(
            symbol=symbol,
            name=name,
            dt=dt,
            interval=interval,
            open=open_val,
            high=high_val,
            low=low_val,
            close=close_val,
            volume=volume,
            amount=amount,
        )
