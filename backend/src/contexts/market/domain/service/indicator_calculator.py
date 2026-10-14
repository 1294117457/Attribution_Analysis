"""技术指标计算器（请求时实时计算，不入库）

支持：
- MA（5/10/20/60）
- EMA（12/26）
- MACD（DIF/DEA/BAR，参数 12/26/9）
- RSI（6/12/24）
- KDJ（K/D/J，参数 9/3/3）
- BOLL（上/中/下轨，参数 20/2）

输入：按日期升序的 K 线序列
输出：与输入等长的指标序列；历史不足的位置为 None（不出假值）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

import pandas as pd

from contexts.market.domain.kline.vo import IndicatorValues

if TYPE_CHECKING:
    from domain.entitys.kline.entity import Kline


INDICATOR_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60",
    "ema12", "ema26",
    "macd_dif", "macd_dea", "macd_bar",
    "rsi6", "rsi12", "rsi24",
    "kdj_k", "kdj_d", "kdj_j",
    "boll_up", "boll_mid", "boll_dn",
]

# 显示窗口之前需要额外读取的 K 线根数。
# EMA/MACD/RSI/KDJ 是递推指标，120 根后初值影响 < 1%（RSI24 最慢），MA60/BOLL20 只需 60 根。
WARMUP_BARS = 120


def _drop_head(series: pd.Series, n: int) -> pd.Series:
    """前 n 个位置置 NaN（递推指标在样本不足时视为无效）"""
    out = series.copy()
    out.iloc[:n] = float("nan")
    return out


class IndicatorCalculator:
    """技术指标计算器

    - 不依赖外部第三方库（不用 pandas_ta，避免额外依赖）
    - 纯函数式（无状态、无 IO）
    """

    # ── MA（简单移动平均）───────────────────────────────

    @staticmethod
    def ma(series: pd.Series, window: int) -> pd.Series:
        return series.rolling(window=window, min_periods=window).mean()

    # ── EMA（指数移动平均）─────────────────────────────

    @staticmethod
    def ema(series: pd.Series, span: int) -> pd.Series:
        return _drop_head(series.ewm(span=span, adjust=False).mean(), span - 1)

    # ── MACD ─────────────────────────────────────────

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """返回 (DIF, DEA, BAR)"""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        bar = (dif - dea) * 2  # 柱状图 = (DIF - DEA) × 2
        dea_head = slow + signal - 2
        return _drop_head(dif, slow - 1), _drop_head(dea, dea_head), _drop_head(bar, dea_head)

    # ── RSI（相对强弱指数，Wilder 平滑）──────────────────

    @staticmethod
    def rsi(close: pd.Series, window: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / window, adjust=False).mean()
        total = avg_gain + avg_loss
        # 只涨不跌 → 100；横盘（涨跌都为 0）→ 50
        rsi = (100 * avg_gain / total.replace(0, float("nan"))).where(total != 0, 50.0)
        return _drop_head(rsi, window)

    # ── KDJ（随机指标）────────────────────────────────

    @staticmethod
    def kdj(high: pd.Series, low: pd.Series, close: pd.Series,
            n: int = 9, m1: int = 3, m2: int = 3):
        """返回 (K, D, J)"""
        low_n = low.rolling(window=n, min_periods=n).min()
        high_n = high.rolling(window=n, min_periods=n).max()
        rsv = (close - low_n) / (high_n - low_n + 1e-9) * 100

        k = rsv.ewm(alpha=1 / m1, adjust=False).mean()
        d = k.ewm(alpha=1 / m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return k, d, j

    # ── BOLL（布林带）───────────────────────────────────

    @staticmethod
    def boll(close: pd.Series, window: int = 20, nb_std: int = 2):
        """返回 (UP, MID, DN)"""
        mid = close.rolling(window=window, min_periods=window).mean()
        std = close.rolling(window=window, min_periods=window).std()
        up = mid + nb_std * std
        dn = mid - nb_std * std
        return up, mid, dn

    # ── 计算所有指标（DataFrame 版）──────────────────────

    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """df 必须包含 'close', 'high', 'low' 列且按日期升序；返回同长度的 18 列指标"""
        if df is None or df.empty:
            return pd.DataFrame(columns=INDICATOR_COLUMNS)

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)

        out = pd.DataFrame(index=df.index)

        out["ma5"]  = self.ma(close, 5)
        out["ma10"] = self.ma(close, 10)
        out["ma20"] = self.ma(close, 20)
        out["ma60"] = self.ma(close, 60)

        out["ema12"] = self.ema(close, 12)
        out["ema26"] = self.ema(close, 26)

        dif, dea, bar = self.macd(close)
        out["macd_dif"] = dif
        out["macd_dea"] = dea
        out["macd_bar"] = bar

        out["rsi6"]  = self.rsi(close, 6)
        out["rsi12"] = self.rsi(close, 12)
        out["rsi24"] = self.rsi(close, 24)

        k, d, j = self.kdj(high, low, close)
        out["kdj_k"] = k
        out["kdj_d"] = d
        out["kdj_j"] = j

        up, mid, dn = self.boll(close)
        out["boll_up"]  = up
        out["boll_mid"] = mid
        out["boll_dn"]  = dn

        return out[INDICATOR_COLUMNS]

    # ── 主入口：K 线序列 → 指标序列 ─────────────────────

    def calculate(self, klines: Sequence[Kline]) -> list[IndicatorValues]:
        """klines 必须按日期升序；返回与 klines 一一对应的指标"""
        if not klines:
            return []
        df = pd.DataFrame(
            [{"close": k.close, "high": k.high, "low": k.low} for k in klines]
        )
        records = self.calculate_all(df).to_dict("records")
        return [
            IndicatorValues(**{
                col: (None if pd.isna(v) else float(v)) for col, v in row.items()
            })
            for row in records
        ]
