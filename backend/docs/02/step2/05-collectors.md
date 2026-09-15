# 05 - Collectors 防腐层（ACL）

> 防腐层（Anti-Corruption Layer）是 DDD 中用于隔离外部系统的组件。
> 采集层负责从外部数据源（AkShare、Tushare）获取数据，并转换为领域层可以理解的数据结构。

---

## 目录结构

```
src/infrastructure/collectors/
├── __init__.py
├── interfaces.py             # FetcherProtocol + CollectParams
├── base.py                   # Collector 基类
└── akshare/
    ├── __init__.py
    ├── fetcher.py            # AkShareFetcher
    └── parser.py             # KlineParser
```

---

## 设计原则

### 为什么需要防腐层？

```
┌─────────────────────────────────────────────────────────────────┐
│                        外部数据源                                  │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐                   │
│   │ AkShare │    │ Tushare │    │  其他   │                   │
│   └────┬────┘    └────┬────┘    └────┬────┘                   │
└────────┼──────────────┼──────────────┼───────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Collectors（防腐层）                        ││
│  │                                                             ││
│  │  1. 适配不同的外部 API                                        ││
│  │  2. 处理 API 版本变化                                        ││
│  │  3. 转换数据格式                                             ││
│  │  4. 统一错误处理                                             ││
│  │  5. 限流和缓存                                               ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Domain（领域层）                           ││
│  │                                                             ││
│  │  - Kline                                                    ││
│  │  - KlineBO (Business Object)                                ││
│  │  - domain.kline.schemas                                     ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 防腐层职责

| 职责 | 说明 |
|------|------|
| **接口适配** | 将不同外部 API 转换为统一的内部接口 |
| **格式转换** | 将外部格式（DataFrame、dict）转换为领域对象 |
| **错误处理** | 捕获外部 API 异常，转换为内部异常 |
| **限流控制** | 防止外部 API 调用过于频繁 |
| **缓存** | 缓存频繁访问的数据（如股票名称） |

---

## infrastructure/collectors/interfaces.py 接口定义

```python
"""采集器接口定义

防腐层对外暴露的统一接口。
所有采集器必须实现 FetcherProtocol。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel


@dataclass
class CollectParams:
    """通用采集参数
    
    所有采集器都接受这个统一的参数结构。
    具体采集器可以忽略不需要的参数。
    """
    
    symbol: Optional[str] = None              # 股票代码
    keyword: Optional[str] = None             # 搜索关键词
    start_date: Optional[date] = None         # 开始日期
    end_date: Optional[date] = None           # 结束日期
    days: int = 30                            # 回溯天数（start_date 为空时使用）
    adjust: str = "qfq"                      # 复权类型：qfq/qianfu/none


@runtime_checkable
class FetcherProtocol(Protocol):
    """采集器协议
    
    所有数据源适配器必须满足此协议。
    使用 @runtime_checkable 支持 isinstance 检查。
    
    接口方法：
    - fetch(params): 执行采集，返回领域对象列表
    """
    
    def fetch(self, params: CollectParams) -> list[BaseModel]:
        """执行采集
        
        Args:
            params: 采集参数
            
        Returns:
            list[BaseModel]: 采集到的数据列表（领域对象）
            
        Raises:
            RuntimeError: 采集失败时抛出
        """
        ...
    
    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...
    
    @property
    def supported_types(self) -> list[type[BaseModel]]:
        """支持的数据类型"""
        ...
```

---

## infrastructure/collectors/base.py 采集器基类

```python
"""采集器基类

提供采集器的通用功能：
- 日志记录
- 错误处理
- 重试机制（可选）
"""

from __future__ import annotations

import logging
from abc import ABC
from typing import Optional

from infrastructure.collectors.interfaces import FetcherProtocol, CollectParams

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """采集器基类
    
    提供通用功能，子类只需实现核心的 fetch 方法。
    """
    
    def __init__(self):
        self._logger = logger
        self._cache: dict = {}  # 简单内存缓存
    
    def _get_cache(self, key: str) -> Optional[any]:
        """获取缓存"""
        return self._cache.get(key)
    
    def _set_cache(self, key: str, value: any, ttl: int = 300) -> None:
        """设置缓存（简单实现，生产环境建议用 Redis）"""
        self._cache[key] = value
    
    def _clear_cache(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def _log(self, level: str, message: str, **kwargs) -> None:
        """日志记录"""
        extra = {"source": self.source_name}
        extra.update(kwargs)
        getattr(self._logger, level)(message, extra=extra)
    
    def _wrap_error(self, message: str, original_error: Exception) -> RuntimeError:
        """包装错误"""
        return RuntimeError(f"{self.source_name}: {message}") from original_error
```

---

## infrastructure/collectors/akshare/parser.py 数据解析器

```python
"""AkShare 数据解析器

