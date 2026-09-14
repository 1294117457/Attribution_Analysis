# 07 - indicators 技术指标计算

> 技术指标域不采集数据，不存储数据，**纯计算层**。
> 从 `kline` 域读取 K 线，用 pandas 计算 MA/MACD/RSI/KDJ/布林带，返回给前端渲染 ECharts。

---

## indicators/calculator.py

```python
"""技术指标计算器（基于 pandas）"""

from __future__ import annotations

from datetime import date

import pandas as pd

from indicators.schema import MAPoint, MACDPoint, RSIPoint


class IndicatorCalculator:
    """接收包含 OHLCV 的 DataFrame，计算各类技术指标。

    DataFrame 要求：
        - index: date（升序）
        - columns: open, high, low, close, volume
    """

    def __init__(self, df: pd.DataFrame):
        self._df = df.copy()
        self._close = df["close"]

    # ── MA 均线 ──────────────────────────────────────────────

    def ma(self, periods: list[int] = [5, 10, 20, 60]) -> list[MAPoint]:
        """移动平均线（简单移动平均 SMA）"""
        result = pd.DataFrame(index=self._df.index)

        for p in periods:
            result[f"ma{p}"] = self._close.rolling(window=p).mean().round(3)

        points = []
        for idx, row in result.iterrows():
            points.append(MAPoint(
                date=idx,
                ma5=self._nan_to_none(row.get("ma5")),
                ma10=self._nan_to_none(row.get("ma10")),
                ma20=self._nan_to_none(row.get("ma20")),
                ma60=self._nan_to_none(row.get("ma60")),
            ))
        return points

    # ── MACD ─────────────────────────────────────────────────

    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> list[MACDPoint]:
        """MACD（指数移动平均差）

        DIF = EMA(close, 12) - EMA(close, 26)
        DEA = EMA(DIF, 9)
        MACD柱 = 2 × (DIF - DEA)
        """
        ema_fast = self._close.ewm(span=fast, adjust=False).mean()
        ema_slow = self._close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        histogram = 2 * (dif - dea)

        points = []
        for idx in self._df.index:
            points.append(MACDPoint(
                date=idx,
                dif=self._nan_to_none(round(dif[idx], 4)),
                dea=self._nan_to_none(round(dea[idx], 4)),
                macd=self._nan_to_none(round(histogram[idx], 4)),
            ))
        return points

    # ── RSI ──────────────────────────────────────────────────

    def rsi(self, periods: list[int] = [6, 12, 24]) -> list[RSIPoint]:
        """相对强弱指数（RSI）

        RSI = 100 - 100 / (1 + RS)
        RS  = 平均上涨幅度 / 平均下跌幅度（EMA 方式）
        """
        delta = self._close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        rsi_series: dict[int, pd.Series] = {}
        for p in periods:
            avg_gain = gain.ewm(com=p - 1, adjust=False).mean()
            avg_loss = loss.ewm(com=p - 1, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, float("inf"))
            rsi_series[p] = (100 - 100 / (1 + rs)).round(2)

        points = []
        for idx in self._df.index:
            points.append(RSIPoint(
                date=idx,
                rsi6=self._nan_to_none(rsi_series.get(6, pd.Series()).get(idx)),
                rsi12=self._nan_to_none(rsi_series.get(12, pd.Series()).get(idx)),
                rsi24=self._nan_to_none(rsi_series.get(24, pd.Series()).get(idx)),
            ))
        return points

    # ── KDJ（预留，Phase 2）─────────────────────────────────

    def kdj(self, n: int = 9, m1: int = 3, m2: int = 3):
        """KDJ 随机指标（预留接口，Phase 2 实现）"""
        raise NotImplementedError("KDJ 将在 Phase 2 实现")

    # ── 布林带（预留，Phase 2）──────────────────────────────

    def bollinger(self, period: int = 20, std_dev: float = 2.0):
        """布林带（预留接口，Phase 2 实现）"""
        raise NotImplementedError("布林带将在 Phase 2 实现")

    # ── 工具方法 ─────────────────────────────────────────────

    @staticmethod
    def _nan_to_none(value) -> float | None:
        """pandas NaN → Python None（JSON 序列化安全）"""
        if value is None:
            return None
        try:
            import math
            return None if math.isnan(float(value)) else float(value)
        except (TypeError, ValueError):
            return None
```

---

## 前端 ECharts 数据格式说明

`GET /api/indicators/{symbol}` 返回：

```json
{
  "code": 200,
  "data": {
    "symbol": "000001",
    "ma": [
      {"date": "2024-01-02", "ma5": 10.23, "ma10": null, "ma20": null, "ma60": null},
      {"date": "2024-01-03", "ma5": 10.31, "ma10": null, "ma20": null, "ma60": null}
    ],
    "macd": [
      {"date": "2024-01-02", "dif": 0.0012, "dea": 0.0008, "macd": 0.0008}
    ],
    "rsi": [
      {"date": "2024-01-02", "rsi6": 56.3, "rsi12": 52.1, "rsi24": null}
    ]
  }
}
```

**ECharts K线图 + MA 叠加示例（前端参考）：**

```javascript
// 主图：K线 + MA均线
const klineData = klines.items.map(k => [k.open, k.close, k.low, k.high])
const dateList = klines.items.map(k => k.date)
const ma5Data = indicators.ma.map(m => m.ma5)
const ma20Data = indicators.ma.map(m => m.ma20)

option = {
  xAxis: { data: dateList },
  yAxis: {},
  series: [
    { type: 'candlestick', data: klineData },
    { name: 'MA5', type: 'line', data: ma5Data, smooth: true },
    { name: 'MA20', type: 'line', data: ma20Data, smooth: true },
  ]
}
```

---

## 注意事项

1. **前 N 条数据为 null**：MA60 需要至少 60 条数据才有值，前 59 条返回 `null`，前端 ECharts 会自动跳过 null 点
2. **请求足够历史数据**：计算 MA60 时需至少 60 条 K 线，建议接口默认 `limit=500`
3. **不需要单独采集**：指标完全从已存储的 K 线计算，无需额外数据源
4. **性能**：pandas 计算 500 条 K 线 + 全部指标 < 10ms，无需缓存（如有需要可在 Phase 2 加 Redis 缓存）
