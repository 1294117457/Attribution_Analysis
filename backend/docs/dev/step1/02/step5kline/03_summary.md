# Step 5 K 线 + AI 归因分析 — 实施总结文档

> 本文档是 step5kline（K 线展宽 + AI 归因接口）的整体实现总结。
> 配套阅读：
> - [01_backend.md](./01_backend.md) — 后端详细设计
> - [02_frontend.md](./02_frontend.md) — 前端详细设计

---

## 1. 整体目标

把当前 `daily_klines` 表从 **「只存 OHLC」** 升级为 **「K 线 + 17 个技术指标」** 的一行结构（方案 A 展宽），并新增 `/stocks/{symbol}/analysis` 接口，一次返回：

- 股票基本信息
- K 线 + 17 个指标列
- 技术形态摘要（后端 SignalDetector 算好的金叉 / 超买 / 突破等）
- 所在操作池

让前端图表组件和后续 AI Agent 用同一个端点消费同一份数据，避免前端来回拼装。

---

## 2. 架构总览

```
┌──────────────────────────────────────────────────────────────────┐
│                    前端 (Vue 3 + TypeScript)                      │
│                                                                  │
│  ┌─────────────┐    ┌──────────────────┐    ┌────────────────┐  │
│  │ StockPanel  │    │ AnalysisMainView │    │  Pinia kline    │  │
│  │ (抽屉三 Tab)│───▶│ (独立分析页)     │───▶│  store + 缓存  │  │
│  └─────────────┘    └──────────────────┘    └────────────────┘  │
│         │                     │                       │          │
│         └─────────────┬───────┴───────────────────────┘          │
│                       ▼                                          │
│              api.ts : getStockAnalysis / getKlines / collectKlines│
└────────────────────────┬─────────────────────────────────────────┘
                         │  HTTP (Axios)
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI + SQLAlchemy 2.0)                │
│                                                                  │
│  route/api/v1/stock_analysis.py          route/api/v1/kline.py    │
│          │                                       │                │
│          ▼                                       ▼                │
│  application/stock_analysis_service.py   application/kline_service│
│          │                                       │                │
│          │                                       ▼                │
│          │           application/signals.py ←─────┘               │
│          │                                       │                │
│          ▼                                       ▼                │
│  infrastructure/indicators/calculator.py   domain/kline/entity.py │
│  (MA / EMA / MACD / RSI / KDJ / BOLL)              │              │
│                                                    ▼              │
│                         infrastructure/repositories/kline_repo.py│
│                                        │                          │
│                                        ▼                          │
│                  PostgreSQL: daily_klines (OHLC + 17 指标)        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 后端实现

### 3.1 数据模型：`DailyKlineDB` 展宽 17 个指标列

`src/infrastructure/database/models/kline.py`

```python
class DailyKlineDB(Base, TimestampMixin):
    __tablename__ = "daily_klines"
    # 基础 OHLC + 业务字段
    id, symbol, name, date, open, high, low, close, volume, amount, change_pct
    # 均线
    ma5, ma10, ma20, ma60
    # EMA
    ema12, ema26
    # MACD
    macd_dif, macd_dea, macd_bar
    # RSI
    rsi6, rsi12, rsi24
    # KDJ
    kdj_k, kdj_d, kdj_j
    # BOLL
    boll_up, boll_mid, boll_dn
```

**展宽决策**：方案 A 而不是 B（独立 `technical_indicators` 表）

| 维度 | 方案 A（展宽） | 方案 B（独立表） | 取舍 |
|------|----------------|------------------|------|
| 写 | 一次 INSERT/UPDATE | 两表写入 + JOIN | ✅ A 简单 |
| 读 | 单表 SELECT | 多表 JOIN | ✅ A 快 |
| 存储 | ~150 字节/行 ≈ 4500 万股 6.6 GB | 拆表空间略省 | ✅ A 可接受 |
| 灵活性 | 加列要 DDL | 加表不阻塞 | ⚠️ B 更灵活 |

### 3.2 自动迁移（无需 alembic）

`src/main.py` 在 `lifespan` 启动钩子里追加了 17 条 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...`：

