# 02 · 去掉 `collect_data_ports` 表 + 去掉 `DataGateway`

> 目标：本次合并**做 2 件事**——(1) `collect_data_ports` 表从 DB 移到内存，catalog 走 `_collect_registry`；(2) **去掉 `DataGateway`**——5 装饰器链（`CacheDecorator` / `ThrottleDecorator` / `RetryDecorator` / `MetricsDecorator` / `DataPortRegistry`）全部删除，限流在 task 内、缓存由 service 写、统计 task 写 logger。

## 1. 去掉 `collect_data_ports` 表

### 1.1 现状（5 处读表）

| # | 位置 | 用途 |
|:--|:--|:--|
| 1 | `CollectTaskRegistry.__init__` → `ctx.catalog` | 启动期加载 |
| 2 | `PortCatalog.load` | `SELECT * FROM collect_data_ports` |
| 3 | `CollectManageService.list_fetchers()` | API `/collect/data-ports` |
| 4 | `CollectManageService.get_fetcher(task_type)` | API 单条 |
| 5 | `di.py` `_port_catalog_singleton` | 全局单例 |

### 1.2 迁移方案

**`TaskDef` 从代码自描述**（不是从表读）：

```python
@dataclass(frozen=True)
class TaskDef:
    task_type: str
    label: str
    description: str
    status: str
    default_params: dict
    supports_run_one: bool
    kind: str = "batch"          # batch（入库）/ realtime（按需查询）
    source: Optional[str] = None
    source_label: Optional[str] = None
    ttl_trading: Optional[int] = None
    consumers: tuple[str, ...] = ()

    @classmethod
    def from_handler(cls, handler: BaseCollectTask) -> "TaskDef":
        return cls(
            task_type=handler.name,
            label=handler.label or handler.name,
            description=handler.description,
            status=handler.status or "ready",
            default_params=dict(handler.default_params),
            supports_run_one=handler.supports_collect_one,
            kind="batch",
            source=handler.default_params.get("source"),
        )
```

**catalog 生成**：

```python
# CollectTaskRegistry.catalog()
def catalog(self) -> list[FacetGroup]:
    groups = {f["facet"]: FacetGroup(...) for f in _FACET_DEFS}
    for handler in self._handlers.values():
        td = TaskDef.from_handler(handler)
        groups[handler.facet].sub_groups.setdefault(handler.sub_facet, []).append(td)
    return sorted_groups(groups)
```

### 1.3 需要删除的（5 个文件 + 1 张表）

| # | 文件 | 删除原因 |
|:--|:--|:--|
| 1 | `collect/infrastructure/persistence/models/collect_data_port.py` | `CollectDataPortDB` ORM |
| 2 | `collect/application/port/catalog.py` | `PortCatalog`（从 DB 读） |
| 3 | `collect/application/service/data_port_manage_service.py` | CRUD `collect_data_ports` |
| 4 | `collect/interface/route/collect.py` 内 `/collect/data-ports` 系列 | CRUD 接口 |
| 5 | `collect/application/service/collect_manage_service.py` 内 `port_to_dict` / `list_fetchers` / `get_fetcher` | 改走 `registry.catalog()` |

**DDL**：

```sql
DROP TABLE IF EXISTS collect_data_ports;
```

### 1.4 保留的（仍然存在但走代码）

| 概念 | 保留 | 来源 |
|:--|:--|:--|
| `XxxBO`（23 个） | ✅ | task / fetcher 共用 |
| `XxxEntity`（聚合根） | ✅ | `collect/domain/entitys/` |
| `BaseCollectTask` 类变量 | ✅ | catalog 自描述的来源 |
| `TaskDef.from_handler` | ✅ | 不需要 port.info 推导 |

## 2. 去掉 `DataGateway`

### 2.1 现状（`DataGateway` 5 装饰器链）

