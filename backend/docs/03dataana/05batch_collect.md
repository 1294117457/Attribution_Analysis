# 并发批量采集方案设计

## 1. 现状分析

### 1.1 当前采集流程

以日K线采集为例，当前处理链条为严格串行：

```
for symbol in symbols:       # 逐只遍历
    fetcher.fetch(params)    # Tushare API 调用 (~300ms, 同步, asyncio.to_thread 包装)
    → indicator 计算          # CPU 计算 (~5ms)
    → repo.save_batch()      # DB UPSERT (~20ms)
    → redis 更新进度          # (~1ms)
```

**相关代码位置：**

| 文件 | 职责 |
|------|------|
| `route/api/v1/collect_task.py` → `_collect_daily_kline()` | 采集调度循环 |
| `application/kline_service.py` → `KlineAppService.collect()` | 单只股票采集+指标+入库 |
| `infrastructure/collectors/tushare/fetcher.py` → `TushareFetcher.fetch()` | Tushare API 调用（同步） |

### 1.2 性能瓶颈

| 阶段 | 耗时 | 阻塞方式 | 说明 |
|------|------|---------|------|
| Tushare API | ~300ms/只 | 网络 I/O | 等待远程响应，CPU 空闲 |
| 指标计算 | ~5ms/只 | CPU | pandas 运算 |
| DB UPSERT | ~20ms/只 | 磁盘 I/O | 批量写入 PostgreSQL |
| Redis 更新 | ~1ms/只 | 网络 I/O | HSET 单次 |

> **关键发现**：~92% 的时间花在 Tushare API 等待上，属于纯 I/O 等待。串行模式下 CPU 大部分时间空闲。

### 1.3 当前性能基准

| 场景 | 股票数 | 串行耗时（估算） | 瓶颈 |
|------|--------|----------------|------|
| SSE 日K 1天 | ~2300 | ~19 min | Tushare I/O |
| 全市场日K 1天 | ~5300 | ~44 min | Tushare I/O |
| 全市场日K 30天 | ~5300 | ~44 min | 同上（单次返回多天数据） |

---

## 2. Tushare 限流约束

Tushare API 有严格的频率限制，是并发度设计的硬约束：

| 积分等级 | `daily()` 频率限制 | 推荐并发度 |
|---------|-------------------|-----------|
| 120+ 积分 | ~200 次/分钟 (~3.3 次/秒) | 2-3 |
| 2000+ 积分 | ~500 次/分钟 (~8.3 次/秒) | 4-5 |
| 5000+ 积分 | ~800 次/分钟 (~13 次/秒) | 6-8 |

> **注意**：超出限制会返回 `抱歉，您每分钟最多访问该接口N次` 错误，不是 HTTP 429，而是正常 200 响应但 DataFrame 为空或报文异常。

---

## 3. 并发方案设计

### 3.1 核心思路

```
                    ┌──────────────────────────┐
                    │  _collect_daily_kline()   │
                    │  (采集调度器)              │
                    └─────────┬────────────────┘
                              │
                    symbols 按 chunk 分组
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ worker 1 │   │ worker 2 │   │ worker 3 │
        │ symbol A │   │ symbol B │   │ symbol C │
        └──────────┘   └──────────┘   └──────────┘
              │               │               │
              │  asyncio.Semaphore(N) 控制并发  │
              │  asyncio.to_thread 执行同步 API │
              │               │               │
              ▼               ▼               ▼
        ┌─────────────────────────────────────────┐
        │          DB Session (每 worker 独立)      │
        │          Redis 进度 (HINCRBY 原子更新)    │
        └─────────────────────────────────────────┘
```

### 3.2 并发控制策略

采用 `asyncio.Semaphore` + chunk 两级控制：

- **Semaphore(N)**：全局并发上限，确保同一时刻最多 N 个 Tushare API 调用
- **chunk 分组**：每 chunk_size 只股票为一组，chunk 内并发执行，chunk 之间串行
- **间隔控制**：每个 worker 在 API 调用后 sleep，平滑请求频率

**并发度由前端用户选择，后端配置提供默认值和上限。**

```
concurrency = min(用户选择值, 后端最大上限)
chunk_size = 30           # 每 chunk 股票数
api_interval = 自动计算    # 根据并发度动态调整
```

### 3.3 并发度前端选择设计

#### 3.3.1 前端交互

