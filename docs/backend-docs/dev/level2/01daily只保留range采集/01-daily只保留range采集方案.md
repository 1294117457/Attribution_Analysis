# daily 只保留 range 采集 —— 修改方案（v3）

> 位置：`docs/backend-docs/dev/level2/01daily只保留range采集/01-daily只保留range采集方案.md`
> 配套文档：
> - `../step2架构优化/01-daily_kline全链路分层重构方案.md`（上一轮全链路分层方案，本轮在其基础上收敛）
> - `../step2架构优化/02-daily_kline路由层独立化方案.md`（route 层独立化，本轮沿用其结论）
> - `../../config/DDD.md`（分层规范，硬约束）
> 更新日期：2026-10-27（v3：事务边界归属澄清 + `DailyFetcherResult` 命名 + 收窄到 Daily 单点跑通）
> 状态：**待评审（暂不修改代码）**
> 范围：**只改 daily 这一条线**，不铺开到其余 24 个 collect service。

---

## 〇、决策摘要

### 0.1 一句话

把 `daily` 采集收敛成**只有时间范围一种模式**：`route → DTO → service.collect(req) → run_collect(req) → 逐日 fetch → BO → repo.save()`，删掉 `ts_code` 单股分支，清掉沿途死代码。

### 0.2 本轮 6 个决策

| # | 决策 | 说明 |
|---|---|---|
| **D1** | **删掉 `ts_code` 单股采集能力** | `DailyCollectRequest` 只剩 `start_date` / `end_date`；前端移除股票代码输入框；坏调用链一并下线（§4） |
| **D2** | **不引入 `TradeCalendarRepository`** | 按前端传的自然日区间逐日采集。周末/节假日 Tushare 返回空 → 记为「无数据」不算失败 |
| **D3** | **定义 `DailyFetcherResult` model，替代裸元组** | 这是当前线上报错的根因。命名收窄到 Daily，不做通用 Collect 设计（§3.6） |
| **D4** | **事务边界在 service，但 commit/rollback 不写在 service 里** | 用 `get_raw_db_context()` 承担 commit/rollback，service 只管「开不开事务」的决策（§3.4） |
| **D5** | **删除沿途死代码** | 见 §2，9 处死代码 + 1 处潜在 bug（`__all__` 导出不存在名字） |
| **D6** | **只针对 Daily 跑通，不提前抽象到整体 Collect** | 命名、模型、repo 方法都带 `Daily` 前缀；不设计通用 `CollectUnitResult` 基类、不改其余 24 个 service（§3.7） |
### 0.3 目标链路（4 层，方向单一，无分叉）

```
POST /api/collect/tech/daily
  body: { start_date, end_date }              ← DailyCollectRequest（interface 层 DTO）
        │
        ▼
  DailyService.collect(req: DailyCollectRequest)      ← 派发后台任务，立即返回
        │
        ▼
  DailyService.run_collect(req: DailyCollectRequest)  ← 后台全生命周期
        │
        ├─ log_util.create() 建日志
        ├─ log_util.update_status(running)
        │
        ├─ 展开 [start_date, end_date] → days: list[date]
        ├─ for day in days:  ─────────────────────────────┐
        │     result = await self._collect_by_date(day)  │  ← 唯一采集方法
        │     #   内部：fetch → BO → repo.save(BO)        │
        │     progress += 1                               │
        │     log_util.update_progress()                  │
        ├─────────────────────────────────────────────────┘
        │
        └─ log_util.update() 终态（写 DB + 清 Redis）
```

**4 层，方向单一，没有分叉。**

### 0.4 关于「为什么不需要 `_collect_range`」

上一版文档设计了 `_collect_range` + `_collect_by_date` 两层，理由是「并发调度 + 进度上报」需要单独一个方法承载。

**本版取消这个设计**，理由：

1. **并发度当前是 1**（`META.concurrency = 1`）。为一个恒为 1 的并发专门开一个方法 + 一层闭包嵌套，是纯粹的复杂度。
2. **`_collect_range` 的返回值 `list[DailyFetcherResult]` 没人真正消费** —— `run_collect` 只需要 `ok_total` / `fail_total` / `saved_total` 三个聚合数。保留整个列表是为了拿这三个数，属于「为了形式而保留」。
3. **闭包嵌套 3 层**（`run_collect` → `for` → `async def one`）是当前 `daily_service.py` 难读的主因之一。取消后 `run_collect` 是一段线性的 `for` 循环，一眼能看完。
4. **进度上报不需要在独立方法里**。`update_progress` 是 1 行调用，直接写在循环体里更直观。

**代价**：如果将来 `META.concurrency` 要调到 >1，需要把循环体重新抽成方法。**但这是 YAGNI** —— 调并发时再抽不迟，而且那时候抽取的边界会更清楚（哪些状态需要 `nonlocal`、session 怎么隔离）。

> ⚠️ **重要取舍**：取消 `_collect_range` 后，**每个采集单元的事务隔离靠 `_collect_by_date` 内部自开 session 实现**（D4）。session 生命周期收回到单元粒度，service 不再持有跨单元的 session，也就不存在「并发共用 session」的问题。

### 0.5 本轮不做（登记备查）

| # | 事项 | 原因 |
|---|---|---|
| X1 | 启用交易日历（`TradeCalendarRepository`） | 用户明确不引入；且该 repo 是**死代码**，本轮直接删除（§2.1） |
| X2 | 修复 `StockInfoService.collect()` 的调用契约 | 本轮删掉 `ts_code` 后该路径自动失效，改为**直接下线**（§4.4） |
| X3 | `KlineBO` 从 `market` 迁到 `collect`（BO 归属修正） | 涉及跨 context 移动 + `to_entity()` 反向依赖，建议单独 commit（§4.6） |
| X4 | `KlineBO.name` 全市场采集时为空串 | `StockNameRepository` 能补齐，但本轮不接（它也是死代码，见 §2.1） |
| X5 | `volume` 单位（手 vs 股） | Tushare `vol` 是「手」，`KlineBO` 注释写「股」。本轮不修，登记备查 |

