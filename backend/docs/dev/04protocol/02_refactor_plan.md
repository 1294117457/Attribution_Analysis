# 采集器协议层重构方案

> 编写日期：2026-09-24
> 对应分析文档：[01_problem_analysis.md](./01_problem_analysis.md)
>
> **⚠️ 本文档对 v1 草稿做了以下重大修正**：
> - 过渡期 `FetcherProtocol` 不再用联合继承（会踢出 PytdxFetcher），改为显式重写方法签名
> - 注册中心不只暴露单例 `get()`，同时暴露 `create()` 工厂方法以支持 `collect_task.py` 并发池场景
> - 新增签名校验逻辑（`inspect.signature`），填补 `@runtime_checkable` 只检查方法存在性、不检查参数列表的盲区
> - 拆出 AKShare 扩展到 [03_akshare_extension.md](./03_akshare_extension.md)

---

## 一、目标

1. **协议拆分**：将超级接口 `FetcherProtocol` 拆解为按数据类型划分的小协议，遵循接口隔离原则
2. **统一注册**：建立数据源注册中心，消除路由层的硬编码工厂函数
3. **纳入 PytdxFetcher**：让所有采集器都走协议体系，行为一致
4. **并发安全**：注册中心同时支持单例查询和并发池工厂两种模式
5. **可扩展**：后续新增 AKShare 等数据源只需实现对应小协议并注册，无需改动上层代码

---

## 二、协议拆分

### 2.1 新协议定义

在 `infrastructure/collectors/protocols.py` 中定义：

```python
"""采集器协议（按数据类型拆分）

协议放置在 infrastructure 层是务实选择：
- 消费方（application / route）依赖协议
- 实现方（infrastructure/collectors/*）实现协议
- 不追求严格 DDD 的"由消费方定义接口"，以避免循环依赖
"""

from __future__ import annotations

import inspect
from typing import (
    TYPE_CHECKING,
    Protocol,
    TypeVar,
    runtime_checkable,
    Any,
)

from infrastructure.collectors.interfaces import CollectParams

P = TypeVar("P", bound=Protocol)


# ════════════════════════════════════════════════════════
# 协议定义
# ════════════════════════════════════════════════════════

@runtime_checkable
class KlineFetcher(Protocol):
    """日K线采集"""
    def fetch(self, params: CollectParams) -> list[Any]: ...
    """采集 K 线，返回 KlineBO 列表"""

    @property
    def source_name(self) -> str: ...
    """数据源名称，如 'Tushare'"""


@runtime_checkable
class MinuteKlineFetcher(Protocol):
    """分钟K线采集"""
    async def fetch_minute_klines(
        self, symbol: str, interval: str, count: int, name: str,
    ) -> list[Any]: ...
    """异步采集分钟 K 线，返回 MinuteKlineBO 列表

    注意：参数 `name` 有默认值（''），实现类的签名必须兼容此默认值
    """

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class StockBasicFetcher(Protocol):
    """股票基本信息采集"""
    def fetch_stock_basic(self, params: CollectParams) -> list[Any]: ...
    """采集股票基本信息，返回 StockInfoBO 列表"""

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class DailyBasicFetcher(Protocol):
    """日频估值指标采集"""
    def fetch_daily_basic(self, trade_date: str) -> list[Any]: ...
    """采集日频估值，返回 FinDailyBasicBO 列表

    Args:
        trade_date: YYYYMMDD 格式日期
    """

    @property
    def source_name(self) -> str: ...


@runtime_checkable
class ConceptFetcher(Protocol):
    """概念板块采集（预留，AKShare 实现）"""
    def fetch_concept_list(self) -> list[Any]: ...
    def fetch_concept_stocks(self, concept_name: str) -> list[Any]: ...

    @property
    def source_name(self) -> str: ...


# ════════════════════════════════════════════════════════
# 签名校验工具（补充 @runtime_checkable 的盲区）
# ════════════════════════════════════════════════════════

def _check_protocol_signature(
    instance: object,
    protocol: type[Protocol],
    method_name: str,
) -> None:
    """比对实例方法与协议方法的参数签名

    @runtime_checkable 只检查方法是否存在，不检查签名。
    本函数检查关键方法的参数列表，防止注册时放行签名不兼容的实现。
    """
    proto_method = getattr(protocol, method_name, None)
    instance_method = getattr(instance, method_name, None)

    if proto_method is None or instance_method is None:
        return  # 方法不存在时不报错，由 @runtime_checkable 兜底

    proto_sig = inspect.signature(proto_method)
    try:
        instance_sig = inspect.signature(instance_method)
    except (ValueError, TypeError):
        # 内置方法或无法反射时跳过
        return

    proto_params = list(proto_sig.parameters.keys())
    instance_params = list(instance_sig.parameters.keys())

    # 忽略 self（协议定义不含 self，实现含 self），对齐后再比较
    if proto_params and proto_params[0] in ("self", "cls"):
        proto_params = proto_params[1:]
    if instance_params and instance_params[0] in ("self", "cls"):
        instance_params = instance_params[1:]

    if proto_params != instance_params:
        raise TypeError(
            f"{type(instance).__name__}.{method_name} 参数列表 {instance_params} "
            f"与协议 {protocol.__name__}.{method_name} 要求 {proto_params} 不匹配"
        )


def validate_protocol_implementation(
    instance: object,
    protocol: type[P],
) -> None:
    """校验实例是否完整实现了给定协议的所有方法签名

    在 registry.register() 内部调用，也可在测试中单独使用。
    """
    for attr_name in dir(protocol):
        if attr_name.startswith("_"):
            continue
        attr = getattr(protocol, attr_name)
        if callable(attr) or isinstance(attr, property):
            _check_protocol_signature(instance, protocol, attr_name)
```