```python
async def _migrate_daily_klines_indicators(conn) -> None:
    indicator_columns = [
        "ALTER TABLE daily_klines ADD COLUMN IF NOT EXISTS ma5 DOUBLE PRECISION",
        "ALTER TABLE daily_klines ADD COLUMN IF NOT EXISTS ma10 DOUBLE PRECISION",
        ...
        "ALTER TABLE daily_klines ADD COLUMN IF NOT EXISTS boll_dn DOUBLE PRECISION",
    ]
    for stmt in indicator_columns:
        await conn.execute(text(stmt))
```

幂等 + 启动时自动执行，无需手动 alembic 升级。

### 3.3 指标计算器

`src/infrastructure/indicators/calculator.py` — `IndicatorCalculator`

只依赖 `pandas`，不引入 `pandas_ta` / `TA-Lib`。计算 17 个指标，方法签名：

```python
class IndicatorCalculator:
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame
    def enrich_klines(self, klines: list, df: pd.DataFrame | None = None) -> dict
```

指标公式：

| 指标 | 公式 | 窗口 |
|------|------|------|
| MA  | `close.rolling(N).mean()` | N = 5/10/20/60 |
| EMA | `close.ewm(span=N, adjust=False).mean()` | 12 / 26 |
| MACD | `EMA12 - EMA26`, `EMA(DIF, 9)`, `2*(DIF-DEA)` | 12/26/9 |
| RSI | EWM 平滑涨 / 跌 比例 → 100 - 100/(1+RS) | 6/12/24 |
| KDJ | `RSV = (close-low9)/(high9-low9)*100`, `K/D` EWM 平滑 | 9/3/3 |
| BOLL | `mid ± 2σ` | 20 / 2σ |

### 3.4 采集即算指标

`src/application/kline_service.py` — `KlineAppService.collect()`

```python
async def collect(self, request, fetcher) -> KlineCollectResponse:
    raw = fetcher.fetch(params)             # 1. 拉原始数据
    klines = [d.to_entity() for d in raw]   # 2. 转领域实体
    self._enrich_with_indicators(...)        # 3. 算 17 指标
    saved = await self._repo.save_batch(klines)  # 4. 一次性 UPSERT
    await self._upsert_stock_info(...)       # 5. 同步股票基本信息
```

`_enrich_with_indicators` 把 K 线列表拼成 DataFrame → 算指标 → 按日期写回 Kline 对象 → 再 UPSERT（DO UPDATE，全部字段覆盖）。

增量重算接口：

```python
async def recalculate(self, symbol: str, days: int = 60) -> int:
    """增量重算最近 N 天指标，供每日 15:10 定时任务调用"""
```

### 3.5 信号检测器（SignalDetector）

`src/application/signals.py`

输入：含指标字段的 Kline 列表（按日期升序）
输出：`TechnicalSummary` 数据类

检测的形态：

- **均线**：多头 / 空头 / 震荡；近 5 日 MA5 上穿 MA20 → 金叉
- **MACD**：金叉 / 死叉 / 零轴上 / 零轴下
- **RSI**：超买 ( >70) / 超卖 ( <30) / 中性
- **KDJ**：金叉 / 死叉 / 超买 ( J>100) / 超卖 ( J<0)
- **BOLL**：突破上轨 / 跌破下轨 / 上半区 / 下半区 / 中轨附近
- **信号列表**：`signals: list[str]`，如 `["MA 多头排列", "MACD 金叉"]`

### 3.6 AI 归因接口 `GET /stocks/{symbol}/analysis`

`src/route/api/v1/stock_analysis.py` + `src/application/stock_analysis_service.py`

```python
@router.get("/{symbol}/analysis", summary="股票归因分析（AI 入口）")
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=30, le=1825),
    service: StockAnalysisService = Depends(get_analysis_service),
):
    result = await service.build(symbol=symbol, days=days)
    return R.ok(result.model_dump())
```

`StockAnalysisService.build()` 组装流程：

1. 查 `stock_infos` → 股票基本信息
2. 查 `daily_klines` 最近 days 天（含指标列，按日期升序）
3. 调 `SignalDetector.summarize()` → 技术形态摘要
4. 调 `pool_repo.find_pools_by_symbol()` → 所在池列表
5. 组装 `StockAnalysisResponse` 返回

**响应结构**：