```
DataGateway.fetch(port, params, source, policy)
  ↓ ① _validate(port, params)              ← Pydantic 校验
  ↓ ② CacheDecorator.get_or_load           ← policy=QUERY + port.cache
  ↓ ③ _select(port, p, source)             ← 选源
       ├─ MetricsDecorator                 ← 计时 + 统计
       ├─ RetryDecorator                   ← 限流重试
       ├─ ThrottleDecorator                ← 跨 task 限流
       └─ XxxAdapter.fetch(p)              ← 调 SDK
```

**5 装饰器**：

| 装饰器 | 职责 | 移到哪 |
|:--|:--|:--|
| `_validate` | 入参 Pydantic 校验 | **删除**——直接靠 Pydantic 校验（在 fetcher 内） |
| `CacheDecorator` | Redis 缓存 + 单飞锁 | **删除**——service 写 redis |
| `_select` | 选源（按 priority 试） | **删除**——`source` 1:1 映射 fetcher |
| `ThrottleDecorator` | 跨 task 限流 | **移到 task**——`RedisCache.rate_limit` 滑动窗口 |
| `RetryDecorator` | 限流重试 | **移到 task**——`for attempt in 3: try/except → sleep backoff → retry` |
| `MetricsDecorator` | 计时 + 统计 | **移到 task**——`logger.info` + `Redis HASH pipeline` |

### 2.2 去掉的原因

| 装饰器 | 原因 | **复用工程已有** |
|:--|:--|:--|
| `_validate` | Pydantic `BaseModel` 自身有 `.model_validate()`；fetcher `__init__` 时 `Params.model_validate(params)` 即可，**不需要 gateway 包一层** | — |
| `CacheDecorator` | 缓存**只针对"实时查询"**（分 K / 实时资金流）——**业务 service 自己写 redis**——`task` 调 fetcher 是采集入库，**不需要缓存** | **`RedisCache` 已有 KV / 单飞锁**（`redis_cache.py`）——service 直接 `await cache.get / cache.set` |
| `_select`（多源） | **不切换源**——`source` 一传定 = 单 fetcher——`"tushare"` → `KlineTushareFetcher`，**1 个映射 1 个对象** | — |
| `ThrottleDecorator` | 限流应该**集中在 task**（task 知道自己的语义、限频策略、并发数） | **`RedisCache.rate_limit` 已有**（滑动窗口 + pipeline 原子）——`shared/infrastructure/cache/redis_cache.py:50-66`——task 内 `await cache.rate_limit("tushare", 200, 60)` 即可 |
| `RetryDecorator` | 重试是 task 自己的事——`async with retry(times=3, on_exc=(RateLimited,))` 上下文 | **`UNAVAILABLE_BACKOFF` 已有**（`decorators.py:130`）——task 内 `for attempt in 3: try/except RateLimited → sleep → retry` 即可 |
| `MetricsDecorator` | 统计 logger 写即可——`logger.info("task=daily_kline unit=000001.SZ latency=234ms source=tushare success=true")`——**后续 ELK 解析** | **`stats_key` HASH 已有**（`ds:stats:{port}:{tool}:{yyyymmdd}`）——task 内 `await cache.hincrby(...)` 或直接 logger |

### 2.3 去掉后的"取代方案"（**全部复用工程已有**）

