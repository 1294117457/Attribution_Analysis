# 03 · Job / Task / Fetcher 设计

> 本文档是合并后采集上下文的**核心架构**——4 层协作：schedule / job / task / fetcher，外加 runner 和 context。**取消 gateway 层**——task 自己管限流 / 并发，fetcher 单纯取数。**没有"多源切换"**——`source` 1:1 映射到 fetcher。

## 1. 4 层架构总览

```
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 1  Schedule（APScheduler，单进程）                              │
│  文件：collect/infrastructure/adapter/scheduler/apscheduler_adapter.py │
│  职责：到点 → 调 manage_service.handle_job_fire(payload) → 转发         │
│  输入：collect_jobs 表中 enabled + mode∈{time,interval} 的记录         │
│  输出：await handler(payload)                                         │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 2  Job（collect_jobs 表 1 条记录）                                │
│  表：collect_jobs                                                       │
│  职责：1 条记录 = 1 个调度单位                                          │
│  字段：task_type / params / mode / concurrency / schedule_type / ...    │
│  状态：pending / running / success / failed / cancelled                │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 3  Task（BaseCollectTask 子类，23 个）                          │
│  文件：collect/application/fetcher/tasks/<task_type>.py               │
│  职责：切单元 + 并发 + 限流（token bucket） + 调 fetcher + 写 repo        │
│  入口：list_units(params) / collect_one(unit, params) / run(...)     │
│  注入：__init__(fetcher, repo) 显式注入                                │
│  由：CollectTaskRegistry 内存维护 task_type → handler                 │
└──────────────────────────────────────────────────────────────────────┘
                                  ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 4  Fetcher（业务名+数据源+Fetcher）                              │
│  文件：collect/infrastructure/fetcher/<业务>_<源>.py                  │
│  职责：调 TushareClient / AdataClient / TdxClient → 解析为 BO          │
│  接口：async fetch(**params) → list[BO]                                │
│  注入：构造时 client 单例（来自 sdk/）                                   │
└──────────────────────────────────────────────────────────────────────┘
```

**辅助**：
- `Runner`（`collect/application/fetcher/runner.py`）—— task 的**状态机外层**（写 `collect_jobs` 状态 / 进度上报 / 取消）
- `Context`（`collect/application/fetcher/context.py`）—— task 运行时注入（`raw_store` / `universe` / `concept` / `progress` / `jobs` / `cache`）

**无 gateway**：
- ❌ 无 `DataGateway` 类
- ❌ 无 `_select` 选源（`source` 1:1 映射 fetcher）
- ❌ 无 `CacheDecorator`（service 自己写 redis）
- ❌ 无 `ThrottleDecorator`（task 内 `RedisCache.rate_limit` 滑动窗口）
- ❌ 无 `RetryDecorator`（task 内 `async with retry(...)`）
- ❌ 无 `MetricsDecorator`（task 内 `logger.info`）

## 2. Layer 1 · Schedule

### 2.1 类

```python
# collect/infrastructure/adapter/scheduler/apscheduler_adapter.py

class ApschedulerAdapter:
    """SchedulerPort 的 APScheduler 实现（单进程）"""
    def __init__(self, timezone: str) -> None: ...
    def start(self) -> None: ...
    def shutdown(self) -> None: ...
    def on_fire(self, handler: JobHandler) -> None: ...
    def upsert(self, key: str, schedule: Schedule, payload: dict) -> None: ...
    def remove(self, key: str) -> None: ...
    def next_run(self, key: str) -> Optional[datetime]: ...
```

### 2.2 关键事实

| 事实 | 说明 |
|:--|:--|
| 进程内单实例 | 启动期 `start()`，关闭期 `shutdown()` |
| 跨进程要锁 | 多 worker 部署时，**job 表加 `locked_at` + `worker_id`**，用 `SELECT FOR UPDATE SKIP LOCKED` 抢 job（**本期不实现，先单进程**） |
| job id 命名 | `{key}`（定频）/ `{key}@{HH:MM}`（定时，每个时间点一个 job） |
| 容错窗口 | `TIME_MISFIRE_GRACE=300` / `INTERVAL_MISFIRE_GRACE=60` |
| 不读仓储 | schedule 不知道 job 长啥样——**只调回调** |

### 2.3 启动期 vs 运行期

```
启动期（main.py lifespan）
├─ redis.init()
├─ collect_ctx = build_collect_context()
├─ handlers = setup_collect_handlers(collect_ctx)      ← 23 个 task 注册
├─ scheduler = ApschedulerAdapter(timezone=settings.TZ)
├─ scheduler.on_fire(collect_service.handle_job_fire)
├─ scheduler.start()
└─ await collect_service.restore_schedules()           ← 读 collect_jobs 重新注册

运行期（HTTP 入口 / 用户手动 / 调度触发）
├─ HTTP POST /collect/jobs/{id}/run → collect_service.run_job_template(id, trigger="manual")
├─ 09:31 触发 → scheduler._fire(key, payload) → collect_service.handle_job_fire(payload)
│                                                              → run_job_template(id, trigger="schedule")
└─ 两者都走：run_job_template → submit → runner.execute → task.run
```