### 2.2 协议映射关系

| 原 `FetcherProtocol` 方法 | 新协议 | 实现者 | source_name 实际值 |
|--------------------------|--------|--------|-----------------|
| `fetch()` | `KlineFetcher` | TushareFetcher | `"Tushare"` |
| `fetch_stock_basic()` | `StockBasicFetcher` | TushareFetcher | `"Tushare"` |
| `fetch_daily_basic()` | `DailyBasicFetcher` | TushareFetcher | `"Tushare"` |
| *(不在原协议)* `fetch_minute_klines()` | `MinuteKlineFetcher` | PytdxFetcher | `"Pytdx"` |
| *(新增)* | `ConceptFetcher` | AKShareFetcher（后续） | `"akshare"` |

### 2.3 过渡期 FetcherProtocol 处理（不使用联合继承）

原 `interfaces.py` 中的 `FetcherProtocol` 改为过渡态，**不使用联合继承**：

```python
# interfaces.py（过渡态保留，标注 @deprecated）
import warnings
import inspect
from typing import Any

class FetcherProtocol:
    """⚠️ 已废弃：请使用拆分后的各小协议

    本类不再继承 Protocol，直接重写方法签名。
    不使用「KlineFetcher + StockBasicFetcher + DailyBasicFetcher 联合继承」——
    那样会使只实现了部分能力的 PytdxFetcher 通过 isinstance，但实际调用会失败，
    造成类型系统与运行时行为不一致。
    """

    @classmethod
    def __init_subclass__(cls) -> None:
        warnings.warn(
            f"子类 {cls.__name__} 继承了废弃的 FetcherProtocol，"
            "请改用 KlineFetcher / MinuteKlineFetcher / StockBasicFetcher 等小协议",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init_subclass__()

    def fetch(self, params: Any) -> list[Any]:
        raise NotImplementedError

    def fetch_stock_basic(self, params: Any) -> list[Any]:
        raise NotImplementedError

    def fetch_daily_basic(self, trade_date: str) -> list[Any]:
        raise NotImplementedError

    @property
    def source_name(self) -> str:
        raise NotImplementedError
```

> **说明**：过渡态 `FetcherProtocol` 只作为**向后兼容的类型别名**使用。上层代码（route / service）在重构期间保持现有签名，完成后删除此类。