| 原 gateway 行为 | 取代方案 | 复用点 |
|:--|:--|:--|
| `gateway.fetch(DailyKlinePort, params, source="tushare", policy=COLLECT)` | `task.collect_one` 内 `await cache.rate_limit("tushare", 200, 60)` + 调 `KlineTushareFetcher.fetch(**params)` | `RedisCache.rate_limit`（滑动窗口） |
| 进程内并发（`min_interval`） | `asyncio.Semaphore(THROTTLE_GROUPS["tushare"].concurrency)` | **`ThrottleConfig` 保留**（`decorators.py:54-67`）——只搬位置不改接口 |
| `gateway.fetch(MinuteKlinePort, params, policy=QUERY)` 走缓存 | `MinuteKlineQueryService.get` 内 `await cache.get(key)` → 命中则返回；未命中则 `await MinuteKlineTushareFetcher.fetch(...)` + `await cache.set(key, value, ex=ttl)` | `RedisCache.get / set` |
| 限流跨 task 共享 | `RedisCache.rate_limit` 跨进程 Redis pipeline | **滑动窗口**（与 token bucket 等价，更简单） |
| 限流重试 | `for attempt in 3: try/except RateLimited → sleep(retry_after) → retry` | 沿用 `RetryDecorator` 的 `UNAVAILABLE_BACKOFF` 模式 |
| 选源 | **`source` 1:1 映射 fetcher**——`CollectContext.fetchers[source]` 直接取 | — |
| 统计 | task 内 `await cache.redis.hincrby(f"ds:stats:{task}:{day}:{source}", "calls", 1)` + `hincrbyfloat("latency_sum", ...)` + `expire(...)` | `MetricsDecorator._record` 模式（`decorators.py:189-210`） |
| 缓存 TTL（盘后 4h） | service 内 `ttl = ttl_for(15)` | **`market_session.ttl_for` 已有**（`market/domain/services/market_session.py:60`）——按 DDD 是跨聚合根纯算法，**直接复用** |

### 2.4 不新建模块（**避免重复造轮子**）

| 之前的草稿 | 修正 | 工程已有什么 |
|:--|:--|:--|
| 新建 `collect/infrastructure/throttle/token_bucket.py` | **不新建** | `RedisCache.rate_limit` 滑动窗口（`redis_cache.py:50-66`）——滑动窗口与 token bucket 在限流场景**等价** |
| 新建 `collect/application/fetcher/retry.py` | **不新建** | `RetryDecorator` 模式（指数退避 1.0/3.0）——task 内 4 行 `for` 即可 |
| 新建 `collect/infrastructure/cache/cache_helper.py` | **不新建** | `RedisCache` 类（`redis_cache.py:25-118`）已覆盖 KV / 限流 / 集合 / 黑名单——直接注入 `RedisCache` 实例 |
| 新建 `collect/application/port/fetcher_port.py` 装 `FetchResult` | **改**：直接用 Pydantic `BaseModel` 作返回（不引入 `FetchResult`） | — |

### 2.5 需要删除的文件（gateway 整套）

| # | 文件 | 删除原因 |
|:--|:--|:--|
| 1 | `data/infrastructure/framework/gateway.py` | `DataGateway` 主类 |
| 2 | `data/infrastructure/framework/cache.py` | `CacheDecorator`（缓存由 `RedisCache` + service 写） |
| 3 | `data/infrastructure/framework/decorators.py` | `ThrottleDecorator` / `RetryDecorator` / `MetricsDecorator`（限流 / 重试 / 统计**保留模式但搬位置**——见 2.6） |
| 4 | `data/infrastructure/framework/registry.py` | `DataPortRegistry`（port 装饰器注册） |
| 5 | `data/infrastructure/framework/context.py` | `call_policy` contextvar |
| 6 | `data/infrastructure/framework/base.py` | `AdapterBase` / `ORIGIN_LABELS` |
| 7 | `data/application/port/base.py` | `DataPort` / `DataCommand` / `DataResult` / `DataGatewayPort` / `CallPolicy` / `CachePolicy` |
| 8 | `data/application/port/`（整个目录） | `tech.py` / `capital.py` / `fundamental.py` / ... 23 个 XxxPort |

### 2.6 保留 `ThrottleConfig` / `RetryDecorator` / `MetricsDecorator` 的**模式**，搬到新位置

`decorators.py` 整体**删除**——但其中的**算法沉淀**值得保留：

