# 04 stock_info 详情中的概念 — 修改设计文档

> 配套开发：仅修改，不破坏现有架构。
> 入口：@Attribution_Analysis/frontend/src/views/stock-info

---

## 0. 概要

**目标**：股票详情抽屉「概念」Tab 点击某个概念 Tag（ConceptTag）后，在抽屉内展开/加载该概念指数的 **日 K 线** + **当日分时**，**获取后不实时刷新**；同时保持 Tag 上"点击时的涨跌幅"。

**核心思路**：

- 后端已有两个接口 → **直接复用，不新增**：
  - `GET /api/v1/concepts/{index_code}/kline` （日 K + 实时）
  - `GET /api/v1/concepts/{index_code}/minute` （分时 241 点）
- 前端：在 ConceptTab.vue 增加"被选中概念"的展示区，复用已有 `ConceptKlineCard.vue`（日K）+ 写一个轻量 `ConceptMinuteChart.vue`（分时）展示分时图
- "不实时刷新"：日 K 单次拉取；分时仅**首次**拉取（不接 `useRealtimePoll`）
- "包含点击时的涨跌幅"：沿用已有 `ConceptTag.snapshot` 字段（已是 `getConceptQuotes` 15s 轮询），Tag 旁的红绿数字本来就有 → 不动

---

## 1. 现状盘点（不重复造轮子）

| 已有 | 路径 | 用途 |
|------|------|------|
| 后端 | `route/api/v1/concept.py` `/{index_code}/kline` | 日 K + 实时快照（service 层走 concept_minute 15s 缓存） |
| 后端 | `route/api/v1/concept.py` `/{index_code}/minute` | 当日分时 241 点（同上实时框架） |
| 前端 | `views/concept-board/components/ConceptKlineCard.vue` | 概念日 K + 实时头部 + MiniKlineChart 渲染 |
| 前端 | `views/stock-info/components/MiniKlineChart.vue` | 通用 K 线 canvas 渲染（基于 CandleChart） |
| 前端 | `views/stock-info/components/ConceptTab.vue` | 已加载所属概念 + snapshot 染色 + 15s 轮询行情 |
| 前端 | `views/stock-info/components/ConceptTag.vue` | Tag 组件 + `pct_change` 红绿后缀 + tooltip |
| 前端 API | `views/stock-info/api.ts` | `getConceptKline(indexCode)` ✅已存在；`getConceptMinute(indexCode)` ❌**需补** |

> 🎯 **关键发现**：日 K 接口 `getConceptKline` **前端已经定义但未在 stock-info 页用到**（只在 concept-board 用）；分时接口 `getConceptMinute` **完全没定义**。两个接口后端都齐了，纯前端增量。

---

## 2. 改哪些文件（最小集）

| 文件 | 改动 |
|------|------|
| `frontend/src/views/stock-info/api.ts` | 新增 `getConceptMinute(index_code)`；`getConceptKline` 已有无需改 |
| `frontend/src/views/stock-info/components/ConceptTab.vue` | 选中态 state + 点击 Tag 触发加载 + 展示区（K线卡 + 分时卡） |
| `frontend/src/views/stock-info/components/ConceptKlineCard.vue` | **新增**：复用 `concept-board/ConceptKlineCard.vue` 的渲染逻辑（从 `concept-board/` 提到 `stock-info/components/`），保持薄壳只渲染 |
| `frontend/src/views/stock-info/components/ConceptMinuteChart.vue` | **新增**：分时折线图（用 `<canvas>` 或简易 SVG，<200 行） |
| 0 文件后端 | **0 改动**（DTO/路由/service 全齐，复用即可） |

> 不动 `StockDetailDrawer.vue`（抽屉布局不调整，仅在 Tab 内部展开，不弹新抽屉）

---

## 3. 详细设计

### 3.1 后端 — 0 改动

| 接口 | 用途 | 状态 |
|------|------|------|
| `GET /concepts/{index_code}/kline?days=250` | 日 K + 实时快照 | ✅ 已实现 |
| `GET /concepts/{index_code}/minute` | 当日 241 点分时 | ✅ 已实现 |