在 `CollectManage.vue` 的可折叠筛选区（日K线 Tab）中，新增并发度选择器：

```
┌─────────────────────────────────────────────────────────┐
│ 采集条件 ▼                                               │
│                                                          │
│ [全部交易所 ▼]  [开始日期 — 结束日期]  [按日期采集]         │
│ [并发度: ● 1(串行) ○ 2 ○ 3(推荐) ○ 5 ]                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

使用 `el-radio-group` 提供固定档位，而非自由输入数字，避免用户误设过高值触发限流：

| 档位 | 值 | 说明 | 适用场景 |
|------|---|------|---------|
| 串行 | 1 | 最安全，无限流风险 | 低积分用户 / 调试 |
| 2 | 2 | 温和并发 | 120+ 积分 |
| 3（推荐） | 3 | 默认推荐 | 120+ 积分 |
| 5 | 5 | 较高并发 | 2000+ 积分 |
| 8 | 8 | 高并发 | 5000+ 积分 |

```vue
<!-- CollectManage.vue 可折叠筛选区新增 -->
<div class="filter-item">
  <span class="filter-label">并发度</span>
  <el-radio-group v-model="klineConcurrency" size="small">
    <el-radio-button :value="1">1 (串行)</el-radio-button>
    <el-radio-button :value="2">2</el-radio-button>
    <el-radio-button :value="3">3 (推荐)</el-radio-button>
    <el-radio-button :value="5">5</el-radio-button>
    <el-radio-button :value="8">8</el-radio-button>
  </el-radio-group>