---

## 一、现状盘点

### 1.1 当前代码结构

`backend/src/contexts/collect/application/service/tech/daily_service.py`（331 行）：

| 方法 | 行号 | 职责 | 问题 |
|---|---|---|---|
| `collect(req)` | 80-90 | 派发后台任务 | ✅ 无问题 |
| `run_collect(req)` | 96-215 | 全生命周期 + 分叉 A/B | ⚠️ 含 A/B 两条路径 |
| `_list_days(start, end)` | 221-229 | 自然日展开 | ⚠️ 纯函数，内联即可 |
| `_collect_all_days(days, session, log_id)` | 231-277 | 并发调度 + 进度上报 | ⚠️ "all" 有歧义；并发恒为 1 |
| `_collect_by_symbol(req, session)` | 279-297 | 单股整段采集 | ❌ **本轮删除** |
| `_collect_by_date(day, session)` | 300-309 | 单日采集 | ⚠️ 返回 2 元组，调用方期望 3 元组 |
| `_retry(call, session)` | 311-320 | 重试 | ⚠️ 回滚外部传入的 session |
| `_save(klines, session)` | 323-327 | 入库 + commit | ⚠️ 并发共用 session |

### 1.2 三个必须记住的现存缺陷

#### 缺陷 1：解包崩溃（线上正在发生）

```256:256:D:\codes\Attribution_Analysis\backend\src\contexts\collect\application\service\tech\daily_service.py
            rows, ok, fail = result
```

`_collect_by_date` 返回 2 元组 `(rows, ok)`，`one()` 按 3 元组解包 → `ValueError: not enough values to unpack (expected 3, got 2)`。

**关键点**：异常兜底分支 `result = (0, False, 1)` 是 3 元组，所以**只有采集成功时才会炸**。

#### 缺陷 2：并发共用一个 session

```125:126:D:\codes\Attribution_Analysis\backend\src\contexts\collect\application\service\tech\daily_service.py
            from shared.infrastructure.di.db_session import get_raw_db_context
            async with get_raw_db_context() as session:
```

这个 session 传给所有日期单元，而 `_save()` 内部 `await session.commit()` —— 多个并发 task 交叉 commit 同一 AsyncSession，SQLAlchemy 下不安全。当前 `META.concurrency = 1` 侥幸没事。

**本轮解法**：session 生命周期从 `run_collect` 下沉到 `_collect_by_date`（每个自然日独立 session + 独立事务），service 里不再出现 commit/rollback（D4，详见 §3.4）。

#### 缺陷 3：进度口径注释与代码相反

```155:158:D:\codes\Attribution_Analysis\backend\src\contexts\collect\application\service\tech\daily_service.py
            # 分母只算查到数据的单元（周末/停牌等空返回不占分母）
            progress = (
                min(100, int(ok_total / total * 100))
                if total > 0 else 0
            )
```

注释说分母只算有数据的单元，代码里分母是 `total`（全部自然日数）。且实时进度用 `done/total`（完成数）、终态进度用 `ok_total/total`（成功数），两处口径不一致。

### 1.3 数据结构链路（这部分**已经是对的**）

```
Tushare DataFrame
  └─ TushareKlineParser.parse_frame()        ← parser：DataFrame → list[KlineBO]
       └─ DailyTushareFetcher.fetch_by_date() ← fetcher：返回 list[KlineBO]
            └─ DailyService._collect_by_date()  ← service：编排（取数 → 事务 → 入库）
                 └─ DailyKlineRepository.save_klines(klines, session)
                      └─ _to_row(k)           ← repo：BO → dict（ORM 列名）
                           └─ pg_insert(TechKlineDailyDB).values(rows)
                                .on_conflict_do_update(index_elements=["symbol","date"])
```

**「返回参用 model 承接 → 直接入库」这件事，现有代码已经做到了**（`KlineBO` 是 Pydantic model，repo 有唯一映射点 `_to_row`）。缺的只是**单元结果**这层的结构化定义（`DailyFetcherResult`）。

**注意**：repo 的 `save_klines(klines, session)` 签名**不需要改** —— session 由 service 自开后传入，repo 只负责「执行 SQL」。

### 1.4 `KlineBO` 字段与 ORM 对照

| BO 字段 | ORM 列 (`tech_daily`) | 类型 | 备注 |
|---|---|---|---|
| `symbol` | `symbol` | str | 6 位 |
| `name` | `name` | str? | 全市场采集时为空串（§0.5 X4） |
| `trade_date` | `date` | date | **命名不一致**，repo 里转换 |
| `open`/`high`/`low`/`close` | 同名 | float | |
| `volume` | `volume` | int | Tushare `vol` 单位是**手**，parser 未换算（§0.5 X5） |
| `amount` | `amount` | float | Tushare `amount` 单位是**千元**，parser ×1000 转元 ✅ |
| `change_pct` | `change_pct` | float? | Tushare `pct_chg` ✅ |
| `source` | — | str | **不入库**（`source` 不在 `_to_row` 里） |

### 1.5 调用方全景

| 调用方 | 传什么 | 现状 | 本轮处理 |
|---|---|---|---|
| `route/tech/daily.py` | `DailyCollectRequest` | ✅ 正常 | DTO 删 `ts_code` |
| 前端 `CollectActionCard.vue` | `{start_date, end_date, ts_code?}` | ✅ 正常 | 移除代码输入框 |
| `StockInfoService.collect()` | `{symbol, start_date, end_date, days}` | ❌ **已损坏** | **下线**（§4.4） |
| `user/di/stock_pool.py::_run_collect_one` | `{days, symbol}` | ❌ **已损坏** | **下线**（§4.4） |
| `user/adapter/background/operation_dispatcher.py` | `{"days": days}` | ❌ **已损坏** | **下线**（§4.4） |

