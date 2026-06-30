# data 层架构设计

## 核心思路

`Collector(Fetcher(Data))` —— 两层抽象，两层多态。

---

## 三个核心抽象

### 1. `BaseData` —— 数据抽象

所有采集结果的基类，用 Pydantic BaseModel 继承。

```python
class BaseData(BaseModel):
    pass

class StockKline(BaseData): ...   # K线
class NewsItem(BaseData): ...     # 新闻（未来）
class MacroData(BaseData): ...    # 宏观数据（未来）
```

**职责**：定义"采出来的数据长什么样"，Fetcher 的返回类型。

---

### 2. `FetcherProtocol` —— 行为抽象

用 `typing.Protocol` 定义采集接口，具体实现类无需显式继承。

```python
class FetcherProtocol(Protocol):
    def fetch(self, params: CollectParams) -> list[BaseData]: ...
```

**实现类**（满足 Protocol 即可，不需要 extends）：

```python
class AkShareFetcher:            # 实现 FetcherProtocol
    def __init__(self, data_type: type[BaseData]):
        self._dispatch = {
            StockKline: self._fetch_kline,
            NewsItem:   self._fetch_news,
        }
        self._handler = self._dispatch[data_type]

    def fetch(self, params: CollectParams) -> list[BaseData]:
        return self._handler(params)

class TushareFetcher:            # 同样实现 FetcherProtocol
    def fetch(self, params: CollectParams) -> list[BaseData]: ...
```

**职责**：封装具体数据源（AkShare/Tushare），内部按 `data_type` 分发到对应方法。

---

### 3. `Collector` —— 编排层

只依赖 `FetcherProtocol`，不认识任何具体 Fetcher 或 Data。

```python
class Collector:
    def __init__(self, fetcher: FetcherProtocol):
        self.fetcher = fetcher

    def collect(self, params: CollectParams) -> list[BaseData]:
        return self.fetcher.fetch(params)
```

**职责**：计算参数（日期范围等）、调用 Fetcher、返回结果。

---

## 组合方式（在 Service 层装配）

```python
# 用 AkShare 采 K线
collector = Collector(AkShareFetcher(data_type=StockKline))

# 换数据源：一行
collector = Collector(TushareFetcher(data_type=StockKline))

# 换数据类型：一行
collector = Collector(AkShareFetcher(data_type=NewsItem))
```

---

## 扩展规则

| 新增内容 | 只需要 |
|---------|--------|
| 新数据源（如 tushare） | 新增 `TushareFetcher` 类 |
| 新数据类型（如新闻） | 新增 `NewsItem(BaseData)` + 在 Fetcher 里加 `_fetch_news` |
| 已有代码 | **不需要修改** |

---

## 设计模式对应

| 层 | 模式 |
|----|------|
| `Collector` 对 `FetcherProtocol` | 策略模式（Strategy）|
| `Fetcher` 对 `data_type` | 分发/工厂（Dispatch）|
| 整体 `Collector(Fetcher(Data))` | 依赖注入 + 组合（DI + Composition）|

---

## 目录结构

```
data/
├── interfaces/
│   └── fetcher.py          # FetcherProtocol, CollectParams
├── schemas/
│   ├── base.py             # BaseData
│   ├── stock.py            # StockKline, StockInfo
│   └── news.py             # NewsItem（未来）
├── adapters/               # 原 fetchers/，改名后更语义化
│   ├── akshare/
│   │   └── fetcher.py      # AkShareFetcher
│   └── tushare/            # （未来）
│       └── fetcher.py
├── parsers/                # DataFrame → BaseData 转换
├── collectors/
│   └── collector.py        # 通用 Collector
└── services/               # 装配层，决定用哪个组合
```