</div>
```

```typescript
// CollectManage.vue script
const klineConcurrency = ref(3)   // 默认 3
```

#### 3.3.2 参数传递

并发度通过 `params.concurrency` 传入创建任务 API，与 exchange / date_range 同级：

```typescript
// 前端 startKline 调用
function startKline(base: Record<string, any>) {
  const params = { ...base }
  if (klineExchange.value.length > 0) params.exchange = [...klineExchange.value]
  params.concurrency = klineConcurrency.value   // 新增
  startTask('daily_kline', params)
}
```

API 请求体示例：
```json
{
  "task_type": "daily_kline",
  "params": {
    "start_date": "20250909",
    "end_date": "20261023",
    "exchange": ["SSE"],
    "concurrency": 3
  }
}
```

#### 3.3.3 后端安全约束

后端从 `params` 读取 `concurrency`，但强制 clamp 到 `[1, COLLECT_MAX_CONCURRENCY]` 范围：

```python
# collect_task.py → _collect_daily_kline()
settings = get_settings()
max_concurrency = settings.COLLECT_MAX_CONCURRENCY   # 后端硬上限，默认 8
user_concurrency = params.get("concurrency", settings.COLLECT_CONCURRENCY)
concurrency = max(1, min(int(user_concurrency), max_concurrency))
```

这样即使前端传入异常值（比如 100），后端也会限制到安全范围。

#### 3.3.4 API 间隔自动调整

不同并发度对应不同的 API 调用间隔，避免触发 Tushare 限流：

```python
# 根据并发度动态计算间隔
# 目标: 总请求频率不超过 ~3 次/秒 (120+ 积分安全线)
api_interval = max(0.1, concurrency * 0.15)
```

| 并发度 | api_interval | 总请求频率 | 安全性 |
|--------|-------------|-----------|--------|
| 1 | 0.15s | ~3.3/秒 | 120+ 积分安全 |
| 2 | 0.30s | ~3.3/秒 | 120+ 积分安全 |
| 3 | 0.45s | ~3.3/秒 | 120+ 积分安全 |
| 5 | 0.75s | ~3.3/秒 | 120+ 积分安全 |
| 8 | 1.20s | ~3.3/秒 | 120+ 积分安全 |

> 此策略保持总请求频率恒定（~3/秒），并发度越高意味着更多"同时等待"的请求，但每个请求之间的发送间隔更长。实际吞吐量的提升来自 I/O 等待的重叠。

#### 3.3.5 进度展示中显示并发度

前端进度展开行中显示当前任务的并发度，方便用户了解：

```
已完成 120 / 2901   成功 118   失败 2   并发 ×3   当前: 000029
▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░  4.1%
```

可从 `task.params.concurrency` 读取，无需额外 API。

### 3.4 改动范围

**后端**（修改 2 个文件）：

| 文件 | 改动 |
|------|------|
| `infrastructure/config.py` | 新增 `COLLECT_CONCURRENCY`, `COLLECT_MAX_CONCURRENCY` |
| `route/api/v1/collect_task.py` → `_collect_daily_kline()` | 读取 `params.concurrency`，引入 Semaphore 并发 |

**前端**（修改 1 个文件）：

| 文件 | 改动 |
|------|------|
| `views/collect-manage/CollectManage.vue` | 筛选区新增并发度 radio-group，startKline 传参，进度行显示并发度 |

**不修改**：
- `KlineAppService.collect()` — 单只股票逻辑不变
- `TushareFetcher.fetch()` — API 调用逻辑不变
- `FetcherProtocol` 接口 — 不变
- `api.ts` — `createTask` 接口签名不变（params 本身就是 `Record<string, any>`）
- 前端轮询逻辑 — `TaskProgress` 类型不变

### 3.5 新增配置项

在 `infrastructure/config.py` 的 `Settings` 中新增：

```python
# 采集并发
COLLECT_CONCURRENCY: int = 3          # 前端未传时的默认并发数
COLLECT_MAX_CONCURRENCY: int = 8      # 后端允许的最大并发数（硬上限）
COLLECT_CHUNK_SIZE: int = 30          # chunk 大小
```

通过环境变量 / .env 覆盖。`COLLECT_MAX_CONCURRENCY` 作为安全阀，防止前端传入过大值。

---

## 4. 详细实现方案

### 4.1 改造后的 `_collect_daily_kline`

```python
async def _collect_daily_kline(task_id: int, params: dict):
    settings = get_settings()
    max_conc = settings.COLLECT_MAX_CONCURRENCY       # 硬上限，默认 8
    user_conc = params.get("concurrency", settings.COLLECT_CONCURRENCY)
    concurrency = max(1, min(int(user_conc), max_conc))  # clamp [1, max]
    api_interval = max(0.1, concurrency * 0.15)          # 动态间隔
    chunk_size = settings.COLLECT_CHUNK_SIZE              # 默认 30

    days = params.get("days", 7)
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    exchange_filter: list[str] | None = params.get("exchange")
    redis = await get_redis()

    logger.info("日K采集任务 %d 参数: 并发=%d (用户请求=%s, 上限=%d), 间隔=%.2fs",
                task_id, concurrency, user_conc, max_conc, api_interval)

    # 1. 获取股票列表
    async with AsyncSessionLocal() as session:
        stmt = select(StockInfoDB.symbol).where(StockInfoDB.list_status == "L")
        if exchange_filter:
            stmt = stmt.where(StockInfoDB.exchange.in_(exchange_filter))
        result = await session.execute(stmt.order_by(StockInfoDB.symbol))
        symbols = [r[0] for r in result.all()]

    # 2. 初始化进度
    total = len(symbols)
    await redis.hset(f"collect:progress:{task_id}", "total", str(total))

    # 3. 构造采集参数
    collect_kwargs: dict = {}
    if start_date and end_date:
        collect_kwargs["start_date"] = date(...)
        collect_kwargs["end_date"] = date(...)
    else:
        collect_kwargs["days"] = days

    fetcher = _get_tushare_fetcher()
    sem = asyncio.Semaphore(concurrency)
    success = fail = 0
    _lock = asyncio.Lock()   # 保护 success/fail 计数器
    start_time = time.time()

    # 4. 单只股票采集协程
    async def _collect_one(symbol: str) -> bool:
        nonlocal success, fail
        async with sem:
            # 取消检查
            if task_id in _cancel_flags:
                return False

            try:
                async with AsyncSessionLocal() as session:
                    svc = KlineAppService(session=session)
                    await svc.collect(
                        KlineCollectRequest(symbol=symbol, **collect_kwargs),
                        fetcher,
                    )
                    await session.commit()

                async with _lock:
                    success += 1
            except Exception as e:
                logger.warning("任务 %d 采集 %s 失败: %s", task_id, symbol, e)
                async with _lock:
                    fail += 1

            # 原子更新 Redis 进度
            pipe = redis.pipeline()
            pipe.hincrby(f"collect:progress:{task_id}", "done", 1)
            pipe.hset(f"collect:progress:{task_id}", "current", symbol)
            await pipe.execute()

            # API 限流间隔
            await asyncio.sleep(api_interval)
            return True

    # 5. 分 chunk 并发执行
    for i in range(0, total, chunk_size):
        if task_id in _cancel_flags:
            _cancel_flags.discard(task_id)
            await _finish_task(task_id, "cancelled", success=success, fail=fail,
                               message=f"已取消: 成功 {success}, 失败 {fail}")
            await redis.hset(f"collect:progress:{task_id}", "status", "cancelled")
            return

        chunk = symbols[i:i + chunk_size]
        batch_idx = i // chunk_size + 1
        total_batches = (total + chunk_size - 1) // chunk_size
        logger.info("任务 %d 批次 %d/%d (%d只, 并发%d)",
                     task_id, batch_idx, total_batches, len(chunk), concurrency)

        # chunk 内并发
        await asyncio.gather(*[_collect_one(s) for s in chunk])

        # 同步 Redis 精确计数（修正 HINCRBY 可能的偏差）
        await redis.hset(f"collect:progress:{task_id}", mapping={
            "done": str(success + fail),
            "success": str(success),
            "fail": str(fail),
        })

        elapsed_so_far = time.time() - start_time
        rate = (success + fail) / elapsed_so_far if elapsed_so_far > 0 else 0
        logger.info("任务 %d 进度: %d/%d (成功%d 失败%d) %.1f只/秒",
                     task_id, success + fail, total, success, fail, rate)

    # 6. 完成
    elapsed = int((time.time() - start_time) * 1000)
    status = "success" if fail == 0 else ("failed" if success == 0 else "success")
    msg = f"完成: 成功 {success}, 失败 {fail}, 耗时 {elapsed // 1000}s"
    await _finish_task(task_id, status, success=success, fail=fail,
                       duration_ms=elapsed, message=msg)
    await redis.hset(f"collect:progress:{task_id}", "status", status)
