# Data 模块设计分析

## 1. 模块定位

```
┌─────────────────────────────────────────────────────────────────┐
│                      data/ (数据采集层)                           │
│                                                                 │
│   fetchers/ ──────▶ 从数据源获取原始数据                         │
│   parsers/ ───────▶ 解析和转换数据                               │
│   collectors/ ────▶ 封装采集流程                                │
│   models/ ───────▶ 数据模型定义                                 │
│   scripts/ ──────▶ 采集脚本                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      app/ (API 层)                               │
│   database/ ──────▶ 持久化到数据库                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ml/ (机器学习层)                            │
│   detector/ ───────▶ 异常检测                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 分层设计

### 2.1 三层职责

```
数据源 (AkShare, Tushare, News API)
    │
    ▼
┌─────────────────────────────────────────┐
│          fetchers/ (获取层)              │
│  - 负责与数据源交互                      │
│  - 返回原始数据 dict/DataFrame          │
│  - 不做业务逻辑                          │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│          parsers/ (解析层)               │
│  - 负责数据转换                          │
│  - raw model → core model               │
│  - 数据清洗和标准化                      │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│         collectors/ (采集层)             │
│  - 封装完整采集流程                      │
│  - 错误处理                              │
│  - 返回采集结果                          │
└─────────────────────────────────────────┘
    │
    ▼
数据库 / 内存
```

### 2.2 为什么需要三层？

| 层级 | 职责 | 可替换性 |
|------|------|----------|
| fetcher | 获取逻辑 | 换数据源不改 parser |
| parser | 转换逻辑 | 换数据源不改 collector |
| collector | 采集流程 | 整体可复用 |

**示例**：从 AkShare 切换到 Tushare
```python
# 只需替换 fetcher
class StockCollector(BaseCollector):
    def __init__(self):
        # 替换这里
        fetcher = TushareFetcher()  # 而不是 AkShareFetcher()
        super().__init__(fetcher)
```

## 3. Fetcher 设计

### 3.1 泛型基类

```python
T = TypeVar("T")

class BaseFetcher(ABC, Generic[T]):
    @abstractmethod
    async def fetch(self, **kwargs) -> list[T]:
        pass
```

**设计理由**：
- 泛型确保类型安全
- `list[T]` 返回统一
- 便于类型检查

### 3.2 AkShare 获取器

```python
class AkShareFetcher(BaseFetcher[RawStockKline]):
    async def fetch_stock_kline(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[RawStockKline]:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
            adjust="qfq",
        )
        # 转换为 RawStockKline
```

**特点**：
- 异步方法 `async/await`
- 日期格式转换
- DataFrame → Pydantic 模型

### 3.3 扩展更多数据源

```python
# Tushare 获取器
class TushareFetcher(BaseFetcher[RawStockKline]):
    async def fetch(self, **kwargs) -> list[RawStockKline]:
        import tushare as ts
        pro = ts.pro_api(TOKEN)
        df = pro.daily(ts_code=kwargs["symbol"], ...)
        # 转换...
```

## 4. Parser 设计

### 4.1 转换链

```
RawStockKline (fetchers 返回)
    │
    ▼
StockParser.to_core_model()
    │
    ▼
StockKline (core/models)
    │
    ▼
StockWithIndicators (添加技术指标)
```

### 4.2 技术指标计算

```python
class StockParser:
    @staticmethod
    def parse_ma(prices: list[float], period: int) -> float | None:
        """计算移动平均"""
        if len(prices) < period:
            return None
        return round(sum(prices[-period:]) / period, 2)

    @staticmethod
    def parse_rsi(prices: list[float], period: int = 14) -> float:
        """计算 RSI"""
        # 详细实现...
```

## 5. Collector 设计

### 5.1 状态机

```
CollectStatus:
    ├── SUCCESS ──── 数据完整获取
    ├── PARTIAL ─── 部分成功（如网络中断）
    └── FAILED ──── 完全失败
```

### 5.2 采集结果

```python
class CollectResult:
    status: CollectStatus      # 采集状态
    symbol: str                 # 股票代码
    start_date: date           # 开始日期
    end_date: date             # 结束日期
    records_count: int         # 记录数
    error: str | None          # 错误信息
    collected_at: datetime     # 采集时间