### 1.6 「已损坏」的证据

**`StockInfoService.collect()`**（`market/application/service/stock_info_service.py:219-226`）：

```python
params = {
    "symbol": request.symbol,        # ← 字段名错，DTO 要的是 ts_code
    "start_date": ...,
    "end_date": ...,
    "days": request.days,            # ← DTO 里没这个字段
}
await self._daily_svc.collect(params)   # ← 但 collect() 收的是 DailyCollectRequest（强类型）
```

`DailyCollectRequest` 是强类型 Pydantic model，`params` 是 `dict` → `start_date`/`end_date` 缺失 → 校验失败抛 `ValidationError`。**这条路径现在就是坏的。**

另外 `get_stock_info_service()` 根本没注入 `daily_svc`：

```45:57:D:\codes\Attribution_Analysis\backend\src\contexts\market\infrastructure\di\stock_info.py
    return StockInfoService(
        stock_repo=StockRepoImpl(raw_session, attr_session),
        kline_repo=KlineRepoImpl(raw_session),
        pool_repo=StockPoolRepoImpl(attr_session),
        panel_repo=StockPanelComposeRepoImpl(raw_session, attr_session),
        concept_repo=ConceptRepoImpl(raw_session, attr_session),
        brief_service=ConceptBriefService(),
        indicator_calc=IndicatorCalculator(),
        stock_basic_svc=stock_basic_svc,
    )
```

→ `self._daily_svc is None` → `raise RuntimeError("StockInfoService 未注入 DailyService")` → `POST /api/v1/klines/collect` **必 500**。

**`stock_pool.py::_run_collect_one`** 传 `{"symbol": symbol}` —— 同样字段名错。

**结论**：这些是**改造前就存在的坏路径**，本轮不需要"修复"它们，直接下线即可（§4.4）。

---

## 二、死代码清理清单（D5）

### 2.1 确认的死代码（可安全删除）

> 判定标准：全仓 grep 无任何引用，或唯一引用方本身也是死代码。

| # | 位置 | 内容 | 证据 | 动作 |
|---|---|---|---|---|
| **DC-1** | `collect/infrastructure/persistence/repositories/kline_repo.py` | `KlineRepository`（184 行） | docstring 自称「DailyService 直接调本类的 save_klines()」，实际**从未被调用**；`get_kline_repository()` 无任何 `Depends` | **删文件** + 删 DI 工厂 |
| **DC-2** | `collect/domain/entitys/kline/repository.py` | `KlineRepository` Protocol | 实现方（DC-1）被删后无人引用；且它 import `market.domain.entities.kline.entity`（反向依赖） | **删文件** |
| **DC-3** | `collect/infrastructure/persistence/repositories/tech/trade_calendar_repo.py` | `TradeCalendarRepository` | 用户明确不引入；全仓无调用方 | **删文件** + 删 DI 工厂 |
| **DC-4** | `collect/infrastructure/persistence/repositories/tech/stock_name_repo.py` | `StockNameRepository` | 全仓无调用方 | **删文件** + 删 DI 工厂 |
| **DC-5** | `market/application/bo/kline.py:32-42` | `KlineBO.to_entity_args()` | 全仓无调用方（`to_entity()` 走的是另一条路径） | **删方法** |
| **DC-6** | `market/application/bo/kline.py:123` | `__all__` 里的 `"CachePolicy"` / `"DataPort"` | **这两个类在文件里根本不存在** → `from ... import *` 会直接 `ImportError` | **删这两个名字**（潜在 bug，见 §2.2） |
| **DC-7** | `collect/application/port/params.py:41-43` | `StockBasicParams` | `StockBasicTushareFetcher.py:30` **自己又定义了一个同名类**，port 里这个是真死代码 | **删类** |
| **DC-8** | `collect/application/port/params.py:26-28` | `TradeDateParams` | 仅 `market/application/bo/stock_info.py:8` import，但那个文件里**没有实际使用**（只 import 不用） | **删类** + 清理 import |
| **DC-9** | `collect/application/port/params.py:46-50` | `MinuteKlineParams`（port 版） | `market/application/bo/kline.py:96` 有**另一个同名类**且**实际在用**（`minute_kline.py` route + `MinutePytdxFetcher.py` 都用 market 版）；port 版无调用方 | **删类** |
| **DC-10** | `collect/application/service/base.py:83-101` | `CollectResult.to_dict()` | 全仓无调用方 | **删方法** |
| **DC-11** | `market/application/bo/kline.py:50-58` | `KlineBO.to_entity()` 的空行块（`:50-58` 是 8 个空行） | — | **清理格式** |

### 2.2 顺带发现的潜在 bug（DC-6）

```120:124:D:\codes\Attribution_Analysis\backend\src\contexts\market\application\bo\kline.py
__all__ = [
    "KlineBO", "MinuteKlineBO", "MinuteKlineParams", "MinuteInterval",
    "BARS_PER_DAY", "CachePolicy", "DataPort",
]
```

`CachePolicy` 和 `DataPort` **在这文件里根本没定义**（grep 确认无 `class CachePolicy` / `class DataPort`）。

任何 `from contexts.market.application.bo.kline import *` 都会抛：
```
ImportError: cannot import name 'CachePolicy' from 'contexts.market.application.bo.kline'
```

当前没炸是因为**没有代码用 `import *`**。属于潜伏 bug，删掉即可。

### 2.3 死代码清理后的连带修改