```json
{
  "code": 0,
  "data": {
    "stock":   { "symbol": "000001", "name": "平安银行", "industry": "银行", "market": "主板" },
    "summary": {
      "latest_close": 12.34,
      "pct_change_1d": 2.1,
      "ma_alignment": "bullish",
      "macd_status": "golden_cross",
      "rsi6": 65.4,
      "rsi_status": "neutral",
      "kdj_status": "neutral",
      "boll_position": "upper_half",
      "signals": ["MA 多头排列", "MACD 金叉"]
    },
    "klines": [
      { "date": "2024-01-02", "open": 12.0, "high": 12.4, "low": 11.9,
        "close": 12.34, "volume": 1234567, "change_pct": 2.83,
        "ma5": 12.1, "ma10": 12.0, "ma20": 11.8, "ma60": 11.5,
        "macd_dif": 0.1, "macd_dea": 0.05, "macd_bar": 0.1, ... },
      ...
    ],
    "pools": [
      { "pool_id": 1, "pool_name": "我的自选" }
    ]
  }
}
```

### 3.7 修改的文件清单

```
backend/src/
├── main.py                                            # 改：lifespan 加 17 列迁移
├── application/
│   ├── kline_service.py                               # 改：采集即算指标 / 提供 recalculate
│   ├── signals.py                                     # 新：SignalDetector
│   ├── stock_analysis_service.py                      # 新：组装归因响应
│   └── dto/
│       ├── kline.py                                   # 改：KlineItemResponse 加 17 字段
│       └── stock_analysis.py                          # 新：归因 DTO
├── domain/kline/
│   └── entity.py                                      # 改：Kline 加 17 派生属性
├── infrastructure/
│   ├── indicators/
│   │   ├── __init__.py                                # 新
│   │   └── calculator.py                              # 新：IndicatorCalculator
│   ├── database/models/kline.py                       # 改：17 指标列
│   └── repositories/kline_repository.py               # 改：ORM ↔ Entity 含指标
└── route/api/
    ├── router.py                                      # 改：注册 stock_analysis router
    └── v1/stock_analysis.py                           # 新：/stocks/{symbol}/analysis
```

---

## 4. 前端实现

### 4.1 设计要点

1. **单一数据源**：K 线、指标、摘要、所在池全部从 `/analysis` 拿，前端不重复组装
2. **Pinia 缓存**：相同 symbol 不重复请求
3. **轻量图表**：用纯 SVG 自绘蜡烛图（不引入 klinecharts / echarts），零依赖
4. **三层展示**：股票面板抽屉 Tab → 独立分析页 → 后续 AI Agent

### 4.2 三层展示结构

