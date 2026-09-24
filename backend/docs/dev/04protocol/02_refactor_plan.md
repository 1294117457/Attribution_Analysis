# 采集器协议层重构方案

> 编写日期：2026-09-24
> 对应分析文档：[01_problem_analysis.md](./01_problem_analysis.md)

## 一、目标

1. **协议拆分**：将超级接口 `FetcherProtocol` 拆解为按数据类型划分的小协议，遵循接口隔离原则
2. **统一注册**：建立数据源注册中心，消除路由层的硬编码工厂函数
3. **纳入 PytdxFetcher**：让所有采集器都走协议体系，行为一致
4. **可扩展**：后续新增 AKShare 等数据源只需实现对应小协议并注册，无需改动上层代码

## 二、协议拆分

### 2.1 新协议定义

在 `infrastructure/collectors/protocols.py` 中定义：

```python
from typing import Protocol, runtime_checkable, Any
from infrastructure.collectors.interfaces import CollectParams


@runtime_checkable
class KlineFetcher(Protocol):
    """日K线采集"""
    def fetch(self, params: CollectParams) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class MinuteKlineFetcher(Protocol):
    """分钟K线采集"""
    async def fetch_minute_klines(
        self, symbol: str, interval: int, count: int, name: str
    ) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class StockBasicFetcher(Protocol):
    """股票基本信息采集"""
    def fetch_stock_basic(self, params: CollectParams) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class DailyBasicFetcher(Protocol):
    """日频估值指标采集"""
    def fetch_daily_basic(self, trade_date: str) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class ConceptFetcher(Protocol):
    """概念板块采集（预留，AKShare 实现）"""
    def fetch_concept_list(self) -> list[Any]: ...
    def fetch_concept_stocks(self, concept_name: str) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...
```

### 2.2 协议映射关系

| 原 `FetcherProtocol` 方法 | 新协议 | 实现者 |
|--------------------------|--------|--------|
| `fetch()` | `KlineFetcher` | TushareFetcher |
| `fetch_stock_basic()` | `StockBasicFetcher` | TushareFetcher |
| `fetch_daily_basic()` | `DailyBasicFetcher` | TushareFetcher |
| *(不在原协议)* `fetch_minute_klines()` | `MinuteKlineFetcher` | PytdxFetcher |
| *(新增)* | `ConceptFetcher` | AKShareFetcher（后续） |

### 2.3 向后兼容

旧 `FetcherProtocol` 暂时保留为类型别名，标记 `@deprecated`，给上层代码过渡期：

```python
# interfaces.py（过渡期保留）
import warnings

class FetcherProtocol(KlineFetcher, StockBasicFetcher, DailyBasicFetcher, Protocol):
    """@deprecated: 请使用拆分后的小协议"""
    pass
```

过渡完成后删除。

## 三、数据源注册中心

### 3.1 注册中心设计

在 `infrastructure/collectors/registry.py` 中实现：

```python
from __future__ import annotations
from typing import TypeVar, Type
from infrastructure.collectors.protocols import (
    KlineFetcher, MinuteKlineFetcher,
    StockBasicFetcher, DailyBasicFetcher,
    ConceptFetcher,
)

P = TypeVar("P")  # Protocol type

class FetcherRegistry:
    """数据源注册中心

    集中管理「数据类型 → 采集器实例」的映射关系。
    路由层通过 registry.get(KlineFetcher) 获取实例，
    不再需要知道具体实现类。
    """

    def __init__(self):
        self._providers: dict[type, object] = {}

    def register(self, protocol: type, instance: object) -> None:
        """注册采集器实例到指定协议"""
        if not isinstance(instance, protocol):
            raise TypeError(
                f"{type(instance).__name__} 未实现 {protocol.__name__}"
            )
        self._providers[protocol] = instance

    def get(self, protocol: Type[P]) -> P:
        """根据协议类型获取采集器"""
        if protocol not in self._providers:
            raise KeyError(f"未注册 {protocol.__name__} 的实现")
        return self._providers[protocol]  # type: ignore

    def has(self, protocol: type) -> bool:
        return protocol in self._providers


# 全局单例
_registry = FetcherRegistry()


def get_registry() -> FetcherRegistry:
    return _registry


def setup_default_registry() -> FetcherRegistry:
    """应用启动时调用，注册默认数据源

    在 main.py 的 lifespan 中调用。
    """
    from infrastructure.collectors.tushare.fetcher import TushareFetcher
    from infrastructure.collectors.pytdx.fetcher import PytdxFetcher
    from domain.kline.bo import KlineBO

    tushare = TushareFetcher(KlineBO)
    pytdx = PytdxFetcher()

    _registry.register(KlineFetcher, tushare)
    _registry.register(StockBasicFetcher, tushare)
    _registry.register(DailyBasicFetcher, tushare)
    _registry.register(MinuteKlineFetcher, pytdx)

    return _registry
```