| 文件 | 动作 |
|---|---|
| `collect/infrastructure/di/repo.py` | 删 `get_kline_repository` / `get_trade_calendar_repository` / `get_stock_name_repository` 三个工厂 + `__all__` 对应项 |
| `collect/infrastructure/persistence/repositories/__init__.py` | 删 `KlineRepository` import + `__all__` 项 |
| `collect/infrastructure/persistence/repositories/tech/__init__.py` | 删 `StockNameRepository` / `TradeCalendarRepository` import + `__all__` 项 |
| `collect/application/port/__init__.py` | 删 `StockBasicParams` / `TradeDateParams` / `MinuteKlineParams` import + `__all__` 项 |
| `collect/application/port/params.py` | 删 DC-7 / DC-8 / DC-9 三个类 + `__all__` 项 |
| `market/application/bo/kline.py` | 删 `to_entity_args()` + 修 `__all__`（DC-5 / DC-6） |
| `market/application/bo/stock_info.py:8` | 清理未使用的 import |
| `collect/application/service/base.py` | 删 `CollectResult.to_dict()` |

### 2.4 不在本轮清理范围（登记备查）

| # | 位置 | 原因 |
|---|---|---|
| Y-1 | `collect/application/port/params.py` 的 `EmptyParams` / `IndexCodeParams` / `SymbolParams` | **有调用方**：`concept/application/bo/concept.py:8`、`concept/domain/concept/bo.py:8`、`market/application/bo/stock_info.py:8` |
| Y-2 | `collect/application/port/params.py` 的 `ListStatus` | **有调用方**：`market/application/bo/stock_info.py:8` |
| Y-3 | `collect/application/service/base.py` 的 `CollectResult` 类本身 | **有调用方**：`minute_service.py`、`concept_minute_service.py`、`sentiment_service.py` |
| Y-4 | `market/application/bo/kline.py` 的 `MinuteKlineBO` / `MinuteKlineParams` / `MinuteInterval` / `BARS_PER_DAY` | **有调用方**：`minute_kline.py` route、`MinutePytdxFetcher.py` |
| Y-5 | `collect/domain/entitys/` 下其他 24 个 Protocol | 不在 daily 链路范围内，超出本轮范围 |
| Y-6 | `market/infrastructure/persistence/repositories/kline_repository.py`（`KlineRepoImpl`） | **有调用方**：`market/application/service/stock_info_service.py` |

---

## 三、核心设计：单方法 + 事务边界归位

### 3.1 `DailyService` 目标结构（4 个方法）

```python
class DailyService:
    """日 K 线采集服务（按时间范围采集全市场）"""

    META = ServiceMeta(...)

    async def collect(self, req: DailyCollectRequest) -> None:
        """派发采集任务（立即返回）"""

    async def run_collect(self, req: DailyCollectRequest) -> None:
        """后台全生命周期：建日志 → 逐日采集 → 实时进度 → 终态"""

    async def _collect_by_date(self, day: date) -> DailyFetcherResult:
        """采集单个自然日：fetch → BO → repo.save()"""

    async def _retry(self, call):
        """重试包装"""

    # ❌ 没有 _save —— commit/rollback 交给 get_raw_db_context（D4）
    # ❌ 没有 _list_days —— 展开内联进 run_collect
    # ❌ 没有 _collect_range —— 取消（§0.4）
    # ❌ 没有 _collect_by_symbol —— 删除（D1）
```

**方法数 8 → 4**（`collect` / `run_collect` / `_collect_by_date` / `_retry`）。

### 3.2 `run_collect` —— 线性 `for` 循环

```python
    async def run_collect(self, req: DailyCollectRequest) -> None:
        """后台执行：建日志 → 逐日采集 → 实时进度 → 终态

        日志生命周期：
            1. create()          建日志（DB init + Redis init）
            2. update_status()   置 running（只写 Redis）
            3. update_progress() 过程中实时进度（只写 Redis）
            4. update()          终态（写 DB + 清 Redis）

        ★ 异常路径必须保证日志落到终态，否则会留下卡在 init 的孤儿日志。
        """
        log_id = await log_util.create(
            service_name=self.META.name,
            category=self.META.facet,
            action=self.META.kind.value,
            meta=req.model_dump(exclude_none=True, mode="json"),
            trigger_source="manual",
        )
        started_at = time.monotonic()

        try:
            await log_util.update_status(
                log_id, service_name=self.META.name, status="running",
            )

            # ── 展开时间范围为自然日列表 ──
            days: list[date] = []
            cur = req.start_date
            while cur <= req.end_date:
                days.append(cur)
                cur += timedelta(days=1)

            if not days:
                await log_util.update(
                    log_id,
                    service_name=self.META.name,
                    status="failed",
                    progress=0,
                    error=f"{req.start_date} ~ {req.end_date} 区间为空",
                    duration_ms=_elapsed_ms(started_at),
                )
                return

            total = len(days)
            ok_total = 0
            fail_total = 0
            saved_total = 0

            # ── 逐日采集 ──
            for i, day in enumerate(days, start=1):
                result = await self._collect_by_date(day)

                if result.ok:
                    ok_total += 1
                if result.fail:
                    fail_total += 1
                saved_total += result.rows

                # 实时进度（只写 Redis；失败不中断采集）
                await log_util.update_progress(
                    log_id,
                    service_name=self.META.name,
                    progress=int(i / total * 100),
                    saved_count=ok_total,
                    fail_count=fail_total,
                    total_count=total,
                )

            # ── 终态（写 DB + 清 Redis）──
            # 进度统一口径：已处理单元数 / 总单元数
            progress = min(100, int(total / total * 100))

            if fail_total == 0:
                status = "success"
            elif ok_total == 0:
                status = "failed"
            else:
                status = "partial_fail"

            await log_util.update(
                log_id,
                service_name=self.META.name,
                status=status,
                progress=100 if status != "failed" else progress,
                saved_count=ok_total,
                fail_count=fail_total,
                duration_ms=_elapsed_ms(started_at),
            )
            logger.info(
                "daily 完成: log_id=%s, status=%s, rows=%d, ok=%d,"
                " fail=%d, units=%d",
                log_id, status, saved_total, ok_total, fail_total, total,
            )

        except Exception as e:
            logger.exception("daily 采集失败: %r", e)
            try:
                await log_util.update(
                    log_id,
                    service_name=self.META.name,
                    status="failed",
                    progress=0,
                    error=str(e)[:500],
                    duration_ms=_elapsed_ms(started_at),
                )
            except Exception as e2:
                logger.error(
                    "log_util.update 失败（log_id=%s）: %r", log_id, e2,
                )
```

