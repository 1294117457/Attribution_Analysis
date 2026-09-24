# 采集器协议层问题分析

> 分析日期：2026-09-24
> 涉及目录：`backend/src/infrastructure/collectors/`

## 一、当前架构概览

```
infrastructure/collectors/
├── interfaces.py          ← FetcherProtocol（统一协议）+ CollectParams
├── base.py                ← BaseCollector（日志、错误处理基类）
├── tushare/
│   ├── fetcher.py        ← TushareFetcher（日K、股票信息、日频估值）
│   └── parser.py         ← TushareKlineParser
└── pytdx/
    ├── fetcher.py         ← PytdxFetcher（分钟K线，实时透传不落库）
    └── parser.py          ← PytdxKlineParser
```

### 当前数据流

```
Route 层（FastAPI Depends）
  → 各路由文件内的工厂函数（硬编码 TushareFetcher / PytdxFetcher）
    → Application Service（接收 FetcherProtocol）
      → 具体 Fetcher 实现（Tushare / Pytdx）
        → 返回领域 BO（KlineBO / StockInfoBO / FinDailyBasicBO / MinuteKlineBO）
```

### 工厂函数分布（5 处，散布在路由层）

| 工厂函数 | 位置 | 缓存策略 | 实际行为 |
|---------|------|---------|---------|
| `get_kline_fetcher()` | `route/api/v1/kline.py:33` | `@lru_cache`（单例） | 每次调用返回同一实例 |
| `get_stock_fetcher()` | `route/api/v1/stock.py:34` | `@lru_cache`（单例） | 每次调用返回同一实例 |
| `_get_tushare_fetcher()` | `route/api/v1/collect_task.py:27` | **无缓存**（每次 new） | 每只股票新建一个 TushareFetcher 实例 |
| `get_pytdx_fetcher()` | `route/api/v1/minute_kline.py:18` | `@lru_cache`（单例） | 每次调用返回同一实例 |
| **函数内直接实例化** | `infrastructure/tasks/operation_dispatcher.py:82` | 无缓存 | 后台任务中每只股票新建实例 |

> **⚠️ 特别说明**：第 4 处和第 5 处**无缓存**，在 `_collect_daily_kline` 的并发池场景（concurrency=10，每只股票新建）下，Tushare token 初始化 + `pro_api()` 会执行多次。注意 `ts.set_token()` 是全局调用，多次执行无副作用但会浪费初始化时间。

### 协议使用情况

| 消费方 | 依赖的类型 | 说明 |
|--------|----------|------|
| `kline_service.py` | `FetcherProtocol` | `collect()` / `collect_batch()` |
| `stock_service.py` | `FetcherProtocol` | `sync_stocks()` |
| `kline.py` 路由 | `FetcherProtocol` | Depends 注入（KlineFetcher 语义） |
| `stock.py` 路由 | `FetcherProtocol` | Depends 注入（StockBasicFetcher 语义） |
| `collect_task.py` 路由 | `FetcherProtocol` | 后台任务并发池 |
| `collect_task.py` 直接调用 | `FetcherProtocol` | `_collect_daily_basic` / `_collect_stock_basic` 内直接使用 `_get_tushare_fetcher()` |
| `operation_dispatcher.py` | **无协议注解** | 直接 `TushareFetcher(KlineBO)` |
| `minute_kline.py` 路由 | **直接依赖 `PytdxFetcher`** | 未经协议，且使用 `@lru_cache` |

### source_name 实际值（与文档假设不符）

| 类 | 实际 `source_name` | 文档假设值 |
|----|--------------------|-----------|
| `TushareFetcher` | `"Tushare"`（大写 T） | `"tushare"` |
| `PytdxFetcher` | `"Pytdx"`（大写 P） | `"pytdx"` |

---

## 二、问题分析

### 问题 1：FetcherProtocol 是"超级接口"（违反 ISP）

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

**当前 5 处硬编码（另有函数内直接实例化）**：

```python
# route/api/v1/kline.py:35-36
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)       # @lru_cache 单例

# route/api/v1/stock.py:36-38
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)       # @lru_cache 单例

# route/api/v1/collect_task.py:28-29
from infrastructure.collectors.tushare import TushareFetcher
return TushareFetcher(KlineBO)        # ⚠️ 无缓存，每次 new，且内部做 token 初始化

# route/api/v1/minute_kline.py:11,19
from infrastructure.collectors.pytdx.fetcher import PytdxFetcher
return PytdxFetcher()                 # @lru_cache 单例

# infrastructure/tasks/operation_dispatcher.py:62,82
from infrastructure.collectors.tushare.fetcher import TushareFetcher
fetcher = TushareFetcher(KlineBO)    # 函数内直接 new，无缓存，无协议
```