将 AkShare 返回的 DataFrame 转换为领域对象。
注意：这里使用领域层定义的 KlineBO，不依赖具体的数据源。
"""

from __future__ import annotations

import pandas as pd
from datetime import date, datetime

from domain.kline.schemas import KlineBO


class KlineParser:
    """K线数据解析器
    
    将 AkShare 返回的 DataFrame 解析为 KlineBO 列表。
    """
    
    # AkShare 列名 → KlineBO 字段名
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
        """解析 DataFrame
        
        Args:
            df: AkShare 返回的 DataFrame
            symbol: 股票代码
            
        Returns:
            list[KlineBO]: K线业务对象列表
        """
        if df is None or df.empty:
            return []
        
        # 重命名列
        df = df.rename(columns=self._COL_MAP)
        
        results = []
        for _, row in df.iterrows():
            try:
                kline = self._parse_row(row, symbol)
                results.append(kline)
            except (KeyError, ValueError, TypeError) as e:
                # 单行解析失败不影响其他行
                continue
        
        return results
    
    def _parse_row(self, row: pd.Series, symbol: str) -> KlineBO:
        """解析单行数据"""
        # 解析日期
        trade_date = self._parse_date(row["trade_date"])
        
        # 解析价格数据
        open_price = self._parse_float(row["open"])
        high_price = self._parse_float(row["high"])
        low_price = self._parse_float(row["low"])
        close_price = self._parse_float(row["close"])
        
        # 解析交易数据
        volume = self._parse_int(row["volume"])
        amount = self._parse_float(row["amount"])
        change_pct = self._parse_float_or_none(row.get("change_pct"))
        
        return KlineBO(
            symbol=symbol,
            name="",  # 名称由 fetcher 补充
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
        """解析日期"""
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            # 尝试多种日期格式
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        raise ValueError(f"无法解析日期: {value}")
    
    def _parse_float(self, value) -> float:
        """解析浮点数"""
        if pd.isna(value):
            return 0.0
        return float(value)
    
    def _parse_int(self, value) -> int:
        """解析整数"""
        if pd.isna(value):
            return 0
        return int(value)
    
    def _parse_float_or_none(self, value) -> float | None:
        """解析可选浮点数"""
        if value is None or pd.isna(value):
            return None
        return float(value)
```

---

## infrastructure/collectors/akshare/fetcher.py AkShare 采集器

```python
"""AkShare 数据采集器

实现 FetcherProtocol，从 AkShare 获取股票数据。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import akshare as ak

from infrastructure.collectors.interfaces import FetcherProtocol, CollectParams
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.akshare.parser import KlineParser
from domain.kline.schemas import KlineBO