---

## 三、数据源注册中心

### 3.1 设计目标

注册中心需同时满足两类场景：

1. **FastAPI 路由层单例注入**（`get_kline_fetcher()` → `Depends(get_registry().get(KlineFetcher))`）
2. **后台任务并发池**（`collect_task.py` 中的 `asyncio.Queue[KlineFetcher]`，每个 worker 取/放实例）

为支持场景 2，Registry 提供：
- `get(Protocol)` — 获取已注册的**共享实例**（单例，供路由层使用）
- `create(Protocol)` — 创建**新实例**（供并发任务池使用，避免共享同一 TCP 连接）

### 3.2 注册中心实现

```python
# infrastructure/collectors/registry.py
"""
数据源注册中心

设计约束：
- 启动期（lifespan）一次性注册，运行期只读——因此不需要写锁
- create() 返回工厂函数而非实例，由调用方决定何时创建
- 对外暴露的数据结构仅为 Protocol → instance / factory 的映射，不暴露具体类名
"""

from __future__ import annotations

import threading
from typing import Callable, TypeVar, Type, Any

from infrastructure.collectors.protocols import (
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
    DailyBasicFetcher,
    ConceptFetcher,
    validate_protocol_implementation,
)

P = TypeVar("P")


class FetcherRegistry:
    """数据源注册中心

    集中管理「协议类型 → 采集器实例/工厂」的映射关系。
    """

    def __init__(self) -> None:
        # _providers: Protocol type → singleton instance
        self._providers: dict[type, object] = {}
        # _factories: Protocol type → factory callable
        self._factories: dict[type, Callable[[], object]] = {}
        self._lock = threading.Lock()

    # ── 注册（启动期调用）─────────────────────────────────

    def register_instance(self, protocol: type[P], instance: P) -> None:
        """注册单例实例（适用于无状态或内部已做池化的采集器）

        Args:
            protocol: 协议类型（如 KlineFetcher）
            instance: 满足该协议的具体实例
        """
        validate_protocol_implementation(instance, protocol)
        with self._lock:
            self._providers[protocol] = instance

    def register_factory(self, protocol: type[P], factory: Callable[[], P]) -> None:
        """注册工厂函数（适用于有状态或需并发隔离的采集器）

        Args:
            protocol: 协议类型
            factory: 返回满足协议的实例的可调用对象（无参数）
        """
        with self._lock:
            self._factories[protocol] = factory

    # ── 查询（运行期调用）─────────────────────────────────

    def get(self, protocol: type[P]) -> P:
        """获取已注册的单例实例

        Raises:
            KeyError: 未注册该协议的实现
        """
        if protocol not in self._providers:
            raise KeyError(f"未注册 {protocol.__name__} 的单例实例，请检查 setup_default_registry()")
        return self._providers[protocol]  # type: ignore[return-value]

    def create(self, protocol: type[P]) -> P:
        """创建新实例（供并发池使用）

        必须先调用 register_factory() 注册工厂，否则报错。

        Raises:
            KeyError: 未注册该协议的工厂
        """
        if protocol not in self._factories:
            # 降级：从 providers 取单例（要求实现类无状态或内部已做池化）
            if protocol in self._providers:
                return self._providers[protocol]  # type: ignore[return-value]
            raise KeyError(f"未注册 {protocol.__name__} 的工厂，请检查 setup_default_registry()")
        return self._factories[protocol]()  # type: ignore[return-value]

    def has(self, protocol: type) -> bool:
        """查询某协议是否已注册（单例或工厂）"""
        return protocol in self._providers or protocol in self._factories

    def __repr__(self) -> str:
        return (
            f"FetcherRegistry("
            f"providers={list(self._providers.keys())}, "
            f"factories={list(self._factories.keys())})"
        )


# ── 全局注册中心（模块单例）─────────────────────────────────

_registry: FetcherRegistry | None = None


def get_registry() -> FetcherRegistry:
    """获取全局注册中心（延迟初始化）"""
    global _registry
    if _registry is None:
        _registry = FetcherRegistry()
    return _registry


def setup_default_registry() -> FetcherRegistry:
    """应用启动时调用：注册默认数据源

    在 main.py 的 lifespan 中调用。
    注册策略说明：
    - TushareFetcher：无状态（内部持有一个 pro_api 实例，requests.Session 线程安全），
      适合单例注册；但在 collect_task.py 的高并发池场景下，每次 get() 会拿到同一实例，
      若 Tushare 有连接数限制应改用 register_factory()
    - PytdxFetcher：内部维护 TCP 连接（有状态），适合 register_factory() 每次创建新连接；
      但分钟K线是透传不落库、QPS 低，用 register_instance() 单例也可接受

    调用示例（main.py lifespan）：
        from infrastructure.collectors.registry import setup_default_registry
        setup_default_registry()
    """
    reg = get_registry()

    # ── KlineFetcher ─────────────────────────────────────
    # 路由层单例（低并发）
    from infrastructure.collectors.tushare import TushareFetcher
    from domain.kline.schemas import KlineBO
    tushare_singleton = TushareFetcher(KlineBO)
    reg.register_instance(KlineFetcher, tushare_singleton)

    # 后台并发池工厂（高并发，每 worker 新实例）
    # 当前 TushareFetcher 内部 pro_api 线程安全，单例够用；
    # 若后续出现连接数瓶颈，改为 factory 模式
    reg.register_factory(KlineFetcher, lambda: TushareFetcher(KlineBO))

    # ── StockBasicFetcher ─────────────────────────────────
    # 与 KlineFetcher 共用同一 TushareFetcher 实例（source_name = "Tushare"）
    reg.register_instance(StockBasicFetcher, tushare_singleton)
    reg.register_factory(StockBasicFetcher, lambda: TushareFetcher(KlineBO))

    # ── DailyBasicFetcher ─────────────────────────────────
    reg.register_instance(DailyBasicFetcher, tushare_singleton)
    reg.register_factory(DailyBasicFetcher, lambda: TushareFetcher(KlineBO))

    # ── MinuteKlineFetcher ────────────────────────────────
    # PytdxFetcher 有状态（维护 TCP 连接），单例复用连接
    from infrastructure.collectors.pytdx import PytdxFetcher
    pytdx_fetcher = PytdxFetcher()
    reg.register_instance(MinuteKlineFetcher, pytdx_fetcher)
    # 若未来需要并发隔离分钟K线采集，可注册 factory：
    # reg.register_factory(MinuteKlineFetcher, PytdxFetcher)

    return reg
```