> **进度口径统一**：实时进度用 `i / total`（已处理单元数），终态进度用 `total / total = 100`。两处一致。

### 3.3 `_collect_by_date` —— 唯一采集方法

```python
    async def _collect_by_date(self, day: date) -> DailyFetcherResult:
        """采集单个自然日 → DailyFetcherResult

        链路：fetcher 取数 → KlineBO → repo.save(BO, session)

        ★ 事务边界由本方法决定（每个自然日一个事务），
          但 commit/rollback 的执行交给 get_raw_db_context() ——
          service 里不出现任何 commit()/rollback() 调用。
        """
        try:
            klines = await self._retry(
                lambda: self._fetcher.fetch_by_date(day),
            )
        except Exception as e:
            logger.exception("daily %s 失败: %r", day, e)
            return DailyFetcherResult(
                trade_date=day, rows=0, ok=False, fail=1, error=str(e),
            )

        if not klines:
            # 查不到数据 ≠ 失败（周末/节假日/停牌）
            return DailyFetcherResult(trade_date=day, rows=0, ok=False, fail=0)

        # ── 入库：事务边界在本方法，commit/rollback 由 context manager 负责 ──
        async with get_raw_db_context() as session:
            saved = await self._kline_repo.save_klines(klines, session)

        return DailyFetcherResult(trade_date=day, rows=saved, ok=True, fail=0)
```

**关键点**：
- service 里**没有** `commit()` / `rollback()` 调用 —— 全部由 `get_raw_db_context()` 承担
- `get_raw_db_context()` 正常退出 → `commit()`；抛异常 → `rollback()` 后重新抛出
- 每个自然日**一个独立事务** → 某天失败不影响其他天

### 3.4 事务边界：谁决定、谁执行

这是本轮最需要说清的一点。**「事务边界」和「事务执行」是两件事**：

| | 归属 | 本方案 |
|---|---|---|
| **事务边界**（一个用例 = 一个事务还是多个） | **application 层**（DDD 规范：`docs/backend-docs/config/DDD.md:86`「管事务边界」） | `_collect_by_date` 里 `async with get_raw_db_context()` 的缩进范围 = 一个自然日一个事务 |
| **事务执行**（commit / rollback 的实际调用） | **infrastructure 机制** | `get_raw_db_context()` 内部：`yield` 正常 → `commit()`；异常 → `rollback()` |

**`get_raw_db_context()` 已经是这个机制的实现**：

```78:89:D:\codes\Attribution_Analysis\backend\src\shared\infrastructure\di\db_session.py
@asynccontextmanager
async def get_raw_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Service 层独立事务用（采集库）"""
    async with raw_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

**所以 service 里只需要**：

```python
async with get_raw_db_context() as session:
    saved = await self._kline_repo.save_klines(klines, session)
```

**没有 `await session.commit()`，也没有 `await session.rollback()`** —— 这正是你要的效果。

#### 3.4.1 为什么不让 repo 自己管 session

考虑过的方案：`DailyKlineRepository.save_klines(klines)` 内部自开 session + commit。

**不采用**，三个理由：

| # | 理由 |
|---|---|
| 1 | **违背 DDD**：application 层的职责第一条就是「管事务边界」。repo 自管事务 = 把边界决策权交给 infrastructure，application 失去「一个用例是单事务还是多事务」的控制力 |
| 2 | **违背 collect context 既有约定**：`tech/__init__.py:7`「统一约定：session 由 service 层持有、以参数传入；repo 不自行开关事务」—— 25 个 repo 全部遵循 |
| 3 | **DI 注入的 session 活不过后台任务**：`get_raw_db` 是 FastAPI `Depends`，HTTP 请求结束就 close。而 daily 采集跑在后台 task 里（`collect()` 只 `asyncio.create_task`）。`collect_task_runner.py:124-128` 已经明确用 `session=None` 处理这个边界 |

#### 3.4.2 与 market context 的差异（不是矛盾）

| context | session 怎么来 | 为什么 |
|---|---|---|
| **market**（查询） | repo 构造时注入（`KlineRepoImpl.__init__(session)`） | 查询在 HTTP 请求内完成，session 活到请求结束没问题 |
| **collect**（后台采集） | service 自开 + 以参数传给 repo | 采集跑在后台 task，跨 HTTP 生命周期，必须自开 |

两个 context 的模式不同是**合理的**，由「请求内同步」vs「后台异步」决定，不是风格不统一。

#### 3.4.3 现状对比

| | 现在 | 目标 |
|---|---|---|
| session 在哪开 | `run_collect` 开**一次**，传给所有单元 | `_collect_by_date` **每个单元开一次** |
| 谁传给 repo | service 传 | service 传（**不变**） |
| repo 签名 | `save_klines(klines, session)` | **不变** |
| repo 自己开 session | ❌ | ❌ |
| service 里的 commit/rollback | `_save()` 里显式 `commit()`；`_retry()` 里显式 `rollback()` | **全部消失** |
| 事务粒度 | 全区间一个事务 | **每个自然日一个事务** |

**repo 文件 `daily_kline_repo.py` 一行都不用改** —— 符合你「调用定义好的 repo 的接口，传入 fetcher 获取的参数和 session」的要求。

### 3.5 `_retry` 的改造

**现状问题**：`_retry(call, session)` 内部 `await session.rollback()` —— 这是把事务管理塞进重试逻辑，且 rollback 的对象是**外部传入**的 session。

**目标**：`_retry` 只管重试，不管事务。

```python
    async def _retry(self, call):
        """最多重试 3 次；前两次失败等待 1 秒

        ★ 只管重试，不管事务 —— 事务由 get_raw_db_context() 统一处理。
          这里不碰 session（fetch 阶段还没进事务）。
        """
        for attempt in range(3):
            try:
                return await call()
            except Exception:
                if attempt < 2:
                    await asyncio.sleep(1)
                else:
                    raise