```

### 4.2 关键设计决策

#### 4.2.1 每个 worker 独立 Session

```python
# 当前（共享 session，串行安全）：
async with AsyncSessionLocal() as session:
    svc = KlineAppService(session=session)
    for symbol in batch:
        await svc.collect(...)   # 串行，共享 session 没问题
    await session.commit()       # 统一提交

# 改造后（独立 session，并发安全）：
async def _collect_one(symbol):
    async with AsyncSessionLocal() as session:     # 每个协程独立 session
        svc = KlineAppService(session=session)
        await svc.collect(...)
        await session.commit()                     # 各自提交
```

**原因**：SQLAlchemy 的 `AsyncSession` 不是线程/协程安全的，并发协程不能共享同一个 session。

**DB 连接池影响**：当前配置 `DB_POOL_SIZE=10, DB_MAX_OVERFLOW=20`，并发 3 个 worker 各持一个连接，完全在池容量内。

#### 4.2.2 Redis 进度用 HINCRBY 原子更新

```python
# 当前（HSET 覆盖写，串行安全）：
await redis.hset(f"collect:progress:{task_id}", mapping={
    "done": str(success + fail),
    "success": str(success),
    "fail": str(fail),
    "current": symbol,
})

# 改造后（HINCRBY 原子递增，并发安全）：
pipe = redis.pipeline()
pipe.hincrby(f"collect:progress:{task_id}", "done", 1)
pipe.hset(f"collect:progress:{task_id}", "current", symbol)
await pipe.execute()
```

**补充**：每个 chunk 结束后用 `HSET` 覆盖写精确值，修正可能的累积偏差。

#### 4.2.3 asyncio.Lock 保护计数器

`success` / `fail` 是协程间共享的 int 变量。虽然 CPython 的 GIL 使 `+= 1` 在大多数情况下是安全的，但在 async 上下文中，规范做法是用 `asyncio.Lock`：

```python
_lock = asyncio.Lock()

async with _lock:
    success += 1
```

#### 4.2.4 取消信号传播

chunk 级别检查 `_cancel_flags`（和当前一致），同时 `_collect_one` 内部也检查。worker 检测到取消后直接 return，`asyncio.gather` 等剩余 worker 完成后在 chunk 循环检查到取消标记，执行清理。

---

## 5. `_collect_daily_basic` 并发改造

`daily_basic` 的采集对象是日期（而非股票），每次调用 `fetcher.fetch_daily_basic(date)` 获取全市场某天的估值数据。由于通常只有 1~7 个日期，并发收益有限，但模式可以统一。

```python
# 当前串行：
for d in dates:
    bo_list = await asyncio.to_thread(fetcher.fetch_daily_basic, d)
    ...