### 3.2 注册中心使用

**路由层改造（以 `kline.py` 为例）**：

```python
# 改造前
def get_kline_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare import TushareFetcher
    return TushareFetcher(KlineBO)

@router.post("/collect")
async def collect_kline(
    fetcher: FetcherProtocol = Depends(get_kline_fetcher),
): ...

# 改造后
from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import KlineFetcher

def get_kline_fetcher() -> KlineFetcher:
    return get_registry().get(KlineFetcher)

@router.post("/collect")
async def collect_kline(
    fetcher: KlineFetcher = Depends(get_kline_fetcher),
): ...
```

**Application Service 改造（以 `kline_service.py` 为例）**：

```python
# 改造前
async def collect(self, request, fetcher: FetcherProtocol): ...

# 改造后
async def collect(self, request, fetcher: KlineFetcher): ...
```

### 3.3 应用启动注册

在 `main.py` 的 lifespan 事件中初始化：

```python
from contextlib import asynccontextmanager
from infrastructure.collectors.registry import setup_default_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_default_registry()
    yield

app = FastAPI(lifespan=lifespan)
```

## 四、PytdxFetcher 纳入协议

### 4.1 当前状态

```python
class PytdxFetcher(BaseCollector):
    async def fetch_minute_klines(self, symbol, interval, count, name):
        ...
    @property
    def source_name(self) -> str:
        return "pytdx"
```

已经有 `source_name` 属性和 `fetch_minute_klines` 方法，方法签名与新协议 `MinuteKlineFetcher` 一致。

### 4.2 改造内容

无需修改方法签名，Python 的结构化类型（Protocol）会自动匹配。只需确认：

1. `fetch_minute_klines` 的参数类型注解完整
2. `source_name` 有 `@property` 装饰器
3. 在注册中心注册为 `MinuteKlineFetcher`

### 4.3 路由层改造

```python
# 改造前（minute_kline.py）
from infrastructure.collectors.pytdx.fetcher import PytdxFetcher

def get_pytdx_fetcher() -> PytdxFetcher:
    return PytdxFetcher()

@router.get("/minute-klines/{symbol}")
async def get_minute_klines(
    fetcher: PytdxFetcher = Depends(get_pytdx_fetcher),
): ...

# 改造后
from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import MinuteKlineFetcher

def get_minute_kline_fetcher() -> MinuteKlineFetcher:
    return get_registry().get(MinuteKlineFetcher)

@router.get("/minute-klines/{symbol}")
async def get_minute_klines(
    fetcher: MinuteKlineFetcher = Depends(get_minute_kline_fetcher),
): ...
```

## 五、后续扩展：AKShare 概念采集器

### 5.1 目录结构

```
infrastructure/collectors/akshare/
├── __init__.py
├── fetcher.py      ← AKShareConceptFetcher
└── parser.py       ← 解析东方财富概念板块数据
```

### 5.2 实现示例

```python
class AKShareConceptFetcher(BaseCollector):
    """AKShare 概念板块采集器

    数据来源：东方财富（通过 AKShare 免费 API）
    """

    def fetch_concept_list(self) -> list[ConceptBO]:
        import akshare as ak
        df = ak.stock_board_concept_name_em()
        return ConceptParser.parse_list(df)

    def fetch_concept_stocks(self, concept_name: str) -> list[ConceptStockBO]:
        import akshare as ak
        df = ak.stock_board_concept_cons_em(symbol=concept_name)
        return ConceptParser.parse_stocks(df)

    @property
    def source_name(self) -> str:
        return "akshare"
```

### 5.3 注册