| 原 `decorators.py` 元素 | 搬到新位置 | 说明 |
|:--|:--|:--|
| `ThrottleConfig` (dataclass) | `collect/infrastructure/throttle/config.py` | 保留数据结构：`concurrency` + `min_interval` |
| `_GroupState`（进程内 `Semaphore` + `min_interval`） | `collect/infrastructure/throttle/group_state.py` | 进程内限流——**单 worker 单进程场景下够用**——多 worker 场景下叠加 `RedisCache.rate_limit` 做跨进程 |
| `UNAVAILABLE_BACKOFF`（指数退避） | `collect/application/fetcher/retry.py` | 重试退避表——`{1.0, 3.0}` (COLLECT) / `{0.5,}` (QUERY) |
| `RATE_LIMIT_RETRIES = 3` | 同上 | 限流重试次数 |
| `stats_key` / `cache_stats_key` | `collect/infrastructure/stats/keys.py` | Redis 统计键 |
| `STATS_KEEP_DAYS = 7` | 同上 | |
| `QUERY_FETCH_TIMEOUT = 10` | 同上 | |

**注**：`retry.py` 这里只是**算法常量**——task 自己写 4 行循环调用，不引入"上下文管理器"包装。

### 2.7 移到 `collect/` 的（替代品）

| 当前位置 | 移动目标 | 说明 |
|:--|:--|:--|
| `data/infrastructure/framework/base.py` 中 `AdapterBase` | `collect/infrastructure/fetcher/base.py` 中 `BaseFetcher` | 改名 + 移动 |
| `data/application/port/base.py` 中 `RateLimited` / `SourceUnavailable` | `collect/application/port/fetcher_port.py` | 移到 fetcher port |
| `data/infrastructure/client/tushare.py` | `collect/infrastructure/sdk/tushare.py` | 改名 `TushareClient`（已叫这名） |
| `data/infrastructure/client/adata.py` | `collect/infrastructure/sdk/adata.py` | 同 |
| `data/infrastructure/parser/tushare.py` | `collect/infrastructure/parser/tushare.py` | 移动 |

## 3. **不新增**独立限流 / 重试 / 缓存模块——**全部复用工程已有**

| 之前的草稿 | 修正 | 复用 |
|:--|:--|:--|
| 新建 `collect/infrastructure/throttle/token_bucket.py` | ❌ **不新建** | `shared/infrastructure/cache/redis_cache.py:50-66` 已有 `RedisCache.rate_limit(key, max_count, window_seconds)`——**滑动窗口**与 token bucket 在限流场景下**等价**（滑动窗口更简单，无需 ZSET） |
| 新建 `collect/application/fetcher/retry.py`（contextmanager 包装） | ❌ **不新建 contextmanager**——task 内写 4 行循环 | 沿用 `decorators.py:130` `UNAVAILABLE_BACKOFF = {(1.0, 3.0), {0.5,}}` 的**退避表**作为常量即可 |
| 新建 `collect/infrastructure/cache/cache_helper.py` | ❌ **不新建** | `shared/infrastructure/cache/redis_cache.py` 已有 `RedisCache`（`get` / `set` / `delete` / `incr` / `expire` / `sadd` / `smembers` / ...）——service 注入 `RedisCache` 直接调 |
| 新建 `collect/application/port/fetcher_port.py` 装 `FetchResult` | ⚠️ 收敛到 Pydantic `BaseModel` | task `collect_one` 返回 `UnitResult` 即可——不引入"统一返回类型" |
| 新建 `collect/infrastructure/throttle/config.py` | ⚠️ **保留** `ThrottleConfig`（进程内 `Semaphore` + `min_interval`） | 进程内限流在单 worker 单进程下**够用**——多 worker 时叠加 `RedisCache.rate_limit` 做跨进程 |

**最终目录变化**：