# 改造（如 dates > 3，开启并发）：
if len(dates) <= 3:
    # 串行即可
    ...
else:
    sem = asyncio.Semaphore(3)
    async def _fetch_one(d): ...
    await asyncio.gather(*[_fetch_one(d) for d in dates])
```

**优先级低**：大部分使用场景是"同步今日"(1天) 或"近7天"(7天)，串行总耗时不超过 30 秒。

---

## 6. 预期性能提升

### 6.1 日K线采集（2901 只，SSE 全市场）

| 方案 | 并发度 | API间隔 | 估算耗时 | 相对加速 |
|------|--------|---------|---------|---------|
| 当前串行 | 1 | 0s（无间隔，但串行自然限流） | ~24 min | 1x |
| Semaphore(2) | 2 | 0.35s | ~12 min | 2x |
| Semaphore(3) | 3 | 0.35s | ~8 min | 3x |
| Semaphore(5) | 5 | 0.25s | ~5 min | 5x |

> 实际提速取决于 Tushare 积分等级。建议从 `COLLECT_CONCURRENCY=3` 开始，观察是否触发限流后再调整。

### 6.2 资源消耗评估

| 资源 | 并发=3 时消耗 | 现有容量 | 是否安全 |
|------|-------------|---------|---------|
| DB 连接 | 3 个并发 + 1 个空闲 | pool_size=10, overflow=20 | 安全 |
| 线程池 | 3 个 `to_thread` 线程 | 默认 min(32, cpu+4) | 安全 |
| 内存 | 每只 ~1MB DataFrame | 3 × 1MB = 3MB 峰值 | 安全 |
| Redis | HINCRBY + HSET 管道 | 单实例足够 | 安全 |

---

## 7. 实施步骤

### Step 1: 后端 — 新增配置项
- 文件：`infrastructure/config.py`
- 新增：`COLLECT_CONCURRENCY: int = 3`、`COLLECT_MAX_CONCURRENCY: int = 8`、`COLLECT_CHUNK_SIZE: int = 30`

### Step 2: 后端 — 改造 `_collect_daily_kline`
- 文件：`route/api/v1/collect_task.py`
- 从 `params.get("concurrency")` 读取用户选择，clamp 到 `[1, max]`
- 引入 Semaphore + asyncio.gather + 独立 session + Redis pipeline
- 动态计算 `api_interval = max(0.1, concurrency * 0.15)`
- 保持 chunk 分组和取消检查逻辑

### Step 3: 前端 — 可折叠筛选区增加并发度选择
- 文件：`views/collect-manage/CollectManage.vue`
- 日K线 Tab 的可折叠筛选区新增 `el-radio-group`（档位 1/2/3/5/8）
- 新增 `klineConcurrency` ref，默认 3
- `startKline` 将 `concurrency` 写入 params
- 展开行进度区域显示 `并发 ×N`（从 `task.params.concurrency` 读取）

### Step 4: 可选 — 改造 `_collect_daily_basic`
- 文件：`route/api/v1/collect_task.py`
- 当 dates > 3 时启用并发（优先级低）

### Step 5: 测试验证
- 小规模测试：选 BSE（~200只），分别用并发 1 和 3 验证正确性
- 限流测试：并发 5 观察 Tushare 是否报错
- 压力测试：全市场采集，对比串行耗时
- 取消测试：并发采集中触发取消，验证清理正确性
- 前端测试：切换不同档位，确认参数正确传递和任务参数列显示

---

## 8. 回滚方案

设 `COLLECT_CONCURRENCY=1` 即退化为串行模式，行为与改造前完全一致。无需代码回滚。

---

## 9. 不涉及的改动

| 模块 | 说明 |
|------|------|
| `KlineAppService.collect()` | 单只股票采集逻辑不变 |
| `TushareFetcher.fetch()` | API 调用逻辑不变 |
| `FetcherProtocol` 接口 | 不修改 |
| `api.ts` | `createTask` 签名不变（params 本身就是 `Record<string, any>`） |
| 前端轮询逻辑 | `pollOnce` / `TaskProgress` 类型不变 |
| DB 表结构 | 不变（`params` 字段为 JSON，自动包含 concurrency） |
| Redis 数据结构 | key/field 不变，仅写入方式变更（HSET → HINCRBY） |
| `_collect_daily_basic` / `_collect_stock_basic` | 本次不改（可选后续迭代） |
