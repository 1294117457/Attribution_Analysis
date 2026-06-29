# Data 模块开发步骤

## 概述

`data` 模块负责数据采集，包含：
- **fetchers**: 数据获取（AkShare、Tushare、新闻源）
- **collectors**: 采集器（封装采集流程）
- **parsers**: 数据解析

---

## 开发步骤

### Step 1: 创建目录结构

```
backend/data/
├── __init__.py
│
├── config.py                  # data 模块配置
│
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── raw.py               # 原始数据
│   └── collector.py         # 采集结果
│
├── fetchers/                  # 数据获取
│   ├── __init__.py
│   ├── base.py              # BaseFetcher
│   ├── akshare_fetcher.py   # AkShare 获取器
│   └── news_fetcher.py      # 新闻获取器
│
├── collectors/                # 采集器
│   ├── __init__.py
│   ├── base.py              # BaseCollector
│   ├── stock_collector.py   # 股票采集器
│   └── anomaly_collector.py # 异常数据采集
│
├── parsers/                   # 数据解析
│   ├── __init__.py
│   ├── stock_parser.py      # 股票解析
│   └── anomaly_parser.py    # 异常解析
│
└── scripts/                   # 采集脚本
    ├── __init__.py
    ├── daily_collect.py      # 每日采集
    └── batch_collect.py      # 批量采集
```

### Step 2: 原始数据模型 (`models/raw.py`)

```python
from pydantic import BaseModel
from datetime import date
from typing import Optional

class RawStockKline(BaseModel):
    """原始K线数据（来自数据源）"""
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float

    # 原始字段（未标准化）
    raw_data: dict  # 保留原始数据

class RawNews(BaseModel):
    """原始新闻数据"""
    title: str
    content: str
    publish_date: date
    source: str
    url: Optional[str] = None
    raw_data: dict
```

### Step 3: 采集结果模型 (`models/collector.py`)

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from enum import Enum

class CollectStatus(str, Enum):
    """采集状态"""
    SUCCESS = "success"
    PARTIAL = "partial"  # 部分成功
    FAILED = "failed"

class CollectResult(BaseModel):
    """采集结果"""
    status: CollectStatus
    symbol: str
    start_date: date
    end_date: date
    records_count: int = 0
    error: Optional[str] = None
    collected_at: datetime
```

### Step 4: 基础获取器 (`fetchers/base.py`)

```python
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from data.models.raw import RawStockKline, RawNews

T = TypeVar("T")

class BaseFetcher(ABC, Generic[T]):
    """数据获取器基类"""

    def __init__(self):
        self.source_name: str = "unknown"

    @abstractmethod
    async def fetch(self, **kwargs) -> list[T]:
        """获取数据"""
        pass

    def validate(self, data: dict) -> bool:
        """验证数据格式"""
        return True
```

### Step 5: AkShare 获取器 (`fetchers/akshare_fetcher.py`)

```python
import akshare as ak
from datetime import date, timedelta
from typing import Optional
from data.fetchers.base import BaseFetcher
from data.models.raw import RawStockKline

class AkShareFetcher(BaseFetcher[RawStockKline]):
    """AkShare 数据获取器"""

    def __init__(self):
        super().__init__()
        self.source_name = "akshare"

    async def fetch_stock_kline(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[RawStockKline]:
        """获取股票K线数据"""

        # 格式化日期
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")

        # 调用 AkShare
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            start_date=start_str,
            end_date=end_str,
            adjust="qfq",
        )

        # 转换为 RawStockKline
        results = []
        for _, row in df.iterrows():
            results.append(RawStockKline(
                symbol=symbol,
                date=row["日期"].date() if hasattr(row["日期"], "date") else row["日期"],
                open=float(row["开盘"]),
                high=float(row["最高"]),
                low=float(row["最低"]),
                close=float(row["收盘"]),
                volume=float(row["成交量"]),
                amount=float(row["成交额"]),
                raw_data=row.to_dict(),
            ))

        return results

    async def fetch(self, **kwargs) -> list[RawStockKline]:
        """通用 fetch 方法"""
        return await self.fetch_stock_kline(
            symbol=kwargs["symbol"],
            start_date=kwargs["start_date"],
            end_date=kwargs["end_date"],
        )
```

### Step 6: 新闻获取器 (`fetchers/news_fetcher.py`)

```python
import akshare as ak
from datetime import date
from data.fetchers.base import BaseFetcher
from data.models.raw import RawNews