## 3. Layer 2 · Job（`collect_jobs` 表）

### 3.1 DDL（已存在，不变）

```sql
CREATE TABLE collect_jobs (
    id               SERIAL PRIMARY KEY,
    task_type        VARCHAR(64)  NOT NULL,
    display_name     VARCHAR(128),
    mode             VARCHAR(16)  NOT NULL DEFAULT 'once',
    concurrency      INT          NOT NULL DEFAULT 1,
    enabled          BOOLEAN      NOT NULL DEFAULT TRUE,
    schedule_type    VARCHAR(16),
    times            TEXT[]      DEFAULT '{}',
    interval_seconds INT,
    stop_on_fail     BOOLEAN      NOT NULL DEFAULT TRUE,
    params           JSONB        NOT NULL DEFAULT '{}',

    -- 运行时
    trigger_type     VARCHAR(16)  NOT NULL DEFAULT 'manual',
    status           VARCHAR(16)  NOT NULL DEFAULT 'pending',
    total_count      INT,
    success_count    INT,
    fail_count       INT,
    skip_count       INT,
    started_at       TIMESTAMPTZ,
    finished_at      TIMESTAMPTZ,
    duration_ms      INT,
    message          TEXT,

    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.2 一条记录 = 1 个调度单位

| 字段 | 含义 | 取值示例 |
|:--|:--|:--|
| `task_type` | 调哪个 task 类 | `daily_kline` / `stock_basic` / `concept` |
| `params` | task.run 的入参（透传到 collect_one） | `{"source": "tushare", "days": 7, "exchange": ["SSE"]}` |
| `mode` | 调度方式 | `once` / `time` / `interval` |
| `concurrency` | task 内并发 | `5` |
| `times` | 定时触发的时刻 | `["09:31", "15:31"]` |
| `interval_seconds` | 定频秒数 | `3600` |
| `enabled` | 是否启用 | `true` |
| `stop_on_fail` | 单元失败时是否终止整个 task | `true` |
| `trigger_type` | 实际触发方式 | `manual` / `schedule` |
| `status` | 当前执行状态 | `pending` / `running` / `success` / `failed` / `cancelled` |

### 3.3 `params` JSONB 内容约定

```jsonc
// daily_kline
{
    "source": "tushare",                // 数据源（1:1 映射 fetcher）
    "days": 7,
    "start_date": "2026-01-01",
    "end_date": "2026-01-15",
    "exchange": ["SSE", "SZSE"],
    "symbols": ["000001.SZ", ...],
    "mode": "condition",
    "concurrency": 5                    // 覆盖 job.concurrency
}

// concept_membership
{
    "source": "adata:ths",
    "only_missing": true
}
```

**`source` 字段** —— 直接对应 fetcher：
| `source` 取值 | 调用的 fetcher |
|:--|:--|
| `tushare` | `KlineTushareFetcher` / `StockBasicTushareFetcher` / ... |
| `adata:ths` | `ConceptMembershipAdataFetcher` / `ConceptReasonAdataFetcher` |
| `adata` | `NewsAdataFetcher` |

**没有 "多源尝试"**——`source` 一传定 = 单 fetcher。

## 4. Layer 3 · Task（23 个具体类）

### 4.1 抽象基类

```python
# collect/application/fetcher/base.py

class BaseCollectTask(ABC):
    # ── 任务标识（子类必须设置） ──
    name: ClassVar[str]
    facet: ClassVar[str] = ""
    sub_facet: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""
    sort_order: ClassVar[int] = 0
    status: ClassVar[str] = "ready"

    # ── 执行配置 ──
    default_params: ClassVar[dict] = {}
    full_params: ClassVar[dict] = {}
    concurrency: ClassVar[int] = 1              # 1 task 内单元并发数
    rate_limit: ClassVar[Optional[tuple[int, float]]] = None   # (n, period) 跨进程限流

    def __init__(self) -> None:
        self._task_id: int = -1
        self._ctx: Optional["CollectContext"] = None

    def bind(self, ctx: "CollectContext") -> None: ...
    @property
    def ctx(self) -> "CollectContext": ...

    # ── 单元接口（子类实现） ──
    @abstractmethod
    async def list_units(self, params: dict) -> list[str]: ...
    @abstractmethod
    async def collect_one(self, unit: str, params: dict) -> UnitResult: ...

    async def existing_units(self, units: list[str], params: dict) -> set[str]:
        return set()

    async def pending_units(self, params: dict) -> list[str]: ...

    @property
    def supports_collect_one(self) -> bool: ...

    # ── 默认 run 实现 ──
    async def estimate_total(self, params: dict) -> int:
        return len(await self.pending_units(params))

    async def run(
        self,
        params: dict,
        on_unit_done: Callable[[UnitResult, str], Awaitable[None]],
    ) -> TaskSummary:
        units = await self.pending_units(params)
        concurrency = params.get("concurrency", self.concurrency)
        tally = await run_units(
            units=units,
            work=self._work,
            concurrency=concurrency,
            stop_on_fail=self.ctx._stop_on_fail,
            on_unit_done=on_unit_done,
            retry_delay=RETRY_DELAY,
            is_cancelled=lambda: is_cancelled(self._task_id),
        )
        return TaskSummary(
            success=tally.success, fail=tally.fail, skip=tally.skip,
            saved=tally.saved, total_count=len(units),
        )

    async def _work(self, unit: str, params: dict) -> UnitResult:
        return await self.collect_one(unit, params)