### 3.3 工厂函数改造（路由层）

改造后，路由层不再 import 具体类，只依赖协议类型：

```python
# route/api/v1/kline.py（改造后）

# ── 改造前 ────────────────────────────────────────────────
# from infrastructure.collectors.tushare import TushareFetcher  # ❌ 具体类
# @lru_cache
# def get_kline_fetcher() -> FetcherProtocol:
#     return TushareFetcher(KlineBO)

# ── 改造后 ────────────────────────────────────────────────
from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import KlineFetcher

@lru_cache
def get_kline_fetcher() -> KlineFetcher:
    """K 线采集器依赖（单例）"""
    return get_registry().get(KlineFetcher)

@router.post("/collect", summary="采集K线")
async def collect_kline(
    request: KlineCollectRequest,
    service: KlineAppService = Depends(get_kline_service),
    fetcher: KlineFetcher = Depends(get_kline_fetcher),   # ← 改为小协议类型
):
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())
```

```python
# route/api/v1/minute_kline.py（改造后）

from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import MinuteKlineFetcher

@lru_cache
def get_minute_kline_fetcher() -> MinuteKlineFetcher:
    return get_registry().get(MinuteKlineFetcher)

@router.get("/{symbol}", summary="实时获取分钟K线")
async def get_minute_klines(
    symbol: str,
    interval: str = Query("5min"),
    count: int = Query(200, ge=1, le=1200),
    fetcher: MinuteKlineFetcher = Depends(get_minute_kline_fetcher),
):
    # ... 逻辑不变 ...
```