```python
def setup_default_registry():
    # ... 原有注册 ...
    from infrastructure.collectors.akshare.fetcher import AKShareConceptFetcher
    akshare = AKShareConceptFetcher()
    _registry.register(ConceptFetcher, akshare)
```

## 六、实施步骤

### 阶段 1：协议拆分 + 注册中心（不改变外部行为）

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 1.1 | 创建 `protocols.py`，定义 5 个小协议 | 新增 |
| 1.2 | 创建 `registry.py`，实现注册中心 | 新增 |
| 1.3 | `interfaces.py` 中旧 `FetcherProtocol` 改为联合继承 + deprecation 标记 | 修改 |
| 1.4 | `TushareFetcher` 确认实现 `KlineFetcher` + `StockBasicFetcher` + `DailyBasicFetcher`（方法签名已满足，无需改代码） | 检查 |
| 1.5 | `PytdxFetcher` 补全类型注解，确认满足 `MinuteKlineFetcher` | 微调 |
| 1.6 | `main.py` lifespan 中调用 `setup_default_registry()` | 修改 |

### 阶段 2：路由层改造（逐文件替换）

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 2.1 | `kline.py`：工厂函数改用 registry，类型注解改为 `KlineFetcher` | 修改 |
| 2.2 | `stock.py`：工厂函数改用 registry，类型注解改为 `StockBasicFetcher` | 修改 |
| 2.3 | `collect_task.py`：`_get_tushare_fetcher` 改用 registry | 修改 |
| 2.4 | `minute_kline.py`：工厂函数改用 registry，类型注解改为 `MinuteKlineFetcher` | 修改 |
| 2.5 | `operation_dispatcher.py`：直接实例化改为从 registry 获取 | 修改 |

### 阶段 3：Application Service 改造

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 3.1 | `kline_service.py`：`FetcherProtocol` → `KlineFetcher` | 修改 |
| 3.2 | `stock_service.py`：`FetcherProtocol` → `StockBasicFetcher` | 修改 |

### 阶段 4：清理 + AKShare 扩展

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 4.1 | 删除旧 `FetcherProtocol` 及所有旧导入 | `interfaces.py` |
| 4.2 | 新增 `akshare/` 目录，实现 `ConceptFetcher` | 新增 |
| 4.3 | 注册 `ConceptFetcher` 到 registry | `registry.py` |

## 七、重构前后对比

### 对比总览

| 维度 | 重构前 | 重构后 |
|------|-------|--------|
| 接口粒度 | 1 个超级接口 | 5 个职责单一的小协议 |
| 数据源绑定 | 4+ 处硬编码 `TushareFetcher` | 仅 `registry.py` 内绑定 |
| PytdxFetcher | 游离在协议外 | 实现 `MinuteKlineFetcher` |
| 切换数据源 | 改 4-5 个文件 | 改 `registry.py` 一处 |
| 新增数据源 | 必须实现全部方法 | 只实现对应小协议 |
| 运行时切换 | 不支持 | registry 支持动态替换 |

### 依赖方向

```
改造前：
  Route → 具体类 (TushareFetcher/PytdxFetcher)
  Service → 超级协议 (FetcherProtocol)

改造后：
  Route → Registry → 小协议 (KlineFetcher, MinuteKlineFetcher, ...)
  Service → 小协议
  具体类 → 实现小协议（结构化类型匹配，无需显式继承）
```

## 八、注意事项

1. **`collect_task.py` 的 fetcher pool**：当前用 `asyncio.Queue[FetcherProtocol]` 管理并发实例池，重构后需改为 `asyncio.Queue[KlineFetcher]`，注册中心需要支持「创建新实例」而非只返回单例（或 pool 逻辑保留在路由层，从 registry 获取工厂函数而非实例）
2. **`@lru_cache` 缓存问题**：部分工厂函数用了 `@lru_cache`，改用 registry 后自然解决（registry 内部持有实例）
3. **线程安全**：`TushareFetcher` 内部使用 `tushare.pro_api()` 基于 `requests.Session`，并发场景仍需 pool 模式，registry 应提供 `create()` 方法或单独的 pool 管理
4. **Python Protocol 的结构化类型**：无需 `class TushareFetcher(KlineFetcher)`，只要方法签名匹配即可，但建议显式继承以获得 IDE 检查支持