**为什么不动**：
- `concept_board_service.py::get_kline` 已经在用 `concept_minute` 实时 + 日 K 走 `concept_index_ths` 表
- `concept.py::get_concept_minute` 已经在用 `realtime_query_framework().query("concept_minute", ...)`
- 两个接口都有 15s Redis 缓存 + 兜底 fallback（取不到分时返回最近一日收盘 + 空 points 数组）
- 缓存已经天然提供"获取后不实时刷新"的语义：第二次拉分时会拿 15s 缓存的同一份，但这是缓存，不是主动轮询 → 满足"获取后不实时刷新"

### 3.2 前端 — api.ts

#### 3.2.1 新增 `getConceptMinute`

```ts
/** GET /api/v1/concepts/{index_code}/minute  概念当日分时 241 点
 *  - 实时接口 concept_minute（15s 缓存，adata 同花顺）
 *  - 失败/取不到时返回 points=[], stale=true
 *
 * 配套设计文档：docs/dev/step3/04概念看板/stock_info详情中的概念.md §3.2
 */
export interface ConceptMinutePoint {
  trade_time: string
  price: number
  avg_price: number | null
  volume: number | null
  amount: number | null
  change_pct: number | null
}

export interface ConceptMinuteResponse {
  index_code: string
  trade_date: string | null
  pre_close: number | null
  price: number | null        // 最新价
  change: number | null
  change_pct: number | null  // 最新涨跌幅（= Tag 上当时显示的数字来源）
  trade_time: string | null
  points: ConceptMinutePoint[]
  stale: boolean
  cached: boolean
  fetched_at: string | null
}

export const getConceptMinute = (index_code: string): Promise<ConceptMinuteResponse> =>
  http.get<ConceptMinuteResponse>(`/concepts/${index_code}/minute`).then(unwrap)
```

> `getConceptKline` 已在 stock-info/api.ts 中**不存在**，但 concept-board/api.ts 有，需在 stock-info/api.ts 复制定义（两端共用同一后端，可后续考虑拆 lib）。

### 3.3 前端 — 新增 `ConceptMinuteChart.vue`

#### 3.3.1 组件契约

```vue
<!--
 * 概念当日分时折线图
 *
 * 数据来源：getConceptMinute(index_code)
 *
 * 展示策略：
 * - 241 点折线（9:30 ~ 15:00，每分钟 1 点）
 * - pre_close 基线（虚线）
 * - 点 hover → tooltip 显示 trade_time / price / change_pct
 * - 涨跌染色：>= 红涨 = 绿跌 = 灰平（同花顺配色）
 *
 * 不实时刷新（获取后即定格；分时是当日已发生的数据，1 分钟也用不上）
 *
 * 配套设计文档：docs/dev/step3/04概念看板/stock_info详情中的概念.md §3.3
-->
```

#### 3.3.2 props

```ts
const props = defineProps<{
  index_code: string
  concept_name: string
  data: ConceptMinuteResponse | null
  loading: boolean
  height?: number        // 默认 160
  /** 点击时锁定的涨跌幅（从 Tag.snapshot.pct_change 传入），header 显示 */
  frozen_pct_change?: number | null
}>()
```

#### 3.3.3 实现要点

1. **不引入图表库**：用 SVG 自己手画 241 折线（点数恒定 ≤ 241，SVG 性能足够）
2. **关键算法**：
   - X 轴：5 个时间刻度（09:30 / 10:30 / 11:30 / 13:00 / 15:00）
   - Y 轴：以 `pre_close` 为中心上下等比；如缺 `pre_close`，以所有点 price 的 min/max + 5% padding
3. **涨跌色**：
   ```ts
   const color = computed(() => {
     const pct = props.data?.change_pct ?? props.frozen_pct_change
     if (pct == null || pct === 0) return '#9ca3af'
     return pct > 0 ? '#dc2626' : '#16a34a'
   })
   ```
4. **空态**：points.length === 0 时显示"暂无分时数据（可能非交易时段）"

### 3.4 前端 — ConceptTab.vue

#### 3.4.1 state 扩展

```ts
// 现有
const data = ref<ConceptTabContentVO | null>(null)
const merged = ref(false)
// ...

// 🆕 选中概念 + 日K + 分时（一次性加载，不实时刷新）
const pickedConcept = ref<{
  index_code: string
  concept_id: number
  name: string
  concept_type: ConceptType
  pct_change: number | null  // 冻结 Tag 上当时的涨跌幅
} | null>(null)
const klineData = ref<ConceptKlineResponse | null>(null)
const klineLoading = ref(false)
const minuteData = ref<ConceptMinuteResponse | null>(null)
const minuteLoading = ref(false)
```