### 3.4 后台任务改造（并发池）

```python
# route/api/v1/collect_task.py（改造后）
# _collect_daily_kline 中的 fetcher pool 改用 registry.create()

from infrastructure.collectors.registry import get_registry
from infrastructure.collectors.protocols import KlineFetcher

async def _collect_daily_kline(task_id: int, params: dict):
    # ...
    concurrency = max(1, min(int(user_conc), max_conc))

    # 改造前：asyncio.Queue[FetcherProtocol]
    # 改造后：改用 registry.create() + registry.get() 双模式
    fetcher_pool: asyncio.Queue[KlineFetcher] = asyncio.Queue()

    # 注册中心已注册 factory，每次 create() 返回新实例
    for _ in range(concurrency):
        fetcher_pool.put_nowait(get_registry().create(KlineFetcher))

    # worker 内从 pool 取实例，完成后归还
    async def _collect_one(symbol: str) -> bool:
        fetcher = await fetcher_pool.get()
        try:
            async with AsyncSessionLocal() as session:
                svc = KlineAppService(session=session)
                await asyncio.wait_for(
                    svc.collect(
                        KlineCollectRequest(symbol=symbol, **collect_kwargs),
                        fetcher,
                    ),
                    timeout=WORKER_TIMEOUT,
                )
                await session.commit()
        finally:
            await fetcher_pool.put(fetcher)
        # ...
```

### 3.5 Application Service 改造

```python
# application/kline_service.py（改造后）

# 改造前
# async def collect(self, request, fetcher: FetcherProtocol):

# 改造后
from infrastructure.collectors.protocols import KlineFetcher

class KlineAppService:
    async def collect(
        self,
        request: KlineCollectRequest,
        fetcher: KlineFetcher,     # ← 小协议类型
    ) -> KlineCollectResponse:
        # ...

    async def collect_batch(
        self,
        symbols: list[str],
        days: int,
        fetcher: KlineFetcher,
    ) -> dict[str, KlineCollectResponse]:
        # ...
```

```python
# application/stock_service.py（改造后）

from infrastructure.collectors.protocols import StockBasicFetcher

class StockAppService:
    async def sync_stocks(
        self,
        fetcher: StockBasicFetcher,   # ← 小协议类型
        list_status: str = "L",
    ) -> SyncStockResponse:
        # ...
```

### 3.6 应用启动注册

```python
# main.py（改造后）

from contextlib import asynccontextmanager
from infrastructure.collectors.registry import setup_default_registry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... 原有迁移逻辑 ...
    async with async_engine.begin() as conn:
        await _migrate_rename_kline_table(conn)
        await conn.run_sync(Base.metadata.create_all)
        await _migrate_stock_infos(conn)
        await _migrate_daily_klines_indicators(conn)
        await _ensure_default_pool(conn)

    # ← 新增：注册数据源
    setup_default_registry()

    yield
    await close_db()
```

---

## 四、PytdxFetcher 纳入协议

### 4.1 当前状态验证

```python
# PytdxFetcher 已有方法签名（无需修改）：
class PytdxFetcher(BaseCollector):
    @property
    def source_name(self) -> str:
        return "Pytdx"  # ⚠️ 注意大写 P，文档早期误写为 "pytdx"

    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",   # ⚠️ 有默认值！
        count: int = 800,          # ⚠️ 有默认值！
        name: str = "",            # ⚠️ 有默认值！
    ) -> list[MinuteKlineBO]:
        ...
```

### 4.2 签名校验注意事项

`MinuteKlineFetcher` 协议中 `fetch_minute_klines` 的参数签名：

```python
async def fetch_minute_klines(
    self, symbol: str, interval: str, count: int, name: str,
) -> list[Any]: ...
```

但 `PytdxFetcher.fetch_minute_klines` 实际参数有默认值：

```python
async def fetch_minute_klines(
    self,
    symbol: str,
    interval: str = "5min",   # 默认值
    count: int = 800,           # 默认值
    name: str = "",             # 默认值
) -> list[MinuteKlineBO]:
```