class AkShareFetcher(BaseCollector):
    """AkShare 数据采集器
    
    支持的数据类型：
    - KlineBO：日K线数据
    
    用法：
        fetcher = AkShareFetcher()
        params = CollectParams(symbol="000001", days=365)
        klines = fetcher.fetch(params)
    """
    
    def __init__(self, data_type: type[KlineBO] = KlineBO):
        super().__init__()
        self._data_type = data_type
        self._parser = KlineParser()
        
        # 缓存股票名称（避免频繁调用全量接口）
        self._name_cache: dict[str, str] = {}
    
    @property
    def source_name(self) -> str:
        return "AkShare"
    
    @property
    def supported_types(self) -> list[type[KlineBO]]:
        return [KlineBO]
    
    def fetch(self, params: CollectParams) -> list[KlineBO]:
        """执行采集
        
        根据 data_type 分发到对应的采集方法。
        """
        self._log("info", f"开始采集: {params.symbol}")
        
        if self._data_type == KlineBO:
            return self._fetch_kline(params)
        
        raise ValueError(f"不支持的数据类型: {self._data_type}")
    
    def _fetch_kline(self, params: CollectParams) -> list[KlineBO]:
        """采集K线数据"""
        if not params.symbol:
            raise ValueError("采集K线需要提供 symbol")
        
        # 计算日期范围
        end_date = params.end_date or date.today()
        start_date = params.start_date or (end_date - timedelta(days=params.days))
        
        try:
            # 调用 AkShare
            df = ak.stock_zh_a_hist(
                symbol=params.symbol,
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=params.adjust,
            )
        except Exception as e:
            raise self._wrap_error(f"获取 {params.symbol} K线失败", e)
        
        # 解析数据
        klines = self._parser.parse(df, params.symbol)
        
        # 补充股票名称
        name = self._get_stock_name(params.symbol)
        for kline in klines:
            kline.name = name
        
        self._log("info", f"采集完成: {params.symbol}, 获取 {len(klines)} 条数据")
        return klines
    
    def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称（带缓存）"""
        if symbol in self._name_cache:
            return self._name_cache[symbol]
        
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                name = str(row.iloc[0]["名称"])
                self._name_cache[symbol] = name
                return name
        except Exception as e:
            self._log("warning", f"获取股票名称失败: {symbol}", error=str(e))
        
        return ""
    
    def get_realtime_quote(self, symbol: str) -> dict:
        """获取实时行情（扩展接口）
        
        注意：这是非标准接口，用于实时数据展示。
        """
        try:
            df = ak.stock_zh_a_spot_em()
            row = df[df["代码"] == symbol]
            if not row.empty:
                return row.iloc[0].to_dict()
        except Exception as e:
            self._log("error", f"获取实时行情失败: {symbol}", error=str(e))
        return {}
```

---

## infrastructure/collectors/akshare/__init__.py

```python
"""AkShare 采集器导出"""

from infrastructure.collectors.akshare.fetcher import AkShareFetcher
from infrastructure.collectors.akshare.parser import KlineParser

__all__ = ["AkShareFetcher", "KlineParser"]
```

---

## infrastructure/collectors/__init__.py

```python
"""采集器模块导出"""

from infrastructure.collectors.interfaces import FetcherProtocol, CollectParams
from infrastructure.collectors.base import BaseCollector

__all__ = [
    "FetcherProtocol",
    "CollectParams",
    "BaseCollector",
]
```

---

## 扩展：Tushare 采集器（Phase 2）

```python
# infrastructure/collectors/tushare/fetcher.py

class TushareFetcher(BaseCollector):
    """Tushare 数据采集器
    
    实现与 AkShareFetcher 相同的接口。
    替换数据源时，路由层代码不需要改动。
    """
    
    def __init__(self, token: str, data_type: type[KlineBO] = KlineBO):
        super().__init__()
        self._token = token
        self._data_type = data_type
        # import tushare as ts
        # ts.set_token(token)
        # self._pro = ts.pro_api()
    
    @property
    def source_name(self) -> str:
        return "Tushare"
    
    @property
    def supported_types(self) -> list[type[KlineBO]]:
        return [KlineBO]
    
    def fetch(self, params: CollectParams) -> list[KlineBO]:
        if self._data_type == KlineBO:
            return self._fetch_kline(params)
        raise ValueError(f"不支持的数据类型: {self._data_type}")
    
    def _fetch_kline(self, params: CollectParams) -> list[KlineBO]:
        # 实现 Tushare API 调用
        ...
```

---

## 调用链示意

```
┌─────────────────────────────────────────────────────────────────┐
│                     Route Layer                                   │
│  route/api/v1/kline.py                                           │
│      ↓ KlineCollectRequest                                      │
├─────────────────────────────────────────────────────────────────┤
│                     Application Layer                             │
│  application/kline_service.py                                    │
│      ↓ KlineCollectRequest                                       │
│      ↓ 调用 FetcherProtocol                                      │
├─────────────────────────────────────────────────────────────────┤
│                   Infrastructure (ACL)                            │
│  infrastructure/collectors/akshare/fetcher.py                    │
│      ↓ CollectParams                                             │
│      ↓ ak.stock_zh_a_hist()  →  DataFrame                       │
│      ↓ KlineParser.parse()  →  list[KlineBO]                    │
├─────────────────────────────────────────────────────────────────┤
│                       Domain Layer                               │
│  domain/kline/schemas.py                                        │
│      KlineBO.to_entity()  →  list[Kline]                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 注意事项

1. **防腐层独立于领域层**：采集器可以引用领域层的 Schema（如 `KlineBO`），但不能引用应用服务
2. **错误转换**：外部 API 异常应该被捕获并转换为 `RuntimeError`，不应直接传播到应用层
3. **缓存策略**：使用简单的内存缓存，生产环境建议使用 Redis
4. **限流**：注意 AkShare 的接口调用频率限制，避免被封禁
5. **数据验证**：Parser 层应该验证数据合法性，丢弃无效数据但不影响其他数据
6. **接口一致性**：不同的 Fetcher 实现（AkShare、Tushare）必须提供相同的接口，应用层可以透明切换