#### 3.4.2 现有 onTagClick 改造

```ts
// 旧：
async function onTagClick(c) {
  if (c.reason) {
    await ElMessageBox.alert(c.reason, `${c.name} · 入选理由...`, ...)
  } else {
    emit('conceptClick', c)
    ElMessage.info(...)
  }
}

// 新：
async function onTagClick(c) {
  const indexCode = c.index_code || c.concept_code
  if (!indexCode) {
    ElMessage.warning(`${c.name} 缺少 index_code，无法加载 K 线`)
    return
  }
  // 冻结当时涨跌幅（来自 Tag.snapshot 或直接 c.snapshot）
  const pct = (c as any).snapshot?.pct_change ?? null
  pickedConcept.value = {
    index_code: indexCode,
    concept_id: c.concept_id,
    name: c.name,
    concept_type: c.concept_type,
    pct_change: pct,
  }
  await Promise.all([loadKline(indexCode), loadMinute(indexCode)])
}
```

#### 3.4.3 新增 loadKline / loadMinute

```ts
async function loadKline(index_code: string) {
  klineLoading.value = true
  try {
    klineData.value = await getConceptKline({ index_code, days: 250 })
  } catch (e) {
    ElMessage.error('加载概念日 K 失败: ' + (e as Error).message)
    klineData.value = null
  } finally {
    klineLoading.value = false
  }
}

async function loadMinute(index_code: string) {
  minuteLoading.value = true
  try {
    minuteData.value = await getConceptMinute(index_code)
  } catch (e) {
    ElMessage.error('加载概念分时失败: ' + (e as Error).message)
    minuteData.value = null
  } finally {
    minuteLoading.value = false
  }
}
```

#### 3.4.4 模板新增展示区

```vue
<!-- 在 sections 之后、concept-footer 之前 -->
<div v-if="pickedConcept" class="concept-picked">
  <div class="picked-header">
    <span class="text-sm font-semibold">
      📊 {{ pickedConcept.name }} · 指数走势
    </span>
    <span v-if="pickedConcept.pct_change != null"
          :class="pickedConcept.pct_change > 0 ? 'text-red-500' : 'text-green-600'"
          class="mono font-bold ml-2">
      {{ pickedConcept.pct_change > 0 ? '+' : '' }}{{ pickedConcept.pct_change.toFixed(2) }}%
    </span>
    <span class="text-xs text-gray-400 ml-2">(点击时)</span>
    <el-button size="small" link class="ml-auto" @click="closePicked">收起</el-button>
  </div>

  <ConceptKlineCard
    class="picked-kline"
    :concept-name="pickedConcept.name"
    :index-code="pickedConcept.index_code"
    :data="klineData"
    :loading="klineLoading"
    :height="220"
  />

  <ConceptMinuteChart
    class="picked-minute"
    :index-code="pickedConcept.index_code"
    :concept-name="pickedConcept.name"
    :data="minuteData"
    :loading="minuteLoading"
    :height="160"
    :frozen-pct-change="pickedConcept.pct_change"
  />
</div>
```

#### 3.4.5 重要：为何不接 useRealtimePoll

- 用户明确要求"获取后不实时刷新"
- 日 K 是历史数据，实时刷没意义（永远是昨日及以前）
- 分时是当日数据，要"实时"得用 `getMinuteKlines`（股票分时接口），但同花顺概念没有类似分钟流接口；且用户明示不要实时
- 涨跌幅"点击时"已通过 `pickedConcept.pct_change` 冻结在 header 上 → 已满足"包含点击时的涨跌幅"

#### 3.4.6 closePicked

```ts
function closePicked() {
  pickedConcept.value = null
  klineData.value = null
  minuteData.value = null
}
```

---

## 4. ConceptKlineCard.vue（stock-info 版）— 是否新建？

**结论：新建**（从 `concept-board/components/ConceptKlineCard.vue` **复制**到 `stock-info/components/`，代码几乎一致）。