**签名不严格一致（默认值差异），但 Python 调用时兼容**。`inspect.signature` 比对参数列表时，这会被标记为不匹配。

**解决方案**：在 `_check_protocol_signature` 中增加"默认值宽松模式"检查，或在协议中使用默认值：

```python
# protocols.py 中的 MinuteKlineFetcher（修正版，兼容 PytdxFetcher 实际签名）
@runtime_checkable
class MinuteKlineFetcher(Protocol):
    async def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = "5min",
        count: int = 800,
        name: str = "",
    ) -> list[Any]: ...
```

这样 `inspect.signature` 就会同时比对默认值，PytdxFetcher 完全匹配。

---

## 五、实施步骤

### 阶段 1：基础设施（协议 + 注册中心）

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 1.1 | 创建 `protocols.py`，定义 5 个小协议（含默认值兼容 PytdxFetcher） | 新增 |
| 1.2 | 创建 `registry.py`，实现注册中心（含 factory + instance 双模式） | 新增 |
| 1.3 | `interfaces.py`：旧 `FetcherProtocol` 改为过渡态（显式重写，不联合继承） | 修改 |
| 1.4 | `TushareFetcher`：确认满足 `KlineFetcher` + `StockBasicFetcher` + `DailyBasicFetcher`（方法签名已满足） | 检查 |
| 1.5 | `PytdxFetcher`：`source_name` 确认返回 `"Pytdx"`（已有，无需修改）；补充参数默认值 | 检查 |
| 1.6 | `main.py` lifespan 中调用 `setup_default_registry()` | 修改 |

### 阶段 2：Application Service（协议拆分，无外部行为变化）

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 2.1 | `kline_service.py`：类型注解 `FetcherProtocol` → `KlineFetcher` | 修改 |
| 2.2 | `stock_service.py`：类型注解 `FetcherProtocol` → `StockBasicFetcher` | 修改 |

### 阶段 3：路由层改造（逐文件替换）

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 3.1 | `kline.py`：工厂函数改用 registry，类型注解改为 `KlineFetcher` | 修改 |
| 3.2 | `stock.py`：工厂函数改用 registry，类型注解改为 `StockBasicFetcher` | 修改 |
| 3.3 | `collect_task.py`：`_get_tushare_fetcher` 改用 registry；`asyncio.Queue[FetcherProtocol]` → `asyncio.Queue[KlineFetcher]`；用 `get_registry().create()` 填充池 | 修改 |
| 3.4 | `minute_kline.py`：工厂函数改用 registry，类型注解改为 `MinuteKlineFetcher` | 修改 |
| 3.5 | `operation_dispatcher.py`：直接实例化改为从 registry.get() 获取 | 修改 |

### 阶段 4：清理

| 步骤 | 操作 | 影响文件 |
|------|------|---------|
| 4.1 | 删除 `interfaces.py` 中的旧 `FetcherProtocol` | 修改 |
| 4.2 | 删除所有 `from infrastructure.collectors.interfaces import FetcherProtocol` 导入 | 全局搜索替换 |

---

## 六、重构前后对比

### 对比总览

| 维度 | 重构前 | 重构后 |
|------|-------|--------|
| 接口粒度 | 1 个超级接口 | 5 个职责单一的小协议 |
| 数据源绑定 | 5 处硬编码 `TushareFetcher` | 仅 `registry.py` 内绑定 |
| PytdxFetcher | 游离在协议外 | 实现 `MinuteKlineFetcher` |
| 切换数据源 | 改 4-5 个文件 | 改 `registry.py` 一处 |
| 新增数据源 | 必须实现全部方法 | 只实现对应小协议 |
| 运行时切换 | 不支持 | registry 支持按 Protocol 获取不同实例 |
| 并发池支持 | `asyncio.Queue[无协议]` | `asyncio.Queue[KlineFetcher]` + `registry.create()` |

### 依赖方向

