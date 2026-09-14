# 02 - collectors 数据采集层

> 职责：对接外部数据源（AkShare/Tushare），只做数据拉取和格式转换，**不操作数据库**。
> 与业务域通过 `FetcherProtocol` 解耦，业务域 service 只感知接口，不感知具体数据源。

---

## 目录结构

```
src/collectors/
├── __init__.py
├── collector.py            ← 泛型 Collector（驱动 Fetcher）
├── interfaces/
│   ├── __init__.py
│   └── fetcher.py          ← FetcherProtocol + CollectParams + BaseData
└── akshare/
    ├── __init__.py
    ├── fetcher.py          ← AkShareFetcher（实现 FetcherProtocol）
    └── parser.py           ← DataFrame → Pydantic 转换
```

> **Tushare 适配器**（`collectors/tushare/`）在 Phase 2 实现，接口完全一致。

---

## collectors/interfaces/fetcher.py

```python
"""Fetcher 协议接口 + 采集参数"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


class BaseData(BaseModel):
    """所有采集数据的基类（Pydantic Model）"""
    pass


@dataclass
class CollectParams:
    """通用采集参数

    - symbol:     股票代码（K线/财务数据使用）
    - keyword:    关键词（新闻搜索使用）
    - start_date: 开始日期（优先级高于 days）
    - end_date:   结束日期（默认 today）
    - days:       回溯天数（start_date 为空时使用）
    """
    symbol: Optional[str] = None
    keyword: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 30


@runtime_checkable
class FetcherProtocol(Protocol):
    """所有数据源适配器必须满足此协议"""

    def fetch(self, params: CollectParams) -> list[BaseData]:
        """执行采集，返回 BaseData 子类列表"""
        ...
```

---

## collectors/collector.py

```python
"""泛型 Collector：驱动任意 FetcherProtocol 实现"""

from collectors.interfaces.fetcher import FetcherProtocol, CollectParams, BaseData


class Collector:
    """将 FetcherProtocol 实例包装为统一调用入口。

    用法：
        collector = Collector(AkShareFetcher(DailyKlineData))
        results = collector.collect(CollectParams(symbol="000001", days=30))
    """

    def __init__(self, fetcher: FetcherProtocol):
        self._fetcher = fetcher

    def collect(self, params: CollectParams) -> list[BaseData]:
        return self._fetcher.fetch(params)
```

---

## collectors/akshare/parser.py

```python
"""AkShare DataFrame → Pydantic 转换"""

from __future__ import annotations

import pandas as pd
from datetime import date

from kline.schema import DailyKlineData


class KlineParser:
    """将 AkShare stock_zh_a_hist 返回的 DataFrame 解析为 DailyKlineData 列表"""

    # AkShare 列名 → 模型字段名
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

    def parse(self, df: pd.DataFrame, symbol: str) -> list[DailyKlineData]:
        """转换 DataFrame，返回 DailyKlineData 列表"""
        if df is None or df.empty:
            return []

        df = df.rename(columns=self._COL_MAP)
        results = []

        for _, row in df.iterrows():
            try:
                results.append(
                    DailyKlineData(
                        symbol=symbol,
                        trade_date=date.fromisoformat(str(row["trade_date"])[:10]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=int(row["volume"]),
                        amount=float(row["amount"]),
                        change_pct=float(row["change_pct"]) if pd.notna(row.get("change_pct")) else None,
                    )
                )
            except (KeyError, ValueError):
                continue

        return results
```

> **注意**：`KlineParser` 现在 import `kline.schema.DailyKlineData`，而不是 `data.schemas.kline`。
> 这是唯一一处 collector 依赖业务域 schema 的地方，可接受（采集器天然需要知道目标数据结构）。

---

## collectors/akshare/fetcher.py

```python
"""AkShare 数据源适配器（实现 FetcherProtocol）"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import akshare as ak

from collectors.interfaces.fetcher import FetcherProtocol, CollectParams, BaseData
from collectors.akshare.parser import KlineParser
from kline.schema import DailyKlineData


class AkShareFetcher:
    """AkShare 适配器，满足 FetcherProtocol。

    根据构造时传入的 data_type 分发到对应采集方法：
        AkShareFetcher(DailyKlineData)  → 采集日K线

    用法：
        fetcher = AkShareFetcher(DailyKlineData)
        klines = fetcher.fetch(CollectParams(symbol="000001", days=365))
    """

    _DISPATCH = {
        DailyKlineData: "_fetch_daily_kline",
    }

    def __init__(self, data_type: type[BaseData]):
        method_name = self._DISPATCH.get(data_type)
        if method_name is None:
            supported = [t.__name__ for t in self._DISPATCH]
            raise ValueError(
                f"AkShareFetcher 不支持 {data_type.__name__}，支持: {supported}"
            )
        self._handler = getattr(self, method_name)
        self._parser = KlineParser()

    def fetch(self, params: CollectParams) -> list[BaseData]:
        return self._handler(params)

    # ── 私有采集方法 ───────────────────────────────────────

    def _fetch_daily_kline(self, params: CollectParams) -> list[DailyKlineData]:
        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))

        try:
            df = ak.stock_zh_a_hist(
                symbol=params.symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",
            )
        except Exception as e:
            raise RuntimeError(f"AkShare 获取 {params.symbol} K线失败: {e}") from e

        klines = self._parser.parse(df, params.symbol)

        # 补充股票名称
        name = self._get_stock_name(params.symbol)
        for k in klines:
            k.name = name

        return klines

    def _get_stock_name(self, symbol: str) -> str:
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return str(row.iloc[0]["名称"])
        except Exception:
            pass
        return ""
```

---

## collectors/akshare/__init__.py

```python
from .fetcher import AkShareFetcher

__all__ = ["AkShareFetcher"]
```

---

## 调用链示意

```
kline/service.py
    collector = Collector(AkShareFetcher(DailyKlineData))
    results = collector.collect(CollectParams(symbol="000001", days=365))
         ↓
    AkShareFetcher.fetch()
         ↓
    ak.stock_zh_a_hist() → DataFrame
         ↓
    KlineParser.parse() → list[DailyKlineData]
```

---

## 注意事项

1. **Fetcher 不操作数据库**：采集完成后返回 Pydantic 列表，由 Service 决定如何持久化
2. **错误处理**：Fetcher 内部 catch 外部 API 异常，统一 raise `RuntimeError`，Service 层决定如何响应
3. **AkShare 限速**：`stock_zh_a_spot_em()` 获取名称会触发全量接口，批量采集时建议缓存名称或单独维护
4. **扩展 Tushare**：Phase 2 只需新增 `collectors/tushare/fetcher.py`，`TushareFetcher` 实现相同的 `fetch` 方法，Service 层代码**不需要改动**