```

**注意**：`_retry` 只包住 **fetch 阶段**（还没开事务）。入库阶段不开事务 —— 出错就整个单元回滚。

### 3.6 `DailyFetcherResult`（新增，替代 `CollectUnitResult`）

```python
# contexts/collect/application/bo/tech.py

@dataclass(frozen=True)
class DailyFetcherResult:
    """单个自然日的采集结果

    ★ 用 model 而非裸元组 —— 裸元组的长度/含义会漂移，
      这正是当前 daily_service 线上报错的根因
      （_collect_by_date 返回 2 元组，调用方按 3 元组解包）。

    ★ 命名收窄到 Daily：先只针对 daily 跑通，
      不提前抽象成通用的 CollectUnitResult。
    """
    trade_date: date                      # 采集的自然日
    rows: int = 0                        # 实际入库行数
    ok: bool = False                     # 是否成功取到数据
    fail: int = 0                        # 失败数（0 或 1）
    error: str | None = None             # 失败原因

    @property
    def is_empty(self) -> bool:
        """查不到数据 ≠ 失败（周末/节假日/停牌都属空返回）"""
        return self.ok and self.rows == 0
```

**命名理由**：用户明确要求「这里叫 `DailyFetcherResult`」。

**为什么不叫 `CollectUnitResult`**：本轮只做 daily 一条线，泛化命名会暗示「这是一套通用机制」，但实际上其余 24 个 service 的采集单元语义完全不同（有的按 symbol，有的按 trade_date，有的按 concept_code）。**先跑通，再看是否值得抽象。**

**为什么用 dataclass 而不是 pydantic**：内部结构，不做外部输入校验，不需要 pydantic 的能力；dataclass 零依赖、frozen 保证不可变。

**为什么带 `trade_date`**：模型自带业务标识，不需要调用方从外部传回去。日志/排查时能直接看出是哪天失败。

**放在哪**：`collect/application/bo/tech.py`（与 `BaseAdjFactorBO` 等同类 BO 同文件），并在 `bo/__init__.py` 的 `__all__` 里加上。

### 3.7 「只针对 Daily 跑通」的边界（D6）

本轮**明确不做**的事，避免过早抽象：

| # | 不做的事 | 原因 |
|---|---|---|
| 1 | 不建 `CollectUnitResult` 通用基类 | 其余 24 个 service 的「采集单元」语义各异，无法共用 |
| 2 | 不改其余 24 个 service 的 `CollectResult` 用法 | `CollectResult` 是 REALTIME 兼容用的，与本轮无关 |
| 3 | 不改 `collect/application/port/params.py` 的通用 Params 模型 | 只删死代码，不新增 |
| 4 | 不做 `DailyFetcherResult` → `CollectUnitResult` 的继承预留 | 需要时再抽（YAGNI） |
| 5 | 不动 `ServiceMeta` / `ServiceKind` | 现有结构够用 |
| 6 | 不改 `log_util` | 日志生命周期机制已够用 |

**判定标准**：本轮改完后，`daily` 这条链路（route → DTO → service → fetcher → repo）能独立跑通，且**没有为其他 service 留下任何新的抽象负担**。

### 3.8 fetcher 收敛

```python
class DailyTushareFetcher:
    async def fetch_by_date(self, trade_date: date) -> list[KlineBO]:
        """拉取某个交易日的全市场日 K"""
        ...
