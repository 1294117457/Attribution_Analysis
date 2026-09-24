# 采集器协议层问题分析

> 分析日期：2026-09-24
> 涉及目录：`backend/src/infrastructure/collectors/`

## 一、当前架构概览

```
infrastructure/collectors/
├── interfaces.py          ← FetcherProtocol（统一协议）+ CollectParams
├── base.py                ← BaseCollector（日志、错误处理基类）
├── tushare/
│   ├── fetcher.py         ← TushareFetcher（日K、股票信息、日频估值）
│   └── parser.py          ← TushareKlineParser
└── pytdx/
    ├── fetcher.py         ← PytdxFetcher（分钟K线，实时透传不落库）
    └── parser.py          ← PytdxKlineParser
```

### 当前数据流

```
Route 层 (FastAPI Depends)
  → 各路由文件内的工厂函数（硬编码 TushareFetcher / PytdxFetcher）
    → Application Service（接收 FetcherProtocol）
      → 具体 Fetcher 实现（Tushare / Pytdx）
        → 返回领域 BO（KlineBO / StockInfoBO / FinDailyBasicBO / MinuteKlineBO）
```

### 现有工厂函数分布（4 处，分散在路由层）

| 工厂函数 | 位置 | 返回类型 | 缓存 |
|---------|------|---------|------|
| `get_kline_fetcher()` | `route/api/v1/kline.py:33` | `TushareFetcher(KlineBO)` | `@lru_cache` |
| `get_stock_fetcher()` | `route/api/v1/stock.py:34` | `TushareFetcher(KlineBO)` | `@lru_cache` |
| `_get_tushare_fetcher()` | `route/api/v1/collect_task.py:27` | `TushareFetcher(KlineBO)` | 无（每次 new） |
| `get_pytdx_fetcher()` | `route/api/v1/minute_kline.py:18` | `PytdxFetcher()` | `@lru_cache` |

另外 `infrastructure/tasks/operation_dispatcher.py:82` 也直接 `TushareFetcher(KlineBO)`。

### 协议使用情况

| 消费方 | 依赖的类型 | 说明 |
|--------|----------|------|
| `kline_service.py` | `FetcherProtocol` | `collect()` / `collect_batch()` |
| `stock_service.py` | `FetcherProtocol` | `sync_stocks()` |
| `kline.py` 路由 | `FetcherProtocol` | Depends 注入 |
| `stock.py` 路由 | `FetcherProtocol` | Depends 注入 |
| `collect_task.py` 路由 | `FetcherProtocol` | 后台任务 |
| `minute_kline.py` 路由 | **直接依赖 `PytdxFetcher` 具体类** | 未经协议 |

---

## 二、问题分析

### 问题 1：FetcherProtocol 是"超级接口"

```python
class FetcherProtocol(Protocol):
    def fetch(self, params: CollectParams) -> list[Any]:          # K线
    def fetch_stock_basic(self, params: CollectParams) -> list[Any]:  # 股票信息
    def fetch_daily_basic(self, trade_date: str) -> list[Any]:    # 日频估值
    @property
    def source_name(self) -> str:                                  # 数据源名称
```

**问题**：

- 三种完全不同的数据类型（日K线、股票信息、日频估值）的采集能力被塞进同一个协议
- `PytdxFetcher` 只提供分钟K线，无法也不应该实现 `fetch_stock_basic` / `fetch_daily_basic`，被迫游离在协议体系之外
- 后续新增 AKShare 采集器只需要采集概念板块，不需要日K/估值能力，同样无法实现完整协议
- 违反**接口隔离原则（ISP）**：调用方被迫依赖它不需要的方法

**影响**：

- `TushareFetcher` 是目前唯一实现完整协议的类，形成了事实上的"单点绑定"
- 无法按数据类型粒度切换数据源（如"日K用 Tushare，概念用 AKShare"）
- 新增数据源时必须实现所有方法，即使大部分抛 `NotImplementedError`

### 问题 2：工厂函数散落在路由层，硬编码数据源

**当前 5 处硬编码**：

```python
# route/api/v1/kline.py:35-36
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)

# route/api/v1/stock.py:36-38
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)

# route/api/v1/collect_task.py:28-29
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)

# route/api/v1/minute_kline.py:11,19
from infrastructure.collectors.pytdx.fetcher import PytdxFetcher
return PytdxFetcher()

# infrastructure/tasks/operation_dispatcher.py:62,82
from infrastructure.collectors.tushare.fetcher import TushareFetcher
fetcher = TushareFetcher(KlineBO)
```

**问题**：

- 切换数据源（如日K从 Tushare 改为 AKShare）需要修改至少 4 个文件
- 无法在运行时根据配置选择数据源（如根据积分余额自动降级）
- 路由层（presentation）耦合了基础设施层的具体实现类
- `_get_tushare_fetcher()` 每次调用都 `new` 实例，`get_kline_fetcher()` 则用 `@lru_cache` 缓存，行为不一致

### 问题 3：PytdxFetcher 游离在协议体系之外

**现状**：

```python
# PytdxFetcher 的核心方法
class PytdxFetcher(BaseCollector):
    async def fetch_minute_klines(self, symbol, interval, count, name) -> list[MinuteKlineBO]:
        ...
```

```python
# minute_kline.py 直接依赖具体类，不经协议
from infrastructure.collectors.pytdx.fetcher import PytdxFetcher
fetcher: PytdxFetcher = Depends(get_pytdx_fetcher)
```

**问题**：

- `PytdxFetcher` 继承了 `BaseCollector` 但没有实现任何协议
- 路由层直接类型注解为 `PytdxFetcher` 而非协议类型
- 如果后续要用其他数据源替代分钟K线（如 AKShare 的分钟数据），需要修改路由代码
- 与 `TushareFetcher` 走 `FetcherProtocol` 的模式不一致，新开发者容易困惑

---

## 三、影响范围

### 需要修改的文件清单（按重构方案）

| 文件 | 当前问题 | 涉及行 |
|------|---------|--------|
| `infrastructure/collectors/interfaces.py` | 超级接口，需拆分 | 全文 |
| `infrastructure/collectors/tushare/fetcher.py` | 需实现拆分后的多个小协议 | 类定义 |
| `infrastructure/collectors/pytdx/fetcher.py` | 需实现 MinuteKlineFetcher 协议 | 类定义 |
| `route/api/v1/kline.py` | 硬编码 TushareFetcher | L33-36 |
| `route/api/v1/stock.py` | 硬编码 TushareFetcher | L34-38 |
| `route/api/v1/collect_task.py` | 硬编码 _get_tushare_fetcher | L27-29, L246, L350, L405 |
| `route/api/v1/minute_kline.py` | 硬编码 PytdxFetcher | L11, L18-19, L38 |
| `infrastructure/tasks/operation_dispatcher.py` | 硬编码 TushareFetcher | L62, L82 |
| `application/kline_service.py` | 依赖 FetcherProtocol（需改为小协议） | L37, L71, L124 |
| `application/stock_service.py` | 依赖 FetcherProtocol（需改为小协议） | L34, L166 |

**新增文件**：

| 文件 | 用途 |
|------|------|
| `infrastructure/collectors/protocols.py` | 拆分后的多个小协议 |
| `infrastructure/collectors/registry.py` | 统一工厂/注册中心 |
| `infrastructure/collectors/akshare/` | AKShare 采集器（后续新增时） |