```
┌─ StockPanel 抽屉 (480px) ────────────────────────────────────┐
│  ┌─ Tab 1: 基本信息 ──┐  ┌─ Tab 2: K 线图 ─┐  ┌─ Tab 3 ──┐  │
│  │ 股票描述 + el-     │  │ CandleChart  +  │  │ 归因分析 │  │
│  │ descriptions       │  │ IndicatorSwitch │  │ 跳转按钮 │  │
│  └────────────────────┘  └─────────────────┘  └──────────┘  │
└──────────────────────────────────────────────────────────────┘
                                  ↓ 点击「打开 K 线分析页」
                          /home/stock-analysis/:symbol
                                  ↓
┌─ AnalysisMainView 独立分析页 ─────────────────────────────────┐
│  [搜索 + 标的信息 + 拉取按钮]                                  │
│  ┌──── 左: CandleChart (580px 高) ─────┐ ┌──── 右 (360px) ─┐│
│  │  + IndicatorSwitcher                 │ │ 信号摘要 Tab   ││
│  │  + 鼠标十字光标 + tooltip            │ │ 所在池 Tab     ││
│  │                                      │ │ AI 输入 JSON   ││
│  └──────────────────────────────────────┘ └────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 4.3 关键组件

| 组件 | 路径 | 职责 |
|------|------|------|
| `CandleChart` | `components/kline/CandleChart.vue` | 纯 SVG 自绘蜡烛图 + MA 叠加 + BOLL + MACD/RSI/KDJ 副图 + 十字光标 tooltip |
| `IndicatorSwitcher` | `components/kline/IndicatorSwitcher.vue` | 主图 MA/BOLL 复选 + 副图 MACD/RSI/KDJ 单选 |
| `KLineDrawerTab` | `views/stock-info/components/KLineDrawerTab.vue` | 抽屉内的 K 线 Tab，含时间范围 + 拉取按钮 |
| `AnalysisMainView` | `views/stock-analysis/components/AnalysisMainView.vue` | 独立分析页布局 |
| `SignalSummaryPanel` | `views/stock-analysis/components/SignalSummaryPanel.vue` | 信号标签 + 数值描述表 |
| `PoolMembershipPanel` | `views/stock-analysis/components/PoolMembershipPanel.vue` | 所在池列表 |
| `useKlineStore` | `stores/kline.ts` | analysis + klines 缓存，失效策略 |

### 4.4 路由

`/home/stock-analysis/:symbol` — 独立分析页（hidden，不出现在左侧菜单）

```ts
{
  path: 'stock-analysis/:symbol',
  name: 'StockAnalysis',
  component: () => import('@/views/stock-analysis/components/AnalysisMainView.vue'),
  meta: { title: '股票分析', icon: 'data-line', hidden: true },
  props: true,
}
```

从抽屉「打开 K 线分析页」按钮 → `router.push('/home/stock-analysis/' + symbol)`。

### 4.5 Pinia 缓存策略

```ts
const useKlineStore = defineStore('kline', () => {
  const analysisCache = ref<Record<string, StockAnalysisResponse>>({})
  const klineCache    = ref<Record<string, Kline[]>>({})

  async function fetchAnalysis(symbol, days = 365, force = false)
  async function fetchKlines(symbol, params = {}, force = false)
  async function collect(symbol, days = 365)   // 采集后自动 invalidate(symbol)
  function invalidate(symbol)                    // 单股失效
  function clearCache()                          // 全清
})
```

### 4.6 修改的文件清单

```
frontend/src/
├── common/styles/
│   └── chart-theme.ts                              # 新：A 股配色规范
├── components/
│   └── kline/
│       ├── index.ts                                # 新
│       ├── CandleChart.vue                         # 新：SVG 自绘
│       └── IndicatorSwitcher.vue                   # 新：指标切换器
├── router/
│   └── home.ts                                     # 改：加 /stock-analysis/:symbol
├── stores/
│   └── kline.ts                                    # 新：分析 + K 线缓存
└── views/
    ├── stock-info/
    │   ├── api.ts                                  # 改：Kline + 17 指标 / StockAnalysisResponse / getStockAnalysis
    │   └── components/
    │       ├── StockPanel.vue                      # 改：抽屉三 Tab（基本信息/K线图/归因分析）
    │       └── KLineDrawerTab.vue                  # 新：抽屉 K 线 Tab
    └── stock-analysis/
        ├── index.ts                                # 新
        └── components/
            ├── AnalysisMainView.vue                # 新：独立分析页
            ├── SignalSummaryPanel.vue              # 新：信号摘要
            └── PoolMembershipPanel.vue             # 新：所在池
```

---

## 5. 端到端数据流

**场景 A：用户在 StockPanel 抽屉内看 K 线**

1. 点击行 → `selectStock(row)` → 抽屉打开，默认 Tab=info
2. 切换到「K 线图」Tab → 渲染 `KLineDrawerTab`
3. `KLineDrawerTab` 调 `getKlines(symbol, { limit: 90 })` → `/api/v1/klines/000001?limit=90`
4. 响应里每条 K 线自带 17 指标列
5. `CandleChart` 渲染蜡烛 + MA / BOLL / MACD / RSI / KDJ
6. 鼠标移动 → 十字光标 + tooltip 显示 OHLC + 当日指标

**场景 B：用户进入独立分析页**

1. 抽屉点「打开 K 线分析页」 → `router.push('/home/stock-analysis/000001')`
2. `AnalysisMainView` 调 `getStockAnalysis('000001', { days: 365 })` → `/api/v1/stocks/000001/analysis?days=365`
3. 后端一次性返回 stock + summary + klines(含指标) + pools
4. 左侧 `CandleChart` 渲染，右侧三个 Tab：信号 / 池 / AI 输入

**场景 C：AI Agent 调用**

```python
import httpx
resp = await httpx.AsyncClient().get(
    "http://api/stocks/000001/analysis",
    params={"days": 365},
    headers={"Authorization": "Bearer ..."}
)
payload = resp.json()["data"]
# payload 即可直接喂给 LLM 的 system prompt
```

---

## 6. 关键决策

| 决策 | 选项 | 理由 |
|------|------|------|
| 数据结构 | **方案 A 展宽** | 单表查询快，JOIN 简单；23 年 6.6 GB 可控 |
| 迁移方式 | **`ALTER TABLE IF NOT EXISTS`** | 不引入 alembic；启动时自动执行 |
| 采集策略 | **采集即算指标** | 避免后续重算；指标随采集一并落地 |
| 计算时机 | **同步**（不用后台任务） | 单只 <50ms，池批量 200 只 <10s |
| 接口分层 | **K 线 vs 归因两接口** | 列表页轻数据用 `/klines/{symbol}`；详情/AI 用 `/analysis` |
| 图表库 | **纯 SVG 自绘** | 零依赖；不引入 klinecharts / echarts 包体 |
| 缓存 | **Pinia + 失效策略** | 单 symbol 缓存；采集后自动失效 |

---

## 7. 测试与验证

### 7.1 手动验证清单

```bash
# 1) 启动后端
cd backend && uvicorn src.main:app --reload