```

**删除** `fetch_by_ts_code()` —— 唯一调用方是 `_collect_by_symbol`，本轮一并删除。

**连带删除** `START_BUFFER_DAYS` 常量（只被 `fetch_by_ts_code` 用）。

**保留** `_resolve_name()`？—— ⚠️ **本轮删除**。它只被 `fetch_by_ts_code` 调用，删了 `fetch_by_ts_code` 后就是死代码。同时删掉 `self._names` / `self._names_loaded` 两个实例属性。

**保留** `rows` / `symbol_to_ts_code` 等 parser 工具（其他 fetcher 在用）。

---

## 四、逐文件修改清单

### 4.1 后端主链路

| 文件 | 动作 | 预估行数变化 |
|---|---|---|
| `collect/application/service/tech/daily_service.py` | **重写** | 331 → ~270 |
| `collect/interface/dto/request/daily.py` | 修改（删 `ts_code`） | -8 |
| `collect/application/bo/tech.py` | 新增 `DailyFetcherResult` | +25 |
| `collect/infrastructure/fetcher/tech/DailyTushareFetcher.py` | 修改（删 `fetch_by_ts_code` / `_resolve_name` / `START_BUFFER_DAYS`） | -45 |
| `collect/infrastructure/persistence/repositories/tech/daily_kline_repo.py` | **不动**（§3.4.3：repo 签名不变） | ±0 |
| `collect/interface/route/tech/daily.py` | 修改（summary 文案） | ±1 |
| `collect/infrastructure/di/collect_service.py` | **不动** | ±0 |

### 4.2 死代码清理（D5）

见 §2.3 的 8 个文件。

### 4.3 下线坏路径

| 文件 | 动作 |
|---|---|
| `market/application/service/stock_info_service.py` | 删 `collect()` 方法 + `daily_svc` 构造参数 |
| `market/interface/route/kline.py` | 删 `/collect` + `/collect/batch` 两个路由 |
| `market/interface/dto/request/kline.py` | 删 `KlineCollectRequest` |
| `market/interface/dto/response/kline.py` | 删 `KlineCollectResponse` |
| `market/infrastructure/di/stock_info.py` | 删 `daily_svc` 相关（本来就没注入） |
| `user/infrastructure/di/stock_pool.py` | 删 `daily` 分支 + `_run_collect_one` 的 daily 特殊处理 |
| `user/infrastructure/adapter/background/operation_dispatcher.py` | 改 `dispatch_kline_collect` → 不再按 symbol 循环调 daily |
| `frontend/src/views/stock-info/api.ts` | 删 `/klines/collect` + `/klines/collect/batch` 调用 |

### 4.4 前端同步

| 文件 | 动作 |
|---|---|
| `views/collect-manage/components/CollectActionCard.vue` | 删除 ts_code 输入框 + 校验逻辑 + 更新文案 |
| `views/collect-manage/api.ts` | `DailyCollectPayload` 删 `ts_code` |
| `views/collect-manage/components/CollectTaskPane.vue` | 文案微调（`saved_count` 语义不变） |

### 4.5 数据库

**无变更**。表 `tech_daily` 结构不动，UK 仍是 `(symbol, date)`。

### 4.6 BO 归属修正（可选，单独 commit）

`KlineBO` 现在定义在 `market/application/bo/kline.py`，被 `collect` 的 infrastructure 引用：

```17:17:D:\codes\Attribution_Analysis\backend\src\contexts\collect\infrastructure\persistence\repositories\tech\daily_kline_repo.py
from contexts.market.application.bo.kline import KlineBO
```

**问题**：`collect`（infrastructure 层）反向依赖 `market`（application 层），违反 DDD §2.2「依赖方向严格自上而下」。

**⚠️ 风险**：`KlineBO.to_entity()` 引用 `market.domain.entities.kline.entity.Kline` —— 迁到 collect 后，collect 的 application 层会依赖 market 的 domain 层。

**建议**：**本轮先不做**，单独 commit 处理（连同 `to_entity()` / `from_entity()` 的去向一起决定）。

---

## 五、影响面清单

### 5.1 后端文件汇总

| 类别 | 文件数 | 文件 |
|---|---|---|
| **主链路重写** | 1 | `collect/application/service/tech/daily_service.py` |
| **主链路修改** | 5 | DTO、BO、fetcher、route、parser（若做 BO 迁移） |
| **死代码删除** | 8 | 见 §2.3 |
| **坏路径下线** | 8 | 见 §4.3 |

### 5.2 前端文件

| 文件 | 动作 |
|---|---|
| `views/collect-manage/components/CollectActionCard.vue` | 删代码输入框 |
| `views/collect-manage/api.ts` | 删 `ts_code` |
| `views/collect-manage/components/CollectTaskPane.vue` | 文案微调 |
| `views/stock-info/api.ts` | 删 K 线采集调用（若下线） |

### 5.3 数据库

**无变更**。

---

## 六、实施建议

### 6.1 推荐拆成 4 个 commit

| Commit | 内容 | 风险 | 可独立验证 |
|---|---|---|---|
| **C1** | **核心重构**：`DailyFetcherResult` 新增；重写 `daily_service.py`（删 `ts_code` 分支、删 `_list_days`、删 `_collect_range`、删 `_collect_by_symbol`、删 `_save`、内联展开、每单元独立事务、去掉 service 里的 commit/rollback、统一进度口径）；DTO 删 `ts_code`；fetcher 删 `fetch_by_ts_code` | 低 | ✅ daily 采集能跑通，日志正常 |
| **C2** | **前端同步**：`CollectActionCard.vue` 删代码输入框、`api.ts` 删 `ts_code` | 低 | ✅ 前端能触发 |
| **C3** | **死代码清理**（§2.3，8 个文件） | 低 | ✅ import 脚本通过 |
| **C4** | **坏路径下线**（§4.3，8 个文件 + 前端 1 个） | 中 | ⚠️ 需确认 Q1/Q2 |

**BO 归属修正（§4.6）单独 C5**。

### 6.2 最小可交付路径

如果只想**快速修好线上报错**，最小集是：

1. `collect/application/bo/tech.py` 加 `DailyFetcherResult`
2. `daily_service.py` 的 `_collect_by_date` 返回 `DailyFetcherResult`（**session 仍在 run_collect 传**，先不动）
3. `daily_service.py` 的 `one()` 不再解包，改用属性访问
4. `daily_service.py` 删掉 `req.ts_code` 分支 + `_collect_by_symbol`

这 4 步就能让 daily 跑起来，且 DTO/fetcher/前端都还兼容旧字段（前端多传 `ts_code` 会被 DTO 忽略）。

### 6.3 验证清单

| # | 验证项 | 方法 |
|---|---|---|
| 1 | 区间采集能跑通 | `POST /api/collect/tech/daily` `{start_date, end_date}` → 查 `collect_logs` |
| 2 | 不再报解包错误 | 日志中无 `not enough values to unpack` |
| 3 | 空返回天不算失败 | 选一个含周末的区间 → `fail_count` 应为 0（周末），`total_count` = 自然日数 |
| 4 | 进度条走完 | `progress` 到 100 |
| 5 | 入库行数正确 | 查 `tech_daily` 该区间的行数 ≈ 交易日数 × 股票数 |
| 6 | 前端能触发 | 采集管理页 daily 卡片 → 开始采集 → 进度卡片实时更新 |
| 7 | 前端不再有代码输入框 | 截图确认 |
| 8 | 死代码清理后 import 正常 | 跑 `backend/scripts/verify_collect_layers.py` |
| 9 | `import *` 不炸 | `from contexts.market.application.bo.kline import *` 能跑通（DC-6 修复验证） |

---

## 七、待确认问题

| # | 问题 | 影响 | 建议 |
|---|---|---|---|
| **Q1** | `StockInfoService.collect()` / `POST /api/v1/klines/collect` 怎么办？ | 决定 C4 范围；前端 `stock-info` 页面有入口 | **下线**（当前必 500），前端按钮一并移除 |
| **Q2** | 自选股池的「采集 K 线」功能保留吗？ | 决定 `stock_pool` / `operation_dispatcher` 改法 | **改为调一次全市场 daily**，不按 symbol 循环 |
| **Q3** | BO 归属修正（`KlineBO` 迁到 collect）本轮做吗？ | 决定是否加 C5 | **单独 commit**，不混主线 |
| **Q4** | `DailyCollectRequest` 要不要加跨度上限（如 max 366 天）？ | 影响大区间误操作保护 | **加**，防止一次请求打爆 Tushare 配额 |
| **Q5** | `saved_count` 保持「成功天数」还是改成「入库行数」？ | 影响前端 3 处文案 | **保持「成功天数」**（前端已适配） |
| **Q6** | 死代码清理里 `StockBasicParams` / `TradeDateParams` / `MinuteKlineParams`（port 版）确认删吗？ | C3 范围 | **删**（已确认无调用方） |

---

## 附录 A：改造后的 `daily_service.py` 完整骨架

> 结构预览用；实际以 C1 实施为准。

```python
"""DailyService — 日 K 线采集 service

v12（2026-10-27）—— 只保留时间范围采集：
    - 删除 ts_code 单股分支（唯一调用方 StockInfoService / stock_pool 已下线）
    - 删除 _list_days（自然日展开内联进 run_collect）
    - 删除 _collect_range（并发恒为 1，改为线性 for 循环）
    - 删除 _save（commit/rollback 交给 get_raw_db_context）
    - 单元结果改用 DailyFetcherResult model（替代裸元组，修掉解包崩溃）
    - 每个采集单元一个独立事务（get_raw_db_context）
    - 进度口径统一为「已处理单元数 / 总单元数」
    - 入库逻辑在 repo（_to_row 映射 + upsert），service 只调 repo 接口

日志生命周期：
    1. log_util.create()          → 建日志（DB init + Redis init）
    2. log_util.update_status()   → 改状态（只写 Redis）
    3. log_util.update_progress() → 采集过程中的实时进度（只写 Redis）
    4. log_util.update()          → 终态（写 DB + 清 Redis）
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, timedelta

from contexts.collect.application.bo.tech import DailyFetcherResult
from contexts.collect.application.service.base import ServiceKind, ServiceMeta
from contexts.collect.infrastructure.fetcher.tech.DailyTushareFetcher import (
    DailyTushareFetcher,
)
from contexts.collect.infrastructure.persistence.repositories.tech import (
    DailyKlineRepository,
)
from contexts.collect.interface.dto.request.daily import DailyCollectRequest
from shared.infrastructure.di.db_session import get_raw_db_context
from shared.infrastructure.log_util import log_util

logger = logging.getLogger(__name__)


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)


class DailyService:
    """日 K 线采集服务（按时间范围采集全市场）"""

    META = ServiceMeta(
        name="daily",
        facet="tech",
        label="日 K 线",
        description="Tushare pro.daily 日 K 线（按时间范围采集）",
        kind=ServiceKind.INCREMENTAL,
        concurrency=1,
    )

    def __init__(
        self,
        fetcher: DailyTushareFetcher | None = None,
        kline_repo: DailyKlineRepository | None = None,
    ) -> None:
        self._fetcher = fetcher or DailyTushareFetcher()
        self._kline_repo = kline_repo or DailyKlineRepository()
        self._tasks: set[asyncio.Task] = set()

    # ── HTTP 入口：派发后台任务 ──
    async def collect(self, req: DailyCollectRequest) -> None:
        task = asyncio.create_task(self.run_collect(req))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    # ── 后台全生命周期 ──
    async def run_collect(self, req: DailyCollectRequest) -> None:
        ...

    # ── 单日采集（唯一采集方法）──
    async def _collect_by_date(self, day: date) -> DailyFetcherResult:
        ...

    # ── 重试（只管重试，不管事务）──
    async def _retry(self, call):
        ...


__all__ = ["DailyService"]
```

## 附录 B：关键代码位置索引

| 关注点 | 文件:行 |
|---|---|
| 解包崩溃点 | `daily_service.py:256` |
| session 并发共用 | `daily_service.py:125-126` + `:323-327` |
| 进度口径矛盾 | `daily_service.py:155-158` vs `:266` |
| `ts_code` 分支 | `daily_service.py:127-131` |
| `_list_days` | `daily_service.py:221-229` |
| `_collect_all_days` | `daily_service.py:231-277` |
| `_collect_by_symbol` | `daily_service.py:279-297` |
| `_collect_by_date`（返回 2 元组） | `daily_service.py:300-309` |
| BO→ORM 映射（唯一映射点） | `daily_kline_repo.py:90-106` |
| repo 批量 upsert | `daily_kline_repo.py:46-63` |
| DTO 定义 | `dto/request/daily.py:8-26` |
| repo 统一约定（session 由 service 传） | `tech/__init__.py:7` |
| `__all__` 潜在 bug | `market/application/bo/kline.py:120-124` |
| 前端代码输入框 | `CollectActionCard.vue:35-45` + `:160-168` + `:173-180` |
| 前端 payload 类型 | `api.ts:68-72` |
| 前端 daily 语义注释 | `CollectTaskPane.vue:89-95` |
| `StockInfoService.collect` | `stock_info_service.py:209-236` |
| `daily_svc` 未注入 | `market/infrastructure/di/stock_info.py:45-57` |
| `stock_pool` daily 分支 | `user/infrastructure/di/stock_pool.py:39-40` + `:62-70` |
| collect repo 统一约定 | `tech/__init__.py:7` |