```
改造前：
  Route → 具体类 (TushareFetcher / PytdxFetcher)
  Service → 超级协议 (FetcherProtocol)

改造后：
  Route → Registry → 小协议 (KlineFetcher, MinuteKlineFetcher, ...)
  Service → 小协议
  具体类 → 实现小协议（结构化类型匹配，无需显式继承）
```

---

## 七、测试策略

### 7.1 协议实现的结构化类型检查

```python
# tests/test_protocols.py

import pytest
from infrastructure.collectors.tushare import TushareFetcher
from infrastructure.collectors.pytdx import PytdxFetcher
from infrastructure.collectors.protocols import (
    KlineFetcher,
    MinuteKlineFetcher,
    StockBasicFetcher,
    DailyBasicFetcher,
)
from domain.kline.schemas import KlineBO

def test_tushare_fetcher_implements_all_protocols():
    fetcher = TushareFetcher(KlineBO)
    assert isinstance(fetcher, KlineFetcher)
    assert isinstance(fetcher, StockBasicFetcher)
    assert isinstance(fetcher, DailyBasicFetcher)

def test_pytdx_fetcher_implements_minute_protocol():
    fetcher = PytdxFetcher()
    assert isinstance(fetcher, MinuteKlineFetcher)

def test_pytdx_does_not_implement_other_protocols():
    """PytdxFetcher 只实现 MinuteKlineFetcher，不应满足其他协议"""
    fetcher = PytdxFetcher()
    assert not isinstance(fetcher, KlineFetcher)
    assert not isinstance(fetcher, StockBasicFetcher)
```

### 7.2 Service 层 mock（协议拆分后）

```python
# tests/test_application.py（改造后）

from infrastructure.collectors.protocols import KlineFetcher

class TestKlineAppService:
    @pytest.mark.asyncio
    async def test_collect_success(self):
        service = self._make_service()
        # MagicMock 自动满足任何 Protocol（Python duck typing）
        fetcher: KlineFetcher = MagicMock(spec=KlineFetcher)  # ← 显式 spec
        fetcher.fetch.return_value = [make_kline_bo(day=1), make_kline_bo(day=2)]
        # ...
```

> 注意：`MagicMock(spec=KlineFetcher)` 限制 mock 只实现协议中定义的方法，防止意外添加协议外方法。

### 7.3 路由层端到端测试

```python
# tests/test_api.py（改造后）

from infrastructure.collectors.protocols import KlineFetcher

class TestKlineAPI:
    @pytest.mark.asyncio
    async def test_collect_endpoint(self, client):
        mock_fetcher: KlineFetcher = MagicMock(spec=KlineFetcher)
        mock_fetcher.fetch.return_value = [make_kline_bo()]

        # 覆盖 Depends 中的工厂函数
        app.dependency_overrides[get_kline_fetcher] = lambda: mock_fetcher

        response = client.post("/api/v1/klines/collect", json={...})
        assert response.status_code == 201
```

---

## 八、错误处理与状态码约定

### 8.1 异常传播链路

```
数据源异常（RuntimeError）
  ↓ TushareFetcher._wrap_error()
RuntimeError(source="Tushare", message="...")
  ↓ KlineService.collect() 的 try/except
CollectionError(symbol, str(e))
  ↓ FastAPI exception_handler（main.py）
JSONResponse(status_code=502, message="Tushare: 调用 Tushare daily() 失败...")
```

### 8.2 注册中心异常映射

| 场景 | 抛出的异常 | HTTP 状态码 | 原因 |
|------|----------|------------|------|
| `registry.get()` 未注册 | `KeyError` | 503 Service Unavailable | 数据源未在 lifespan 中注册（配置错误） |
| `registry.create()` 未注册 | `KeyError` | 503 Service Unavailable | 同上，且没有降级单例可用 |
| 数据源 API 调用失败 | `RuntimeError` | 502 Bad Gateway | Tushare token 无效 / 网络问题 / 积分不足 |
| Pytdx 连接失败 | `RuntimeError("Pytdx: ...") | 502 Bad Gateway | 通达信服务器不可达 |

```python
# main.py 中的异常处理（改造后保持不变，但 KeyError 需要新增）