class NewsFetcher(BaseFetcher[RawNews]):
    """新闻数据获取器"""

    def __init__(self):
        super().__init__()
        self.source_name = "news"

    async def fetch_stock_news(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[RawNews]:
        """获取股票新闻"""

        # AkShare 财经新闻
        df = ak.stock_news_em(symbol=symbol)

        results = []
        for _, row in df.iterrows():
            publish_date = row.get("发布时间")
            if not publish_date:
                continue

            results.append(RawNews(
                title=row.get("新闻标题", ""),
                content=row.get("新闻内容", ""),
                publish_date=publish_date,
                source=row.get("文章来源", ""),
                url=row.get("文章来源", ""),
                raw_data=row.to_dict(),
            ))

        return results

    async def fetch(self, **kwargs) -> list[RawNews]:
        return await self.fetch_stock_news(
            symbol=kwargs["symbol"],
            start_date=kwargs["start_date"],
            end_date=kwargs["end_date"],
        )
```

### Step 7: 基础采集器 (`collectors/base.py`)

```python
from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Generic, TypeVar
from data.fetchers.base import BaseFetcher
from data.models.raw import T
from data.models.collector import CollectResult, CollectStatus

T = TypeVar("T")

class BaseCollector(ABC, Generic[T]):
    """采集器基类"""

    def __init__(self, fetcher: BaseFetcher[T]):
        self.fetcher = fetcher

    @abstractmethod
    async def collect(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> CollectResult:
        """执行采集"""
        pass

    async def _collect(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> CollectResult:
        """通用采集流程"""
        try:
            data = await self.fetcher.fetch(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            return CollectResult(
                status=CollectStatus.SUCCESS,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                records_count=len(data),
                collected_at=datetime.now(),
            )
        except Exception as e:
            return CollectResult(
                status=CollectStatus.FAILED,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                error=str(e),
                collected_at=datetime.now(),
            )
```

### Step 8: 股票采集器 (`collectors/stock_collector.py`)

```python
from datetime import date
from data.collectors.base import BaseCollector
from data.fetchers.akshare_fetcher import AkShareFetcher
from data.models.raw import RawStockKline
from data.models.collector import CollectResult

class StockCollector(BaseCollector[RawStockKline]):
    """股票数据采集器"""

    def __init__(self):
        fetcher = AkShareFetcher()
        super().__init__(fetcher)

    async def collect(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> CollectResult:
        """采集股票K线数据"""
        return await self._collect(symbol, start_date, end_date)

    async def collect_to_db(self, symbol: str, days: int = 365) -> CollectResult:
        """采集最近 N 天数据并保存到数据库"""
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        result = await self.collect(symbol, start_date, end_date)

        if result.status == "success":
            # TODO: 转换为 ORM 模型并保存
            pass

        return result
```

### Step 9: 数据解析器 (`parsers/stock_parser.py`)

```python
from datetime import date
from data.models.raw import RawStockKline
from core.models.stock import StockKline, StockWithIndicators

class StockParser:
    """股票数据解析器"""

    @staticmethod
    def to_core_model(raw: RawStockKline) -> StockKline:
        """转换为核心领域模型"""
        # 计算涨跌幅
        # TODO: 需要前一日收盘价
        return StockKline(
            symbol=raw.symbol,
            name="",  # 需要单独获取
            market="sz",  # 需要判断
            date=raw.date,
            open=raw.open,
            high=raw.high,
            low=raw.low,
            close=raw.close,
            volume=int(raw.volume),
            amount=raw.amount,
        )

    @staticmethod
    def parse_change_pct(current: float, previous: float) -> float:
        """计算涨跌幅"""
        if previous == 0:
            return 0.0
        return round((current - previous) / previous * 100, 2)

    @staticmethod
    def parse_ma(prices: list[float], period: int) -> float | None:
        """计算移动平均"""
        if len(prices) < period:
            return None
        return round(sum(prices[-period:]) / period, 2)
```

### Step 10: 每日采集脚本 (`scripts/daily_collect.py`)

```python
"""
每日数据采集脚本
使用方法: python -m data.scripts.daily_collect
"""

import asyncio
from datetime import date
from data.collectors.stock_collector import StockCollector

# 演示股票列表
DEMO_STOCKS = ["000001", "000002", "600000", "600036"]

async def daily_collect():
    """每日采集"""
    collector = StockCollector()
    today = date.today()

    results = []
    for symbol in DEMO_STOCKS:
        print(f"采集 {symbol} ...")
        result = await collector.collect(
            symbol=symbol,
            start_date=today,
            end_date=today,
        )
        results.append(result)
        print(f"  状态: {result.status}, 数量: {result.records_count}")

    return results

if __name__ == "__main__":
    asyncio.run(daily_collect())
```

### Step 11: 批量采集脚本 (`scripts/batch_collect.py`)

```python
"""
批量采集脚本
使用方法: python -m data.scripts.batch_collect 000001 30
"""

import asyncio
import sys
from datetime import date, timedelta
from data.collectors.stock_collector import StockCollector

async def batch_collect(symbol: str, days: int):
    """批量采集"""
    collector = StockCollector()
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    print(f"批量采集 {symbol}, 从 {start_date} 到 {end_date} ...")
    result = await collector.collect(symbol, start_date, end_date)

    print(f"状态: {result.status}")
    print(f"记录数: {result.records_count}")
    if result.error:
        print(f"错误: {result.error}")

    return result

if __name__ == "__main__":
    symbol = sys.argv[1] if len(sys.argv) > 1 else "000001"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 365

    asyncio.run(batch_collect(symbol, days))
```

---

## 验证清单

- [ ] AkShare 能正常获取股票数据
- [ ] StockCollector 能采集并返回结果
- [ ] StockParser 能转换为核心模型
- [ ] 每日采集脚本能运行
- [ ] 批量采集脚本能运行
- [ ] 采集结果格式正确

---

## 目录结构汇总

```
data/
├── __init__.py
├── config.py
│
├── models/
│   ├── __init__.py
│   ├── raw.py
│   └── collector.py
│
├── fetchers/
│   ├── __init__.py
│   ├── base.py
│   ├── akshare_fetcher.py
│   └── news_fetcher.py
│
├── collectors/
│   ├── __init__.py
│   ├── base.py
│   └── stock_collector.py
│
├── parsers/
│   ├── __init__.py
│   └── stock_parser.py
│
└── scripts/
    ├── __init__.py
    ├── daily_collect.py
    └── batch_collect.py
```