**问题**：

- 切换数据源（日K从 Tushare 改为 AKShare）需要修改至少 4 个文件
- 无法在运行时根据配置选择数据源（如根据积分余额自动降级）
- 路由层（presentation）耦合了基础设施层的具体实现类
- `_get_tushare_fetcher()` 无缓存导致并发任务中重复初始化 token

### 问题 3：PytdxFetcher 游离在协议体系之外

**现状**：

```python
# PytdxFetcher 的核心方法
class PytdxFetcher(BaseCollector):
    async def fetch_minute_klines(self, symbol, interval, count, name) -> list[MinuteKlineBO]:
        ...

    @property
    def source_name(self) -> str:
        return "Pytdx"   # 注意大写 P，文档曾误写为 "pytdx"
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
- 与 `TushareFetcher` 走 `FetcherProtocol` 的模式不一致

---

## 三、影响范围

### 需要修改的文件清单（按重构方案）

| 文件 | 当前问题 | 涉及行 |
|------|---------|--------|
| `infrastructure/collectors/interfaces.py` | 超级接口，需拆分 | 全文 |
| `infrastructure/collectors/protocols.py` | **新增**：拆分后的多个小协议 | 新增 |
| `infrastructure/collectors/registry.py` | **新增**：统一工厂/注册中心 | 新增 |
| `infrastructure/collectors/tushare/fetcher.py` | 确认实现各小协议（方法签名已满足） | 检查 |
| `infrastructure/collectors/pytdx/fetcher.py` | 确认实现 MinuteKlineFetcher（签名已满足）；`source_name` 大小写（实际为 "Pytdx"） | 检查 |
| `route/api/v1/kline.py` | 硬编码 TushareFetcher，类型注解改为 KlineFetcher | L33-36, L93, L109 |
| `route/api/v1/stock.py` | 硬编码 TushareFetcher，类型注解改为 StockBasicFetcher | L34-38 |
| `route/api/v1/collect_task.py` | 硬编码 `_get_tushare_fetcher`（无缓存，每次 new） | L27-29, L244, L340, L402 |
| `route/api/v1/minute_kline.py` | 硬编码 PytdxFetcher，类型注解改为 MinuteKlineFetcher | L11, L18-19, L38 |
| `infrastructure/tasks/operation_dispatcher.py` | 函数内直接 `TushareFetcher(KlineBO)`（无协议注解） | L62, L82 |
| `application/kline_service.py` | 依赖 FetcherProtocol → 改为 KlineFetcher | L37, L71, L124 |
| `application/stock_service.py` | 依赖 FetcherProtocol → 改为 StockBasicFetcher | L34, L166 |
| `main.py` | lifespan 中调用 `setup_default_registry()` | 新增 |

**新增文件**：

| 文件 | 用途 |
|------|------|
| `infrastructure/collectors/protocols.py` | 拆分后的多个小协议定义 |
| `infrastructure/collectors/registry.py` | 数据源注册中心（含 factory 方法和并发池支持） |
| `infrastructure/collectors/__init__.py` | 更新：导出协议和注册中心 |
| `backend/docs/dev/04protocol/03_akshare_extension.md` | AKShare 概念采集器扩展（从原 02 重构方案中拆分） |

---

## 四、测试现状

### 现有测试情况

- `tests/test_application.py`：使用 `MagicMock()` mock fetcher，不依赖具体协议类型
  - `service.collect(request, fetcher)` 中传入 `MagicMock()`，类型检查通过
  - 但服务方法签名写死为 `FetcherProtocol`，协议拆分后需同步更新签名

- `tests/test_api.py`：端到端测试，依赖具体类
- `tests/conftest.py`：标准 pytest 配置，添加了 `src` 到 `sys.path`

### 重构后测试影响

| 文件 | 重构影响 |
|------|---------|
| `test_application.py` | `MagicMock()` 仍可用，但 `collect(request, fetcher)` 签名需改为小协议 |
| `test_api.py` | 路由层的 Depends 工厂需 mock，返回满足协议的 mock 对象 |
| 新增 | 应新增协议单元测试：验证 `isinstance(Fetcher实例, KlineFetcher)` 等 |

详见重构方案中的「测试策略」章节。