```

**设计理由**：
- 状态字段便于判断
- 时间戳便于追踪
- 错误信息便于排查

## 6. 脚本设计

### 6.1 每日采集

```python
# scripts/daily_collect.py
async def daily_collect():
    """每日定时任务"""
    stocks = get_watchlist()  # 监控列表
    for symbol in stocks:
        result = await collector.collect(symbol, today, today)
        log_result(result)
```

**使用方式**：
```bash
# 手动运行
python -m data.scripts.daily_collect

# 定时任务 (crontab)
0 16 * * * python -m data.scripts.daily_collect
```

### 6.2 批量采集

```python
# scripts/batch_collect.py
async def batch_collect(symbol: str, days: int):
    """批量历史数据"""
    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    return await collector.collect(symbol, start_date, end_date)
```

**使用方式**：
```bash
# 采集平安银行最近 30 天
python -m data.scripts.batch_collect 000001 30

# 采集 1 年数据
python -m data.scripts.batch_collect 000001 365
```

## 7. 错误处理

### 7.1 Fetcher 错误

```python
async def fetch(self, **kwargs) -> list[RawStockKline]:
    try:
        df = ak.stock_zh_a_hist(...)
        return self._parse(df)
    except Exception as e:
        logger.error(f"获取数据失败: {e}")
        return []  # 返回空列表
```

### 7.2 Collector 错误

```python
async def _collect(self, symbol, start, end) -> CollectResult:
    try:
        data = await self.fetcher.fetch(...)
        return CollectResult(status=SUCCESS, ...)
    except Exception as e:
        return CollectResult(status=FAILED, error=str(e))
```

## 8. 扩展指南

### 8.1 添加新的数据源

1. `data/fetchers/` - 创建新的 fetcher
2. 继承 `BaseFetcher`
3. 实现 `fetch` 方法

```python
class EastmoneyFetcher(BaseFetcher[RawStockKline]):
    async def fetch(self, **kwargs) -> list[RawStockKline]:
        # 东方财富 API
        ...
```

### 8.2 添加新的解析规则

1. `data/parsers/` - 创建新的 parser
2. 实现转换方法

```python
class StockParser:
    @staticmethod
    def parse_boll(prices: list[float], period: int = 20) -> dict:
        """计算布林带"""
        middle = parse_ma(prices, period)
        std = statistics.stdev(prices[-period:])
        return {
            "upper": middle + 2 * std,
            "middle": middle,
            "lower": middle - 2 * std,
        }
```

### 8.3 添加新的采集场景

1. `data/collectors/` - 创建新的 collector
2. 组合 fetcher 和 parser

```python
class IndexCollector(BaseCollector[RawStockKline]):
    """指数数据采集器"""
    async def collect(self, symbol: str, start_date, end_date):
        # 指数特有的采集逻辑
        ...
```

## 9. 测试策略

```python
# tests/test_data/test_akshare_fetcher.py
import pytest
from datetime import date
from data.fetchers.akshare_fetcher import AkShareFetcher

@pytest.mark.asyncio
async def test_fetch_stock_kline():
    fetcher = AkShareFetcher()
    data = await fetcher.fetch_stock_kline(
        symbol="000001",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 10),
    )
    assert len(data) > 0
    assert data[0].symbol == "000001"
```

## 10. 常见问题

### Q: 为什么 fetcher 返回的是 `RawStockKline` 而不是 `StockKline`？

**A**: 因为 `RawStockKline` 保留了 `raw_data`，便于：
- 调试原始数据
- 处理不同数据源的字段差异
- 追溯数据来源

### Q: 如何处理数据源 API 限流？

**A**: 在 fetcher 中添加延迟：

```python
import asyncio
import time

async def fetch(self, **kwargs):
    await asyncio.sleep(0.5)  # 0.5 秒间隔
    return await self._fetch_impl(**kwargs)
```

### Q: 历史数据量大怎么办？

**A**: 分批采集：

```python
async def batch_collect(symbol, start, end, batch_days=30):
    current = start
    while current < end:
        next_date = min(current + timedelta(batch_days), end)
        await collector.collect(symbol, current, next_date)
        current = next_date + timedelta(1)
```