| 目录 / 文件 | 变化 |
|:--|:--|
| `shared/infrastructure/cache/redis_client.py` | **不动**（`try_get_redis` / `get_redis` 已是全局单例 + 不健康缓存） |
| `shared/infrastructure/cache/redis_cache.py` | **不动**（`RedisCache` 已覆盖 KV / 限流 / 集合 / 黑名单） |
| `collect/infrastructure/throttle/`（**新**） | 仅放 `ThrottleConfig`（dataclass）+ `_GroupState`（`Semaphore` + `min_interval`）——`RedisCache.rate_limit` 之外**纯进程内**限流 |
| `collect/infrastructure/fetcher/base.py`（**新**） | `BaseFetcher`（`fetch(**params) → list[BO]`）+ 错误类型 `RateLimited` / `SourceUnavailable` / `NotSupported` / `InvalidParams` |
| `collect/application/fetcher/retry.py`（**新**，仅常量） | 退避表 `UNAVAILABLE_BACKOFF` + 重试次数 `RATE_LIMIT_RETRIES = 3` |
| `collect/infrastructure/stats/keys.py`（**新**，仅常量） | `stats_key` / `cache_stats_key` / `STATS_KEEP_DAYS` |
| **其他都不新建** | 业务 service 直接注入 `RedisCache`（来自 `shared`） |

**4 个核心复用点**：

```python
# 1) Redis 客户端：业务 service 注入 RedisCache（不直接用 redis_client）
from shared.infrastructure.cache.redis_cache import get_cache

# 2) 限流：滑动窗口（跨进程）—— 直接用 RedisCache
allowed, remaining = await cache.rate_limit("throttle:tushare", 200, 60)
if not allowed:
    raise RateLimited(retry_after=60.0)

# 3) 进程内并发：直接用 asyncio.Semaphore（ThrottleConfig 保留）
from collect.infrastructure.throttle.config import THROTTLE_GROUPS
sem = asyncio.Semaphore(THROTTLE_GROUPS["tushare"].concurrency)
async with sem:
    items = await fetcher.fetch(...)

# 4) 缓存 TTL：直接复用 market_session.ttl_for
from market.domain.services.market_session import ttl_for
ttl = ttl_for(15)   # 交易时段 15s，盘后 4h
await cache.set(key, value, expire=ttl)
```

## 4. `DataGatewayPort` 协议的去向

| 现状 | 回退后 |
|:--|:--|
| `CollectContext.gateway: DataGatewayPort` | ❌ **删除**——改为 `CollectContext.cache: RedisCache`（来自 `shared`） |
| 注入 `DataGatewayPort` | ❌ **删除** |
| `_port_catalog_singleton` | ❌ **删除** |

**`CollectContext` 改为**：

```python
@dataclass
class CollectContext:
    """采集上下文（启动期单例）"""
    raw_store: RawDataStorePort
    universe: StockUniversePort
    concept: ConceptStorePort
    progress: CollectProgressPort
    jobs: CollectJobStorePort
    cache: "RedisCache"                       # ← shared.infrastructure.cache.redis_cache.RedisCache
    concurrency: int = 3
    max_concurrency: int = 8
```

**注入方式**（FastAPI Depends）：

```python
# collect/infrastructure/setup.py
from shared.infrastructure.cache.redis_cache import get_cache

def build_collect_context() -> "CollectContext":
    redis = asyncio.get_event_loop().run_until_complete(get_cache())   # 启动期一次性拿到
    return CollectContext(
        raw_store=...,
        universe=...,
        concept=...,
        progress=...,
        jobs=...,
        cache=redis,
    )
```

**task 持有具体 fetcher**（不在 ctx 里查）：

