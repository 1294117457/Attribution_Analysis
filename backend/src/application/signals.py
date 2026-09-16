"""技术形态信号检测器

输入：含有指标字段的 Kline 列表（按日期升序）
输出：TechnicalSummary（含金叉/死叉/超买/突破等形态判断）

这个模块把"金叉/死叉/超买/突破"这种形态判断集中在后端做,
AI 拿到的是已经提炼过的信号 + 原始数据, 不用自己再算一遍。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class TechnicalSummary:
    """技术形态摘要 - 喂给 AI / 前端信号面板"""

    # 价格
    latest_close: float
    pct_change_1d: float          # 当日涨幅 %
    pct_change_30d: float         # 近 30 日涨幅 %

    # 均线
    ma_alignment: str             # "bullish" | "bearish" | "neutral"
    ma5: Optional[float]
    ma10: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    ma5_above_ma20: bool
    golden_cross_recent: bool     # 近 5 日内 MA5 上穿 MA20

    # MACD
    macd_status: str              # "golden_cross" | "death_cross" | "above_zero" | "below_zero" | "neutral"
    macd_dif: float
    macd_dea: float
    macd_bar: float

    # RSI
    rsi6: float
    rsi_status: str               # "overbought" | "oversold" | "neutral"

    # KDJ
    kdj_k: float
    kdj_d: float
    kdj_j: float
    kdj_status: str               # "golden_cross" | "death_cross" | "overbought" | "oversold" | "neutral"

    # BOLL
    boll_up: Optional[float]
    boll_mid: Optional[float]
    boll_dn: Optional[float]
    boll_position: str            # "above_upper" | "below_lower" | "upper_half" | "lower_half" | "middle"

    # 综合信号标签
    signals: list[str]


class SignalDetector:
    """技术形态摘要生成器

    - 输入：按日期升序的 Kline 列表（必须含指标字段）
    - 输出：基于最近一日 + 前 5 日判断形态
    """

    def summarize(self, klines) -> TechnicalSummary:
        """基于 K 线列表（含指标字段）生成技术形态摘要"""
        if not klines:
            raise ValueError("K 线列表为空，无法生成摘要")

        latest = klines[-1]
        prev = klines[-2] if len(klines) > 1 else None
        prev5 = klines[-6] if len(klines) >= 6 else None

        signals: list[str] = []

        # ── 均线 ────────────────────────────────────────
        ma_align = "neutral"
        if all([latest.ma5, latest.ma10, latest.ma20]):
            if latest.ma5 > latest.ma10 > latest.ma20:
                ma_align = "bullish"
                signals.append("MA 多头排列")
            elif latest.ma5 < latest.ma10 < latest.ma20:
                ma_align = "bearish"
                signals.append("MA 空头排列")

        ma5_above_ma20 = bool(
            latest.ma5 is not None and latest.ma20 is not None and latest.ma5 > latest.ma20
        )

        golden_cross_recent = False
        if prev and prev5:
            if (
                prev5.ma5 is not None and prev5.ma20 is not None
                and prev.ma5 is not None and prev.ma20 is not None
                and prev5.ma5 <= prev5.ma20
                and prev.ma5 > prev.ma20
            ):
                golden_cross_recent = True
                signals.append("MA 金叉")

        # ── MACD ────────────────────────────────────────
        macd_status = "neutral"
        if latest.macd_dif is not None and latest.macd_dea is not None:
            if prev and prev.macd_dif is not None and prev.macd_dea is not None:
                if prev.macd_dif <= prev.macd_dea and latest.macd_dif > latest.macd_dea:
                    macd_status = "golden_cross"
                    signals.append("MACD 金叉")
                elif prev.macd_dif >= prev.macd_dea and latest.macd_dif < latest.macd_dea:
                    macd_status = "death_cross"
                    signals.append("MACD 死叉")
            if macd_status == "neutral":
                if latest.macd_dif > 0:
                    macd_status = "above_zero"
                elif latest.macd_dif < 0:
                    macd_status = "below_zero"

        # ── RSI ─────────────────────────────────────────
        rsi_status = "neutral"
        rsi6_value = latest.rsi6 if latest.rsi6 is not None else 50.0
        if latest.rsi6 is not None:
            if latest.rsi6 > 70:
                rsi_status = "overbought"
                signals.append("RSI 超买")
            elif latest.rsi6 < 30:
                rsi_status = "oversold"
                signals.append("RSI 超卖")

        # ── KDJ ─────────────────────────────────────────
        kdj_status = "neutral"
        if latest.kdj_k is not None and latest.kdj_d is not None:
            if prev and prev.kdj_k is not None and prev.kdj_d is not None:
                if prev.kdj_k <= prev.kdj_d and latest.kdj_k > latest.kdj_d:
                    kdj_status = "golden_cross"
                    signals.append("KDJ 金叉")
                elif prev.kdj_k >= prev.kdj_d and latest.kdj_k < latest.kdj_d:
                    kdj_status = "death_cross"
                    signals.append("KDJ 死叉")
            if kdj_status == "neutral":
                if latest.kdj_j > 100:
                    kdj_status = "overbought"
                    signals.append("KDJ 超买")
                elif latest.kdj_j < 0:
                    kdj_status = "oversold"
                    signals.append("KDJ 超卖")

        # ── BOLL ────────────────────────────────────────
        boll_position = "middle"
        if latest.boll_up is not None and latest.boll_dn is not None and latest.boll_mid is not None:
            if latest.close > latest.boll_up:
                boll_position = "above_upper"
                signals.append("突破布林上轨")
            elif latest.close < latest.boll_dn:
                boll_position = "below_lower"
                signals.append("跌破布林下轨")
            elif latest.close > latest.boll_mid:
                boll_position = "upper_half"
            else:
                boll_position = "lower_half"

        # ── 涨跌幅 ─────────────────────────────────────
        pct_1d = latest.change_pct if latest.change_pct is not None else 0.0
        pct_30d = 0.0
        if len(klines) >= 30:
            prev_30 = klines[-30]
            if prev_30.close and prev_30.close > 0:
                pct_30d = (latest.close / prev_30.close - 1) * 100

        return TechnicalSummary(
            latest_close=latest.close,
            pct_change_1d=float(pct_1d),
            pct_change_30d=pct_30d,
            ma_alignment=ma_align,
            ma5=latest.ma5,
            ma10=latest.ma10,
            ma20=latest.ma20,
            ma60=latest.ma60,
            ma5_above_ma20=ma5_above_ma20,
            golden_cross_recent=golden_cross_recent,
            macd_status=macd_status,
            macd_dif=latest.macd_dif or 0.0,
            macd_dea=latest.macd_dea or 0.0,
            macd_bar=latest.macd_bar or 0.0,
            rsi6=rsi6_value,
            rsi_status=rsi_status,
            kdj_k=latest.kdj_k or 0.0,
            kdj_d=latest.kdj_d or 0.0,
            kdj_j=latest.kdj_j or 0.0,
            kdj_status=kdj_status,
            boll_up=latest.boll_up,
            boll_mid=latest.boll_mid,
            boll_dn=latest.boll_dn,
            boll_position=boll_position,
            signals=signals,
        )