**理由**：
1. `concept-board/ConceptKlineCard.vue` 的 import 路径已耦合 `MiniKlineChart`（在 stock-info 目录）+ `../../api`（concept-board 的 api）→ 跨目录使用要修 import
2. 两个组件未来可能演进不同（concept-board 多了成分股、stock-info 多了"点击时冻结涨跌幅"语义）
3. 复制+微调成本 < 抽象成本

**复制的差异点**（相对原版）：
- 把 `import MiniKlineChart from '@/views/stock-info/components/MiniKlineChart.vue'` 改成相对路径
- 把 `import type { ... } from '../api'` 改成 `from '@/views/stock-info/api'`
- headerTitle 改为 `${conceptName} · 日 K · 走势`
- 其他样式 100% 相同

---

## 5. 不动 / 待你确认的点

| 项 | 决定 |
|----|------|
| 后端 | ❌ 不动 |
| 是否复用 `concept-board/ConceptKlineCard.vue` | ❌ **新建**（理由见 §4） |
| 是否新建图表库 | ❌ 用 SVG 手画分时 |
| 涨跌配色 | 红涨 / 绿跌 / 灰平（同花顺配色，沿用现有约定） |
| ConceptTab 当前 15s 轮询行情（`refreshQuotes`） | ✅ **保留**（用户说"获取后不实时刷新"指的是 K 线，不是 Tag 上的涨跌幅） |
| 选股切换（watch(props.symbol)） | ✅ 重置 `pickedConcept = null`（切换股票后折叠） |
| 分时 15s 缓存命中 | ✅ 第二次点同概念会拿到 15s 内缓存（语义上仍是"不主动实时"，可接受） |

---

## 6. 时序图（点 Tag 触发）

```
[用户]  click ConceptTag
   │
   ▼
[ConceptTab.onTagClick(c)]
   │
   ├─► 冻结 c.snapshot.pct_change 到 pickedConcept.pct_change
   ├─► Promise.all([loadKline, loadMinute])
   │      │
   │      ├─► GET /concepts/{index_code}/kline
   │      │     └─► 后端: concept_index_ths (DB) + concept_minute (实时15s缓存)
   │      │
   │      └─► GET /concepts/{index_code}/minute
   │            └─► 后端: concept_minute 实时接口（adata get_market_concept_min_ths）
   │
   ▼
[模板]  v-if="pickedConcept" 显示 ConceptKlineCard + ConceptMinuteChart
```

---

## 7. 文件清单（落地后请逐个 review）

1. ✅ `frontend/src/views/stock-info/api.ts` — 加 `getConceptMinute` + `ConceptMinutePoint/Response`
2. ✅ `frontend/src/views/stock-info/components/ConceptMinuteChart.vue` — 新建 SVG 分时图
3. ✅ `frontend/src/views/stock-info/components/ConceptKlineCard.vue` — 新建（从 concept-board 复制）
4. ✅ `frontend/src/views/stock-info/components/ConceptTab.vue` — 加 state + onTagClick + 展示区
5. ❌ 后端任何文件 — **0 改动**

---

## 8. 验收清单

- [ ] 抽屉 → 概念 Tab → 加载概念列表（已有，**不要破坏**）
- [ ] 点 Tag → 抽屉**就地**显示日 K 图 + 分时图（不弹新抽屉、不弹入选理由弹窗）
- [ ] header 显示"📊 概念名 · 指数走势" + 冻结的涨跌幅红绿数字 + "(点击时)" 字样
- [ ] 日 K 拉到 concept_index_ths 历史 → MiniKlineChart 正常渲染
- [ ] 分时 241 点 SVG 折线渲染（hover 显示 tooltip）
- [ ] 点"收起"按钮 → 折叠，不重新触发加载
- [ ] 切换不同股票 → pickedConcept 自动重置
- [ ] 切换同股票不同 Tag → 上一个 Tag 的 K/分时清空、新一个 Tag 加载
- [ ] 同概念 15s 内再点 → 命中 Redis 缓存（< 100ms 返回，不重新打 adata）
- [ ] **不接 useRealtimePoll**：分时和日 K 在显示后**不**自动刷新
- [ ] ConceptTag 上 15s 轮询的涨跌幅（`refreshQuotes`）**保留**