```python
# task 构造时显式注入 fetcher + repo，cache 从 ctx 取
class DailyKlineCollectTask(BaseCollectTask):
    def __init__(self, fetcher: KlineTushareFetcher, kline_repo: KlineRepo) -> None:
        self._fetcher = fetcher
        self._kline_repo = kline_repo

    async def collect_one(self, unit, params):
        async with self._rate_limit():
            items = await self._fetcher.fetch(...)
        await self._kline_repo.save_batch(items)

    @asynccontextmanager
    async def _rate_limit(self):
        cache = self.ctx.cache
        allowed, _ = await cache.rate_limit("throttle:tushare", 200, 60)
        if not allowed:
            raise RateLimited(retry_after=60.0)
        yield
```

## 5. `CallPolicy` / `CachePolicy` 的去向

| 概念 | 去向 |
|:--|:--|
| `CallPolicy.QUERY` / `CallPolicy.COLLECT` | ❌ **删除**——没有 gateway policy 概念了 |
| `CachePolicy(ttl_trading, consumers)` | ❌ **删除**——TTL 直接写在 service 的 `cache.set(..., expire=ttl_for(15))` 里 |
| `port.cache` 类变量 | ❌ **删除**——每个 fetcher 自己在 docstring 写"建议缓存 15s"——service 写 redis 时参考 |

## 6. 影响范围汇总（合并后）

| 改动 | 文件 | 行数 |
|:--|:--|:--|
| 删 `DataGateway` | `data/infrastructure/framework/gateway.py` | 删除 |
| 删 `CacheDecorator` | `data/infrastructure/framework/cache.py` | 删除 |
| 删 `Throttle/Retry/Metrics` 装饰器 | `data/infrastructure/framework/decorators.py` | 删除 |
| 删 `DataPortRegistry` | `data/infrastructure/framework/registry.py` | 删除 |
| 删 `call_policy` 上下文 | `data/infrastructure/framework/context.py` | 删除 |
| 删 `DataPort` 等抽象 | `data/application/port/base.py` + `data/application/port/{tech,capital,fundamental,reference}.py` | 删除 5+ 个 |
| 删 `CollectDataPortDB` ORM | `collect/infrastructure/persistence/models/collect_data_port.py` | 删除 |
| 删 `PortCatalog` | `collect/application/port/catalog.py` | 删除 |
| 删 `DataPortManageService` | `collect/application/service/data_port_manage_service.py` | 删除 |
| 改 `CollectContext`（删 gateway 加 fetchers dict） | `collect/application/fetcher/context.py` | `-10 / +10 行` |
| 改 `BaseCollectTask`（构造接收 fetcher） | `collect/application/fetcher/base.py` | `+5 行` |
| 新增 `collect/infrastructure/throttle/config.py`（ThrottleConfig） | `+10 行` |
| 新增 `collect/application/fetcher/retry.py`（UNAVAILABLE_BACKOFF 常量） | `+5 行` |
| 新增 `collect/infrastructure/stats/keys.py`（stats_key 常量） | `+5 行` |
| **合计** | **约 -300 行代码** |

## 7. 与"gateway 简化（保留）"的对比

| 方案 | 描述 | 结论 |
|:--|:--|:--|
| **A** 保留 `DataGateway` + 5 装饰器链 | task / service 调 `gateway.fetch(port, params, source, policy)` | 集中管理 5 件事——但 task 不感知 policy 不合理 |
| **B** 保留 `DataGateway` + 简化（去掉 cache decorator） | task 调 `gateway.fetch` 但不传 policy，service 写 redis | gateway 退化为"只做选源"——**选源本身就是多余的** |
| **C** 去掉 `DataGateway`（本方案） | task 内 `RedisCache.rate_limit` 滑动窗口调 fetcher；service 内 `RedisCache.get/set` 调 fetcher | 5 件事分散到正确位置（task 管采集、service 管查询）——**没有集中抽象层** |

**选 C**：
- gateway 干 5 件事是"为了集中"——但**task 不知道 policy** = 集中抽象反成负担
- task 限流、service 缓存——**职责清晰**
- 装饰器链每次调 4–5 个函数 = 性能开销
- 5 装饰器耦合紧——**改一个要动整链**——难以单测
