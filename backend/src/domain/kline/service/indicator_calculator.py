"""技术指标计算器

支持：
- MA（5/10/20/60）
- EMA（12/26）
- MACD（DIF/DEA/BAR，参数 12/26/9）
- RSI（6/12/24）
- KDJ（K/D/J，参数 9/3/3）
- BOLL（上/中/下轨，参数 20/2）

输入：包含 close / high / low 系列的 K 线 DataFrame（按日期升序）
输出：与输入等长的 DataFrame，新增 17 个指标列
"""

from __future__ import annotations

import pandas as pd


# 输出指标列名（与 daily_klines 表字段一一对应）
INDICATOR_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60",
    "ema12", "ema26",
    "macd_dif", "macd_dea", "macd_bar",
    "rsi6", "rsi12", "rsi24",
    "kdj_k", "kdj_d", "kdj_j",
    "boll_up", "boll_mid", "boll_dn",
]


class IndicatorCalculator:
    """技术指标计算器

    - 不依赖外部第三方库（不用 pandas_ta，避免额外依赖）
    - 输入 / 输出均为 DataFrame，便于与 Pandas/NumPy 生态集成
    - 单元测试友好：纯函数式（无状态）
    """

    # ── MA（简单移动平均）───────────────────────────────

    @staticmethod
    def ma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window, min_periods=1).mean()

    # ── EMA（指数移动平均）─────────────────────────────

    @staticmethod
    def ema(series: pd.Series, span: int) -> pd.Series:
        return series.ewm(span=span, adjust=False, min_periods=1).mean()

    # ── MACD ─────────────────────────────────────────

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """返回 (DIF, DEA, BAR)"""
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=1).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=1).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False, min_periods=1).mean()
        bar = (dif - dea) * 2  # 柱状图 = (DIF - DEA) × 2
        return dif, dea, bar

    # ── RSI（相对强弱指数）────────────────────────────

    @staticmethod
    def rsi(close: pd.Series, window: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=1).mean()
        avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=1).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi = 100 - (100 / (rs + 1))
        return rsi.fillna(50)  # 无数据时取中性 50

    # ── KDJ（随机指标）────────────────────────────────

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3):
        """返回 (K, D, J)"""
        low_n = low.rolling(window=n, min_periods=1).min()
        high_n = high.rolling(window=n, min_periods=1).max()
        rsv = (close - low_n) / (high_n - low_n + 1e-9) * 100

        k = rsv.ewm(alpha=1 / m1, adjust=False, min_periods=1).mean()
        d = k.ewm(alpha=1 / m2, adjust=False, min_periods=1).mean()
        j = 3 * k - 2 * d
        return k, d, j

    # ── BOLL（布林带）───────────────────────────────────

    @staticmethod
    def boll(close: pd.Series, window: int = 20, nb_std: int = 2):
        """返回 (UP, MID, DN)"""
        mid = close.rolling(window=window, min_periods=1).mean()
        std = close.rolling(window=window, min_periods=1).std()
        up = mid + nb_std * std
        dn = mid - nb_std * std
        return up, mid, dn

    # ── 主入口：计算所有指标 ──────────────────────────────

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """计算所有指标并返回新增列的 DataFrame

        Args:
            df: 必须包含 'close', 'high', 'low' 列，按日期升序

        Returns:
            与 df 同长度的 DataFrame，新增 17 个指标列
        """
        if df is None or df.empty:
            return pd.DataFrame(columns=INDICATOR_COLUMNS)

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        out = pd.DataFrame(index=df.index)

        # 均线
        out["ma5"]  = self.ma(close, 5)
        out["ma10"] = self.ma(close, 10)
        out["ma20"] = self.ma(close, 20)
        out["ma60"] = self.ma(close, 60)

        # EMA
        out["ema12"] = self.ema(close, 12)
        out["ema26"] = self.ema(close, 26)

        # MACD
        dif, dea, bar = self.macd(close)
        out["macd_dif"] = dif
        out["macd_dea"] = dea
        out["macd_bar"] = bar

        # RSI
        out["rsi6"]  = self.rsi(close, 6)
        out["rsi12"] = self.rsi(close, 12)
        out["rsi24"] = self.rsi(close, 24)

        # KDJ
        k, d, j = self.kdj(high, low, close)
        out["kdj_k"] = k
        out["kdj_d"] = d
        out["kdj_j"] = j

        # BOLL
        up, mid, dn = self.boll(close)
        out["boll_up"]  = up
        out["boll_mid"] = mid
        out["boll_dn"]  = dn

        return out

    # ── 给定 Kline 列表，返回每个 Kline 对应的指标字典 ────────

    def enrich_klines(self, klines: list, df: pd.DataFrame | None = None) -> dict[date, dict]:
        """计算 DataFrame 上所有指标，返回 {date -> {指标列: 值}}

        Args:
            klines: 领域 Kline 对象列表（必须按日期升序）
            df: 可选，已构建好的 DataFrame；不传则按 klines 构建

        Returns:
            {date(对象): {指标名: 值}, ...}
        """
        if not klines:
            return {}

        if df is None:
            df = pd.DataFrame([{
                "date": k.trade_date.date,
                "close": k.close,
                "high":  k.high,
                "low":   k.low,
            } for k in klines])

        df = df.sort_values("date").reset_index(drop=True)
        indicators = self.calculate_all(df)

        # 把 date 列加回去，便于索引
        if "date" not in indicators.columns:
            indicators["date"] = df["date"].values

        result: dict[date, dict] = {}
        for _, row in indicators.iterrows():
            d = row["date"]
            if isinstance(d, pd.Timestamp):
                d = d.date()
            result[d] = {col: (None if pd.isna(row[col]) else float(row[col]))
                         for col in INDICATOR_COLUMNS}
        return result