```

### 4.2 数据类

```python
@dataclass
class UnitResult:
    success: bool
    detail: str = ""
    saved_count: int = 0
    skipped: bool = False
    error: Optional[str] = None

@dataclass
class UnitTally:
    success: int = 0
    fail: int = 0
    skip: int = 0
    saved: int = 0

@dataclass
class TaskSummary:
    success: int
    fail: int
    skip: int = 0
    saved: int = 0
    total_count: int = 0
```

### 4.3 23 个 task 类模板

**`tasks/daily_kline.py`**：

```python
"""日 K 线采集任务"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from collect.application.fetcher.base import BaseCollectTask, UnitResult
from collect.infrastructure.fetcher.kline_tushare import KlineTushareFetcher
from collect.infrastructure.throttle.config import THROTTLE_GROUPS
from shared.infrastructure.cache.redis_cache import RedisCache
from collect.infrastructure.persistence.kline_repo import KlineRepo

logger = logging.getLogger(__name__)


class DailyKlineCollectTask(BaseCollectTask):
    name = "daily_kline"
    facet = "tech"
    sub_facet = "kline"
    label = "日 K 线"
    description = "单只股票日线 OHLCV（不复权）"
    sort_order = 10
    concurrency = 5                                            # 进程内单元并发（Semaphore）
    rate_limit = ("throttle:tushare", 200, 60)                # Redis 滑动窗口 200/60s（跨进程共享）
    default_params = {"days": 7, "source": "tushare"}
    full_params = {"days": None, "start_date": "2015-01-01"}

    def __init__(self, fetcher: KlineTushareFetcher, kline_repo: KlineRepo) -> None:
        super().__init__()
        self._fetcher = fetcher
        self._kline_repo = kline_repo
        # 进程内 Semaphore（来自 ThrottleConfig，THROTTLE_GROUPS["tushare"].concurrency）
        self._sem = asyncio.Semaphore(THROTTLE_GROUPS["tushare"].concurrency)

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbols"):
            return params["symbols"]
        symbols = await self.ctx.universe.list_symbols(exchange=params.get("exchange"))
        return symbols

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        end = date.fromisoformat(params["end_date"]) if params.get("end_date") else date.today()
        start = (
            date.fromisoformat(params["start_date"])
            if params.get("start_date")
            else end - timedelta(days=params.get("days", 7))
        )

        started = time.perf_counter()
        cache = self.ctx.cache                                # RedisCache（来自 shared）

        # 1) 进程内并发（Semaphore） + 跨进程限流（RedisCache.rate_limit 滑动窗口）
        async with self._sem:
            allowed, remaining = await cache.rate_limit(
                self.rate_limit[0], self.rate_limit[1], self.rate_limit[2],
            )
            if not allowed:
                raise RateLimited(retry_after=self.rate_limit[2])
            # 2) 调 fetcher
            try:
                klines = await self._fetcher.fetch(
                    symbol=unit, start_date=start.isoformat(), end_date=end.isoformat(),
                )
            except RateLimited as e:
                # 3) 退避重试（沿用 UNAVAILABLE_BACKOFF 模式）
                if await self._retry_after_rate_limit(e):
                    klines = await self._fetcher.fetch(
                        symbol=unit, start_date=start.isoformat(), end_date=end.isoformat(),
                    )
                else:
                    raise
        # 4) 统计 + 写库
        latency_ms = int((time.perf_counter() - started) * 1000)
        await self._record_stats(latency_ms, error=None)
        if not klines:
            return UnitResult(success=True, detail=unit, skipped=True)
        saved = await self._kline_repo.save_batch(klines)
        return UnitResult(success=True, detail=unit, saved_count=saved)

    async def _retry_after_rate_limit(self, exc: RateLimited) -> bool:
        """指数退避重试（沿用 UNAVAILABLE_BACKOFF 模式）"""
        for backoff in (1.0, 3.0):                    # COLLECT 退避表
            await asyncio.sleep(backoff)
            try:
                return True                           # 下次重试由 collect_one 外部循环处理
            except Exception:
                continue
        return False

    async def _record_stats(self, latency_ms: int, error: Optional[Exception]) -> None:
        """统计写 Redis（沿用 stats_key HASH 模式）"""
        try:
            redis = self.ctx.cache.redis
            key = f"ds:stats:daily_kline:tushare:{date.today().strftime('%Y%m%d')}"
            async with redis.pipeline(transaction=False) as pipe:
                pipe.hincrby(key, "calls", 1)
                pipe.hincrbyfloat(key, "latency_sum", latency_ms)
                if error is not None:
                    pipe.hincrby(key, "errors", 1)
                pipe.expire(key, 7 * 86400)
                await pipe.execute()
        except Exception as e:
            logger.debug("写采集统计失败: %s", e)
```

### 4.4 `tasks/stock_basic.py`

```python
class StockBasicCollectTask(BaseCollectTask):
    name = "stock_basic"
    facet = "fundamental"
    sub_facet = "stock"
    label = "股票基本信息"
    description = "全 A 股基本信息"
    sort_order = 5
    concurrency = 1
    rate_limit = (200, 60.0)
    default_params = {"source": "tushare", "list_status": "L"}

    def __init__(self, fetcher: StockBasicTushareFetcher, stock_repo: StockRepo) -> None:
        super().__init__()
        self._fetcher = fetcher
        self._stock_repo = stock_repo

    async def list_units(self, params: dict) -> list[str]:
        return ["ALL"]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        allowed, _ = await self.ctx.cache.rate_limit("throttle:tushare", 200, 60)
        if not allowed:
            raise RateLimited(retry_after=60.0)
        stocks = await self._fetcher.fetch(list_status=params.get("list_status", "L"))
        if not stocks:
            return UnitResult(success=True, detail=unit, skipped=True)
        saved = await self._stock_repo.save_basic(stocks)
        return UnitResult(success=True, detail=unit, saved_count=saved)
```

### 4.5 `tasks/concept_membership.py`

```python
class ConceptMembershipCollectTask(BaseCollectTask):
    name = "concept_membership"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念成分股"
    description = "按概念拉成员（adata ths_index_member）"
    sort_order = 30
    concurrency = 3
    rate_limit = (100, 60.0)                              # adata 限频
    default_params = {"source": "adata:ths"}

    def __init__(self, fetcher: ConceptMembershipAdataFetcher, concept_repo: ConceptRepo) -> None:
        super().__init__()
        self._fetcher = fetcher
        self._concept_repo = concept_repo

    async def list_units(self, params: dict) -> list[str]:
        concepts = await self.ctx.concept.list_concepts()
        return [c.code for c in concepts]

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        async with self._sem:
            allowed, _ = await self.ctx.cache.rate_limit(
                "throttle:adata:ths", 100, 60,
            )
            if not allowed:
                raise RateLimited(retry_after=60.0)
            members = await self._fetcher.fetch(concept_code=unit)
        if not members:
            return UnitResult(success=True, detail=unit, skipped=True)
        saved = await self._concept_repo.save_membership(unit, members)
        return UnitResult(success=True, detail=unit, saved_count=saved)
```

### 4.6 `tasks/concept_reason.py`（已存在，改基类）

```python
class ConceptReasonCollectTask(BaseCollectTask):           # 改：去掉 DeclarativeCollectTask
    name = "concept_reason"
    facet = "fundamental"
    sub_facet = "concept"
    label = "概念入选理由"
    description = "F10 入选理由更新"
    default_params = {"only_missing": True, "source": "adata:ths"}

    def __init__(self, fetcher: ConceptReasonAdataFetcher, concept_repo: ConceptRepo) -> None:
        super().__init__()
        self._fetcher = fetcher
        self._concept_repo = concept_repo

    async def list_units(self, params: dict) -> list[str]:
        if params.get("symbol"):
            return [str(params["symbol"]).zfill(6)]
        return await self.ctx.concept.member_symbols(only_missing_reason=bool(params.get("only_missing")))

    async def collect_one(self, unit: str, params: dict) -> UnitResult:
        async with self._sem:
            allowed, _ = await self.ctx.cache.rate_limit(
                "throttle:adata:ths", 100, 60,
            )
            if not allowed:
                raise RateLimited(retry_after=60.0)
            concept_list = await self._fetcher.fetch(symbol=unit)
        if not concept_list:
            return UnitResult(success=True, detail=unit, skipped=True)
        updated = await self._concept_repo.update_reasons(unit, concept_list)
        return UnitResult(success=True, detail=unit, saved_count=updated)
```

### 4.7 注册入口

```python
# collect/infrastructure/setup.py

def setup_collect_handlers(ctx: CollectContext) -> list[BaseCollectTask]:
    tushare = TushareClient(token=settings.TUSHARE_TOKEN)
    adata = AdataClient(token=settings.ADATA_TOKEN)

    return [
        StockBasicCollectTask(
            fetcher=StockBasicTushareFetcher(client=tushare),
            stock_repo=ctx.stock_repo,
        ),
        DailyKlineCollectTask(
            fetcher=KlineTushareFetcher(client=tushare),
            kline_repo=ctx.kline_repo,
        ),
        # ... 23 个
    ]
```

### 4.8 `Runner`（task 的状态机外层）

```python
# collect/application/fetcher/runner.py

class CollectRunner:
    """task 的状态机 + 进度上报"""
    def __init__(self, jobs: CollectJobStorePort, progress: CollectProgressPort) -> None: ...

    async def execute(
        self,
        task_id: int,
        handler: BaseCollectTask,
        params: dict,
        ctx: Optional[CollectContext] = None,
    ) -> None:
        """
        ① pre_execute
        ② estimate_total → progress.set_total
        ③ run（on_unit_done：取消检查 → 累加 → progress.step）
        ④ 收尾：status = TaskOutcome(...).status → jobs.finish + progress.set_status
        """
```

**入口**（`job_service.py`）：

```python
async def submit(self, task_type, params, trigger, *, mode, concurrency) -> SubmittedTask:
    # ① 防重
    cleaned = await self._jobs.mark_running_as_failed(task_type, "进程未正常结束")
    if await self._jobs.has_running(task_type):
        raise TaskConflict(f"{task_type} 已有运行中的任务")
    # ② 解析 params（merge default_params + full_params + 用户传参）
    merged = await self.resolve_params(task_type, params)
    # ③ 写 collect_jobs
    task_id = await self._jobs.create(task_type, trigger, merged, total, mode, concurrency)
    # ④ 初始化 Redis 进度
    await self._progress.init(task_id, total)
    # ⑤ spawn runner（后台跑）
    spawn(self._runner.execute(task_id, self.handler(task_type), merged))
    return SubmittedTask(task_id, task_type, total, merged, mode, concurrency)
```

## 5. Layer 4 · Fetcher

### 5.1 接口

```python
# collect/infrastructure/fetcher/base.py

class BaseFetcher(ABC):
    """Fetcher 抽象基类

    命名规则：业务名 + 数据源 + Fetcher
    例：KlineTushareFetcher / ConceptMembershipAdataFetcher
    """
    fetcher_type: ClassVar[str]                 # "kline_tushare"
    source: ClassVar[str]                       # "tushare" / "adata" / "tdx"
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    async def fetch(self, **params) -> list[BaseModel]:
        """取数 + 解析为 BO"""
        ...
```

### 5.2 SDK 客户端（`sdk/` 目录）

```python
# collect/infrastructure/sdk/tushare.py

class TushareClient:
    """Tushare SDK 封装（init / 配置 / 全局 pro）"""
    def __init__(self, token: str) -> None:
        import tushare as ts
        ts.set_token(token)
        self.pro = ts.pro_api()
```

```python
# collect/infrastructure/sdk/adata.py

class AdataClient:
    """Adata SDK 封装"""
    def __init__(self, token: str) -> None:
        ...
```

### 5.3 一个 Fetcher 样例

```python
# collect/infrastructure/fetcher/kline_tushare.py

class KlineTushareFetcher(BaseFetcher):
    """日 K 线 fetcher（Tushare 数据源）"""
    fetcher_type = "kline_tushare"
    source = "tushare"
    label = "日 K 线（Tushare）"
    description = "Tushare pro.daily 接口"

    def __init__(self, client: TushareClient) -> None:
        self._client = client

    async def fetch(self, *, symbol: str, start_date: str, end_date: str) -> list[KlineBO]:
        df = self._client.pro.daily(
            ts_code=symbol,
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
        )
        return [KlineBO.model_validate(row.to_dict()) for _, row in df.iterrows()]
```

### 5.4 实时 fetcher（**不**走 task）

```python
# collect/infrastructure/fetcher/minute_kline_tushare.py

class MinuteKlineTushareFetcher(BaseFetcher):
    """实时分 K fetcher（Tushare 数据源）"""
    fetcher_type = "minute_kline_tushare"
    source = "tushare"

    def __init__(self, client: TushareClient) -> None:
        self._client = client

    async def fetch(self, *, symbol: str, interval: str, days: int) -> list[MinuteKlineBO]:
        df = self._client.pro.stk_mins(
            ts_code=symbol, freq=interval, days=days,
        )
        return [MinuteKlineBO.model_validate(row.to_dict()) for _, row in df.iterrows()]
```

**被 `MinuteKlineQueryService` 调**——**不走 task**——**service 自己 redis 缓存**。

### 5.5 数据源 / 业务 / fetcher 映射

| 业务 | Fetcher | 数据源 | SDK | 走 task? | 走 query service? |
|:--|:--|:--|:--|:--|:--|
| 日 K（K 线） | `KlineTushareFetcher` | tushare | TushareClient | ✅ | — |
| 股票基本信息 | `StockBasicTushareFetcher` | tushare | TushareClient | ✅ | — |
| 调整因子 | `AdjFactorTushareFetcher` | tushare | TushareClient | ✅ | — |
| 日线基础指标 | `DailyBasicTushareFetcher` | tushare | TushareClient | ✅ | — |
| 停复牌 | `SuspendDTushareFetcher` | tushare | TushareClient | ✅ | — |
| 交易日历 | `TradeCalTushareFetcher` | tushare | TushareClient | ✅ | — |
| 概念列表 | `ConceptTushareFetcher` | tushare | TushareClient | ✅ | — |
| 概念详情 | `ConceptDetailTushareFetcher` | tushare | TushareClient | ✅ | — |
| 概念成分股 | `ConceptMembershipAdataFetcher` | adata | AdataClient | ✅ | — |
| 概念入选理由 | `ConceptReasonAdataFetcher` | adata | AdataClient | ✅ | — |
| 个股资金流 | `MoneyflowTushareFetcher` | tushare | TushareClient | ✅ | — |
| 沪深港通资金流 | `MoneyflowHsgtTushareFetcher` | tushare | TushareClient | ✅ | — |
| 沪深通前 10 | `HsgtTop10TushareFetcher` | tushare | TushareClient | ✅ | — |
| 融资融券 | `MarginTushareFetcher` | tushare | TushareClient | ✅ | — |
| 融资融券明细 | `MarginDetailTushareFetcher` | tushare | TushareClient | ✅ | — |
| 涨停板 | `LimitListDTushareFetcher` | tushare | TushareClient | ✅ | — |
| 股东人数 | `StkHolderNumberTushareFetcher` | tushare | TushareClient | ✅ | — |
| 前 10 股东 | `Top10HoldersTushareFetcher` | tushare | TushareClient | ✅ | — |
| 龙虎榜 | `TopListTushareFetcher` | tushare | TushareClient | ✅ | — |
| 龙虎榜机构 | `TopInstTushareFetcher` | tushare | TushareClient | ✅ | — |
| 新闻 | `NewsAdataFetcher` | adata | AdataClient | ✅ | — |
| 连板天梯 | `LimitStepTushareFetcher` | tushare | TushareClient | ✅ | — |
| 指数基本信息 | `IndexBasicTushareFetcher` | tushare | TushareClient | ✅ | — |
| **实时分 K** | `MinuteKlineTushareFetcher` | tushare | TushareClient | ❌ | ✅（`MinuteKlineQueryService`） |
| **实时资金流（沪深港通）** | `MoneyflowHsgtRealtimeTushareFetcher` | tushare | TushareClient | ❌ | ✅（`MoneyflowQueryService`） |
| **沪深通前 10（实时）** | `HsgtTop10RealtimeTushareFetcher` | tushare | TushareClient | ❌ | ✅ |
| **涨停板（盘中）** | `LimitListDRealtimeTushareFetcher` | tushare | TushareClient | ❌ | ✅ |
| **实时新闻** | `NewsRealtimeAdataFetcher` | adata | AdataClient | ❌ | ✅ |

**28 个 fetcher = 23 个入库 + 5 个实时查询**。

## 6. 限流与并发（**全部复用工程已有**）

### 6.1 限流：滑动窗口（复用 `RedisCache.rate_limit`）

`shared/infrastructure/cache/redis_cache.py:50-66` 已有：

```python
async def rate_limit(self, key: str, max_count: int, window_seconds: int) -> tuple[bool, int]:
    """基于 Redis 的滑动窗口式限流(每窗口都重置 expire)"""
    async with self.redis.pipeline(transaction=True) as pipe:
        await pipe.incr(key)
        await pipe.expire(key, window_seconds)
        count, _ = await pipe.execute()
    remaining = max(0, max_count - count)
    return count <= max_count, remaining
```

**task 用法**：

```python
class DailyKlineCollectTask(BaseCollectTask):
    rate_limit = ("throttle:tushare", 200, 60)            # (key, max, window)

    async def collect_one(self, unit, params):
        cache = self.ctx.cache                            # RedisCache
        allowed, remaining = await cache.rate_limit(*self.rate_limit)
        if not allowed:
            raise RateLimited(retry_after=60.0)
        items = await self._fetcher.fetch(...)
```

**滑动窗口 vs token bucket 对比**：

| 维度 | 滑动窗口 | Token bucket |
|:--|:--|:--|
| 实现复杂度 | 1 个 `INCR` + 1 个 `EXPIRE` | ZADD + ZREMRANGEBYSCORE + ZCARD |
| 突发处理 | 窗口内可能"先放行后累计" | 平滑 |
| 精度 | 窗口边界可能超限 1 次 | 严格不超过 |
| Redis 操作 | 2 命令（pipeline） | 4+ 命令 |
| **限流场景是否够用** | **够用**（与上游 API 协议不冲突） | 够用 |

**`task.rate_limit` 配置**（类变量）：

| task | rate_limit | 含义 |
|:--|:--|:--|
| `DailyKlineCollectTask` | `("throttle:tushare", 200, 60)` | Tushare 全局 200/60s |
| `ConceptMembershipCollectTask` | `("throttle:adata:ths", 100, 60)` | adata ths 100/60s |
| `StockBasicCollectTask` | `("throttle:tushare", 200, 60)` | Tushare 全局 200/60s |
| ... | ... | |

**`source` 是限流的 key**——**同 key 的所有 task 共享同一配额**——Tushare 5 个 task 都在 `throttle:tushare` 限流下。

### 6.2 并发：进程内 `Semaphore`（复用 `ThrottleConfig`）

**`data/infrastructure/framework/decorators.py:54-67` 已有**：

```python
@dataclass(frozen=True)
class ThrottleConfig:
    concurrency: int
    min_interval: float = 0.0

THROTTLE_GROUPS: dict[str, ThrottleConfig] = {
    "tushare": ThrottleConfig(concurrency=settings.COLLECT_MAX_CONCURRENCY, min_interval=0.15),
    "adata:ths": ThrottleConfig(concurrency=5, min_interval=0.5),
    "tdx": ThrottleConfig(concurrency=1, min_interval=0.0),
}
```

**搬到新位置**（`collect/infrastructure/throttle/config.py`）——**不改算法**。

**`task.concurrency` 配置**（类变量）：

| task | concurrency | 含义 |
|:--|:--|:--|
| `DailyKlineCollectTask` | `5` | 同时跑 5 个股票 |
| `ConceptMembershipCollectTask` | `3` | 同时跑 3 个概念 |
| `StockBasicCollectTask` | `1` | 全 A 一次拉完 |
| `ConceptReasonCollectTask` | `5` | 同时 5 只股票 |

**`asyncio.gather(..., concurrency=task.concurrency)` 实现**（`run_units` 已实现）——单元并发。

**进程内 `Semaphore` 来自 `THROTTLE_GROUPS`：

```python
# task 构造时
self._sem = asyncio.Semaphore(THROTTLE_GROUPS["tushare"].concurrency)

# collect_one
async with self._sem:
    allowed, _ = await cache.rate_limit(...)
    items = await self._fetcher.fetch(...)
```

### 6.3 限流 + 并发的关系（两个维度）

| 维度 | 进程内并发 | 跨进程限流 |
|:--|:--|:--|
| 范围 | **单 task 内** | **跨 task + 跨进程** |
| 实现 | `asyncio.Semaphore`（`THROTTLE_GROUPS`） | `RedisCache.rate_limit`（滑动窗口） |
| 共享 | 不共享 | 同 key 共享 |
| 监控 | `UnitResult` 累计 | Redis `INCR` 计数 |
| **调用方** | `run_units` 内部 | task `collect_one` 内 |

**两者是正交的**：
- `concurrency=5` 决定"1 个 task 同时跑 5 个单元"
- `rate_limit=("throttle:tushare", 200, 60)` 决定"5 个 task 一起 1 分钟最多调 200 次"

**两个加在一起 = "5 个单元并发跑，但 1 分钟不会超过 200 次 Tushare 调用"**。

### 6.4 复用汇总表

| 需求 | 复用 | 位置 |
|:--|:--|:--|
| Redis 客户端（不健康缓存） | `try_get_redis` | `shared/infrastructure/cache/redis_client.py:91-127` |
| Redis 客户端（构造） | `get_redis` | `shared/infrastructure/cache/redis_client.py:58-67` |
| Redis 业务工具（KV / 限流 / 集合） | `RedisCache` | `shared/infrastructure/cache/redis_cache.py:25-118` |
| 限流（滑动窗口） | `RedisCache.rate_limit` | `redis_cache.py:50-66` |
| 限流（进程内并发） | `THROTTLE_GROUPS` + `_GroupState` | `decorators.py:54-99`（搬位置） |
| 退避重试 | `UNAVAILABLE_BACKOFF` 常量 | `decorators.py:130`（搬位置） |
| 统计（Redis HASH） | `stats_key` HASH + `MetricsDecorator._record` 模式 | `decorators.py:189-210`（搬位置） |
| 缓存 TTL（盘后 4h） | `ttl_for` | `market/domain/services/market_session.py:60` |

**不新建**（**避免重复造轮子**）：
- ❌ `collect/infrastructure/throttle/token_bucket.py`（用 `RedisCache.rate_limit`）
- ❌ `collect/application/fetcher/retry.py`（task 内 4 行 for 循环 + 退避表常量）
- ❌ `collect/infrastructure/cache/cache_helper.py`（用 `RedisCache`）
- ❌ `collect/infrastructure/stats/redis_stats.py`（task 内 pipeline 直接写 HASH）

## 7. 完整调用链

```
[启动期]
main.py lifespan
  ├─ redis.init()
  ├─ tushare = TushareClient(token=settings.TUSHARE_TOKEN)
  ├─ adata = AdataClient(token=settings.ADATA_TOKEN)
  ├─ collect_ctx = build_collect_context()
  ├─ handlers = setup_collect_handlers(collect_ctx, tushare, adata)    ← 23 个 task 注册
  ├─ query_svcs = setup_query_services(collect_ctx, tushare)          ← 5 个 query service 注册
  ├─ scheduler = ApschedulerAdapter(timezone=settings.TZ)
  ├─ scheduler.on_fire(collect_service.handle_job_fire)
  ├─ scheduler.start()
  └─ await collect_service.restore_schedules()

[运行期 - 定时触发]
09:31
  ↓
scheduler._fire(key="job:1", payload={"job_id": 1})
  ↓
collect_service.handle_job_fire({"job_id": 1})
  ↓
collect_service.run_job_template(job_id=1, trigger="schedule")
  ↓
collect_service.submit(
    task_type="daily_kline",
    params={"source": "tushare", "days": 7},
    trigger="schedule",
    mode="time",
    concurrency=5,
)
  ↓
runner.execute(task_id, handler, params)
  ├─ pre_execute(params)
  ├─ progress.set_total(task_id, total)
  ├─ handler.run(params, on_unit_done)
  │   ├─ pending_units(params)              → list[str]   (5000 股票)
  │   └─ run_units(units, work, concurrency=5)
  │        ├─ work(unit) → handler.collect_one(unit, params)
  │        │    ├─ async with self._sem:                                              ← 进程内 Semaphore（THROTTLE_GROUPS）
  │        │    ├─ allowed, _ = await cache.rate_limit("throttle:tushare", 200, 60)  ← 跨进程限流（RedisCache 滑动窗口）
  │        │    │    └─ KlineTushareFetcher.fetch(symbol, start, end)  → list[KlineBO]
  │        │    └─ kline_repo.save_batch(KlineBO)                        → saved
  │        └─ on_unit_done(result, label)  → 累加 success/fail/skip → progress.step
  │                                                    → logger.info("task=daily_kline unit=...")
  └─ status="success" → jobs.finish + progress.set_status

[运行期 - HTTP 实时查询]
GET /klines/minute?symbol=000001.SZ&interval=5min&days=1
  ↓
route 调 MinuteKlineQueryService.get(symbol, interval, days)
  ↓
service.get(symbol, interval, days)
  ├─ key = f"kline:minute:{symbol}:{interval}:{days}"
  ├─ ttl = 15（交易）/ 4h（盘后）= market_session.ttl_for(15)
  ├─ value, hit = await cache_get_or_set(key, ttl, fetch_fn)
  │   └─ fetch_fn:
  │       └─ MinuteKlineTushareFetcher.fetch(symbol, interval, days)  → list[MinuteKlineBO]
  ├─ return {"klines": [bo.model_dump() for bo in value], "cached": hit, ...}
```

## 8. 与多 worker 部署的关系

| 阶段 | 单进程（当前） | 多 worker（未来） |
|:--|:--|:--|
| APScheduler | 1 个进程 | **1 个独立 scheduler 进程**（不与 HTTP worker 共享） |
| HTTP worker | 1 个 FastAPI | N 个 FastAPI worker |
| Job 抢锁 | 不需要 | **`SELECT ... FOR UPDATE SKIP LOCKED`** 或 Redis SETNX |
| 跨进程限流 | `RedisCache.rate_limit` 走 Redis 滑动窗口——**多进程共享**（已正确） | 同左 |
| Task 注册 | 内存 | 内存（每个 worker 自己注册） |
| Fetcher 注册 | 内存（`setup_collect_handlers` 返回 list） | 内存（每个 worker 自己注册） |
| SDK Client 单例 | 1 个 TushareClient | N 个 TushareClient（每个 worker 1 个）——**正确**（线程/进程安全由 SDK 内部管） |

**Task / Fetcher 的"内存注册"在多 worker 下不变**——**每个 worker 进程自己持有一份**。**重启即刷新**。**只有"调度 + 抢 job"需要跨进程**。