@app.exception_handler(KeyError)
async def registry_not_found(request: Request, exc: KeyError):
    """注册中心未找到对应的协议实现（通常是启动配置缺失）"""
    logging.error("数据源未注册: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"code": 503, "message": f"数据源未配置: {exc}", "data": None},
    )
```

### 8.3 采集任务中的错误处理

```python
# collect_task.py _collect_daily_kline 中的错误处理已存在
# 重构后保持不变：
except asyncio.TimeoutError:
    # → 记录 warning，不影响任务继续
    fail += 1
except Exception as e:
    # → 记录 warning，不影响任务继续
    fail += 1
```

> 注意：这里的错误处理策略是**不重试、不取消任务**，单只股票失败不影响整批。这是合理的设计，因为可能是那只股票本身的问题（如停牌）。

---

## 九、并发安全规范

### 9.1 注册中心的线程安全

`_registry` 是模块级变量，`_lock = threading.Lock()` 保护写操作。读操作（`get()` / `has()`）在 CPython 下受 GIL 保护，可以并发。

约束：**启动期一次性注册，运行期只读**。如果运行期需要动态注册/注销，需要引入读锁保护。

### 9.2 TushareFetcher 的并发安全

`TushareFetcher` 内部持有 `ts.pro_api()` 返回的 API 对象。该对象基于 `requests.Session`，在单进程多协程场景下**线程安全**。

但注意以下边界：
- `ts.set_token()` 是全局调用，多次调用无副作用
- `collect_task.py` 并发场景下每个 worker 有独立 `AsyncSession`，DB 事务互不影响
- 若 Tushare 对同一 token 有 QPS 限制，需在 registry 中加入限流（可后续扩展，不在本方案范围内）

### 9.3 PytdxFetcher 的并发安全

`PytdxFetcher` 内部维护 TCP 连接（`TdxHq_API`）。该连接**不是线程安全的**，因此：
- 当前 `@lru_cache` 单例模式：所有请求共用同一 TCP 连接，在并发请求下会冲突
- **建议**：在 `setup_default_registry()` 中使用 `register_factory()` 而非 `register_instance()`，每次从 pool 取新连接

```python
# setup_default_registry() 中的 PytdxFetcher 注册策略（建议）
reg.register_factory(MinuteKlineFetcher, PytdxFetcher)  # 每次 create() 新建连接

# minute_kline.py 路由层仍然用单例（低 QPS）：
# @lru_cache
# def get_minute_kline_fetcher() -> MinuteKlineFetcher:
#     return get_registry().get(MinuteKlineFetcher)
```

> 权衡：工厂模式会增加连接开销，分钟K线是透传接口 QPS 低，单例够用；若未来高并发，改用 factory。

---

## 十、注意事项

1. **`collect_task.py` 的 `@lru_cache` vs 无缓存**：当前 `_get_tushare_fetcher()` 无缓存，每次 new 一个 TushareFetcher；路由层的 `get_kline_fetcher()` 和 `get_stock_fetcher()` 有 `@lru_cache` 单例。重构后统一由 registry 管理，registry 内部决定单例还是工厂。
2. **`@runtime_checkable` 局限性**：Protocol 用 `@runtime_checkable` 装饰后支持 `isinstance` 检查，但**只检查方法存在性，不检查签名**。本方案在 `register()` 中额外加了 `inspect.signature` 校验，填补这一盲区。
3. **Python Protocol 的结构化类型**：实现类无需显式继承协议，只要方法签名匹配即可。但建议显式继承以获得 IDE 检查支持。
4. **旧 `FetcherProtocol` 的删除时机**：在所有 route / service 都迁移到小协议后，删除 `interfaces.py` 中的旧定义。过渡期间旧代码仍可用，不阻塞提交。
5. **`collect_task.py` 的 `fetcher_pool` 类型注解**：改造后 `asyncio.Queue[FetcherProtocol]` → `asyncio.Queue[KlineFetcher]`，这样类型检查器能确认 pool 中的对象支持 `fetch()` 方法。