# 2) 健康检查
curl http://localhost:8000/health

# 3) 采集 K 线（应触发指标计算）
curl -X POST http://localhost:8000/api/v1/klines/collect \
     -H 'Content-Type: application/json' \
     -d '{"symbol": "000001", "days": 365}'

# 4) 查询 K 线（响应应含 17 指标列）
curl http://localhost:8000/api/v1/klines/000001?limit=10 | jq .data.items[0]

# 5) AI 归因分析
curl http://localhost:8000/api/v1/stocks/000001/analysis?days=365 | jq .data.summary
```

期望：
- `/klines/000001` 每条记录含 `ma5`, `macd_dif`, `rsi6`, `kdj_k`, `boll_up` 等 17 字段
- `/stocks/000001/analysis` 返回 `summary.signals` 至少 1 个信号（采集天数 ≥ 30）
- `summary.latest_close` 与 `/klines/000001` 最新一条 close 一致

### 7.2 前端验证

1. `cd frontend && npm run dev`
2. 浏览器打开 `/home/stock-panel`
3. 点击任意股票行 → 抽屉打开
4. 切换 Tab 到「K 线图」→ 应该看到 K 线（无数据则提示「拉取 K 线」）
5. 点「拉取 K 线」→ 拉完后图表渲染，鼠标悬停十字光标
6. 切到「归因分析」Tab → 点「打开分析页」→ 跳转 `/home/stock-analysis/000001`
7. 独立分析页右侧应显示信号标签、所在池、AI 输入 JSON

---

## 8. 已知限制与后续

| 限制 | 说明 | 后续 |
|------|------|------|
| 指标同步计算 | 200 只池内重算 < 10s；万级可能慢 | 大批量走 Celery |
| joined_at 字段 | 当前 `PoolMembershipVO.joined_at` 固定 null | 仓储查 `StockPoolMemberDB.added_at` 填充 |
| 图表交互 | 十字光标 tooltip + 缩放未做 | 需要时再引入 klinecharts |
| LLM 提示词模板 | AI 输入 JSON 喂给大模型前要包一层 system prompt | step6 做归因 Agent 时引入 |
| 增量重算调度 | recalculate() 已实现，缺 cron | 后续接 APScheduler / Airflow |

---

## 9. 关键 API 一览

### 后端

| 方法 | 路径 | 用途 | 返回 |
|------|------|------|------|
| POST | `/api/v1/klines/collect` | 采集 K 线（自动算指标） | `{ symbol, name, saved_count, ... }` |
| GET  | `/api/v1/klines/{symbol}` | 查询 K 线 + 17 指标列 | `{ total, items: Kline[] }` |
| GET  | `/api/v1/stocks/{symbol}/analysis?days=365` | 🆕 AI 归因分析 | `{ stock, summary, klines, pools }` |

### 前端 (api.ts)

```ts
// K 线
getKlines(symbol, { limit, start_date, end_date, order_desc })
collectKlines({ symbol, days })

// 归因分析
getStockAnalysis(symbol, { days }): Promise<StockAnalysisResponse>

// Pinia
useKlineStore().fetchAnalysis(symbol, days)
useKlineStore().collect(symbol, days)   // 自动 invalidate
useKlineStore().invalidate(symbol)
```

---

## 10. 一句话总结

> **数据展宽**：17 个指标列直接进 `daily_klines`，采集即算，零额外存储开销
>
> **统一入口**：`/stocks/{symbol}/analysis` 一次给齐 K 线 + 指标 + 摘要 + 池，前端和 AI Agent 共用
>
> **三层展示**：抽屉三 Tab（轻量）+ 独立分析页（全屏）+ JSON 输入（调试 / 喂模型），逐级深入
