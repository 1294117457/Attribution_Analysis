"""Tushare 解析工具：代码转换 / 日期解析 / 利润表去重 / 日 K 解析"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

import pandas as pd

from collectors.schemas import KlineBO


def symbol_to_ts_code(symbol: str) -> str:
    """把 6 位股票代码转换为 Tushare ts_code。"""
    if not symbol or len(symbol) != 6 or not symbol.isdigit():
        raise ValueError(f"无效的股票代码: {symbol!r}，应为 6 位数字")

    prefix2 = symbol[:2]
    prefix3 = symbol[:3]

    # 北交所：老代码 83/87/43/82，2024 年起新代码段 920xxx
    if prefix2 in ("83", "87", "43", "82", "92"):
        return f"{symbol}.BJ"

    if prefix3 in ("600", "601", "603", "605", "688", "689"):
        return f"{symbol}.SH"

    return f"{symbol}.SZ"


def ymd(d: Optional[date]) -> Optional[str]:
    return d.strftime("%Y%m%d") if d else None


def parse_list_date(s) -> Optional[date]:
    """YYYYMMDD 字符串 → date"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return None
    s = str(s).strip()
    if not s or s == "0" or s == "00000000":
        return None
    try:
        return pd.to_datetime(s, format="%Y%m%d").date()
    except Exception:
        try:
            return pd.to_datetime(s).date()
        except Exception:
            return None


def rows(df: Optional[pd.DataFrame]) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict("records")


def num(row: dict, key: str) -> Optional[float]:
    v = row.get(key)
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def int_(row: dict, key: str) -> Optional[int]:
    """取整数字段；缺失/NaN 返回 None（不是 0 —— 0 在「排名/计数」语义下会误导）"""
    v = row.get(key)
    if v is None or pd.isna(v):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def text(row: dict, key: str) -> Optional[str]:
    v = row.get(key)
    if v is None or pd.isna(v):
        return None
    return str(v)


def symbol_of(row: dict) -> Optional[str]:
    ts_code = row.get("ts_code")
    if not ts_code or pd.isna(ts_code):
        return None
    return str(ts_code).split(".")[0]


# ── 利润表 ─────────────────────────────────────────────────────────

INCOME_VALUE_FIELDS = (
    "basic_eps", "diluted_eps", "total_revenue", "revenue",
    "operate_profit", "total_profit", "n_income", "n_income_attr_p",
)
INCOME_FIELDS = ",".join((
    "ts_code", "ann_date", "f_ann_date", "end_date", "report_type", "comp_type",
    *INCOME_VALUE_FIELDS, "update_flag",
))
_INCOME_KEY = ["ts_code", "end_date", "report_type"]


def dedupe_income(df: pd.DataFrame) -> pd.DataFrame:
    """同一报告期 Tushare 会返回更正前后多行：优先 update_flag=1，其次实际公告日、公告日最新"""
    if df.empty:
        return df
    ordered = df.assign(
        _flag=df["update_flag"].fillna("0").astype(str),
        _f_ann=df["f_ann_date"].fillna("").astype(str),
        _ann=df["ann_date"].fillna("").astype(str),
    ).sort_values(["_flag", "_f_ann", "_ann"], ascending=False)
    return (
        ordered.drop_duplicates(subset=_INCOME_KEY, keep="first")
        .drop(columns=["_flag", "_f_ann", "_ann"])
        .sort_values("end_date", ascending=False)
    )


# ── 日 K ───────────────────────────────────────────────────────────


class TushareKlineParser:
    """`pro.daily()` DataFrame → KlineBO

    - trade_date: YYYYMMDD
    - vol:        成交量（手）
    - amount:     成交额（千元），×1000 转为元
    - pct_chg:    涨跌幅（%）
    """

    def parse(self, df: pd.DataFrame, symbol: str) -> list[KlineBO]:
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

    def parse_many(self, df: pd.DataFrame) -> list[KlineBO]:
        """`pro.daily(trade_date=...)` 返回**全市场**当日数据 → 一行一个 symbol。

        ★ 这是「按日期整批采集」路径：一次接口调用拿到 5000+ 只股票的当日 K 线，
          而「按 symbol 逐只采集」需要 5000+ 次调用 —— 差 3 个数量级。

        symbol 取自行内 `ts_code`（去掉后缀）。
        """
        if df is None or df.empty:
            return []
        results: list[KlineBO] = []
        for _, row in df.iterrows():
            ts_code = row.get("ts_code")
            if not ts_code or pd.isna(ts_code):
                continue
            symbol = str(ts_code).split(".")[0]
            try:
                kline = self._parse_row(row, symbol)
                if kline is not None:
                    results.append(kline)
            except (KeyError, ValueError, TypeError):
                continue
        return results

    def _parse_row(self, row: Any, symbol: str) -> Optional[KlineBO]:
        trade_date = self._parse_date(row["trade_date"])
        if trade_date is None:
            return None

        amount_kilo = row.get("amount")
        amount_yuan = float(amount_kilo) * 1000.0 if pd.notna(amount_kilo) else 0.0

        volume_raw = row.get("vol")
        volume = int(volume_raw) if pd.notna(volume_raw) else 0

        pct_chg = row.get("pct_chg")
        change_pct: Optional[float] = float(pct_chg) if pd.notna(pct_chg) else None

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


__all__ = [
    "INCOME_FIELDS",
    "INCOME_VALUE_FIELDS",
    "TushareKlineParser",
    "dedupe_income",
    "int_",
    "num",
    "parse_list_date",
    "rows",
    "symbol_of",
    "symbol_to_ts_code",
    "text",
    "ymd",
]
