# 04 — 前端 StockInfoList + StockDetailDrawer 集成

> 配套文档：`./README.md` §四（文件清单）§五（变更统计）
> 前置阅读：`./02-class-design.md`（涉及的类）`./03-data-flow.md`（数据流）
>
> 本期前端改动核心：**StockInfoList 新增"主概念"列 + ConceptTab 新增"🔄 实时刷新"按钮 + ConceptTag 适配双类型**。

---

## 一、改动文件清单

| 文件 | 操作 | 关键改动 |
|:---|:---:|:---|
| `frontend/src/views/stock-info/api.ts` | ✏️ 改 | `ConceptBrief` 增 `concept_type?`；新增 `ConceptMainVO` / `ConceptMergedVO`；新增 `getConceptTabForSymbolMerged` |
| `frontend/src/views/stock-info/components/ConceptTag.vue` | ✏️ 改 | 接受双类型入参；tooltip 内容优先级 reason > description |
| `frontend/src/views/stock-info/components/ConceptTab.vue` | ✏️ 改 | 新增 `merged` 状态 + 🔄 按钮；展示合并视图；入选理由弹窗 |
| `frontend/src/views/stock-info/StockInfoList.vue` | ✏️ 改 | 新增"主概念"列（最多 3 Tag + `+N`）；接 `ConceptTag` |
| `frontend/src/views/stock-info/components/StockDetailDrawer.vue` | ✏️ 改 | 透传 `conceptClick` 到 ConceptTab |

---

## 二、`StockInfoList.vue`：新增"主概念"列

### 2.1 设计目标

在表格中**一眼看到**每只股票所属的主要概念（最多 3 个），点击 Tag 不触发整行选中。

### 2.2 模板改动（在「已加入池」列后插入）

```diff
   <el-table-column label="已加入池" width="160" fixed="left">
     <template #default="{ row }">
       ... (既有)
     </template>
   </el-table-column>

+  <!-- 🆕 主概念列（最多 3 个 + +N 溢出） -->
+  <el-table-column label="主概念" width="200" fixed="left">
+    <template #default="{ row }">
+      <div class="flex flex-wrap gap-1">
+        <ConceptTag
+          v-for="c in (row.concepts || []).slice(0, 3)"
+          :key="c.concept_id"
+          :concept="c"
+          @click.stop="onConceptTagClick(c)"
+        />
+        <el-tooltip
+          v-if="row.concepts_overflow > 0"
+          :content="getOverflowTooltip(row)"
+          placement="top"
+        >
+          <span class="text-xs text-gray-500">+{{ row.concepts_overflow }}</span>
+        </el-tooltip>
+        <span
+          v-if="!row.concepts || row.concepts.length === 0"
+          class="text-xs text-gray-400"
+        >
+          暂无
+        </span>
+      </div>
+    </template>
+  </el-table-column>
```

### 2.3 脚本改动

```diff
 <script setup lang="ts">
 import {
   Search, Refresh, Folder, ArrowDown, ArrowUp, View,
 } from '@element-plus/icons-vue'
 import PageWrapper from '@/components/PageWrapper.vue'
 import AddToPoolDialog from './components/AddToPoolDialog.vue'
 import StockDetailDrawer from './components/StockDetailDrawer.vue'
+import ConceptTag from './components/ConceptTag.vue'
 import { useStockDetailDrawer } from './composables/useStockDetailDrawer'
 import {
   queryStocks,
   getStockMeta,
   syncStocks,
 } from '@/views/stock-info/api'
 import type {
   StockInfo,
   StockMeta,
   StockQueryParams,
   PoolMembership,
+  ConceptMainVO,
 } from '@/views/stock-info/api'
```

```typescript
// 🆕 主概念 Tag 点击：未来跳概念详情页 / 打开新抽屉
function onConceptTagClick(c: ConceptMainVO) {
  ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
  // TODO: router.push(`/home/concept/${c.concept_id}`)
}

// 🆕 +N 溢出 tooltip
function getOverflowTooltip(row: StockInfo): string {
  const overflowNames = (row.concepts || [])
    .slice(3)
    .map((c) => `${c.name}（${c.concept_type}）`)
    .join('、')
  return overflowNames || `还有 ${row.concepts_overflow} 个概念`
}
```

### 2.4 完整改动效果（示意图）

```
┌───────┬──────────────┬─────────┬──────────────────────┬──────────────────┬──────┐
│  ☑   │   002229     │ 鸿博股份 │      我的自选        │ 🏭 行业: 印刷 ⭐ │ +5   │ 🔍 详情 │
│       │              │          │                      │ 🪄 主题: AI算力  │      │          │
│       │              │          │                      │ ⭐ 事件: 英伟达  │      │          │
├───────┼──────────────┼─────────┼──────────────────────┼──────────────────┼──────┤
│  ☑   │   000006     │ 深振业A  │      —              │ 🏭 行业: 房地产  │      │ 🔍 详情 │
│       │              │          │                      │ 🌏 地域: 深圳   │      │          │
└───────┴──────────────┴─────────┴──────────────────────┴──────────────────┴──────┘
                          主概念（最多 3 个 + +N 溢出）
```

### 2.5 排序示例

后端 `_build_main_concepts()` 已按 `concept_type` 优先级排序，前端无需再排序：

| 优先级 | type | 颜色（沿用 ConceptTag） | 含义 |
|:---:|:---|:---|:---|
| 1 | `industry` | `primary` 蓝 | 行业概念 |
| 2 | `theme` | `success` 绿 | 主题概念 |
| 3 | `event` | `danger` 红 | 事件概念 |
| 4 | `style` | `warning` 黄 | 风格概念 |
| 5 | `region` | `info` 灰 | 地域概念 |
| 6 | `other` | `info` 灰 | 其他 |

---

## 三、`ConceptTab.vue`：🔄 实时刷新按钮 + 合并视图

### 3.1 设计目标

用户在不离开抽屉的情况下，**点一下按钮**就能看到 adata 提供的"为什么这只股票属于这个概念"的入选理由。

### 3.2 模板改动（在「概念」分组列表上方插入实时刷新工具栏）

```diff
 <template>
   <div v-loading="loading" class="concept-tab">
+    <!-- 🆕 实时刷新工具栏 -->
+    <div class="flex items-center justify-between mb-3 pb-2 border-b border-gray-100">
+      <div class="flex items-center gap-2">
+        <el-icon class="text-gray-400"><DataLine /></el-icon>
+        <span class="text-sm text-gray-700">
+          {{ merged ? '实时数据（已合并 adata）' : '数据库数据' }}
+        </span>
+        <el-tag v-if="merged" size="small" type="success" effect="plain">
+          ✓ 已合并
+        </el-tag>
+        <span v-if="merged && data?.last_merged_at" class="text-xs text-gray-400">
+          {{ formatRelativeTime(data.last_merged_at) }}
+        </span>
+      </div>
+      <el-button
+        size="small"
+        type="primary"
+        link
+        :loading="loading && merged"
+        @click="onLiveRefresh"
+      >
+        <el-icon class="mr-1"><Refresh /></el-icon>
+        🔄 实时刷新
+      </el-button>
+    </div>
+
     <!-- 骨架屏：抽屉刚打开、用户尚未看热词时 -->
     <div v-if="!data && loading" class="concept-skeleton">
       <el-skeleton :rows="4" animated />
     </div>

     <!-- 正常渲染 -->
     <template v-else-if="data">
       ... (既有)
     </template>
   </div>
 </template>
```

### 3.3 脚本改动

```typescript
import { ref, watch, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, DataLine } from '@element-plus/icons-vue'
import {
  getConceptTabForSymbol,
  getConceptTabForSymbolMerged,  // 🆕
  type ConceptTabContentVO,
  type ConceptGroupedVO,
} from '@/views/stock-info/api'
import ConceptTag from './ConceptTag.vue'

const props = defineProps<{
  symbol: string
  stock_name?: string
}>()

const emit = defineEmits<{
  conceptClick: [c: ConceptGroupedVO]
}>()

const loading = ref(false)
const data = ref<ConceptTabContentVO | null>(null)
const merged = ref(false)  // 🆕 跟踪当前数据是否合并实时

async function load() {
  if (!props.symbol) return
  loading.value = true
  try {
    data.value = await getConceptTabForSymbol(props.symbol, {
      stock_name: props.stock_name,
    })
    merged.value = false
  } catch (e) {
    ElMessage.error('加载概念失败: ' + (e as Error).message)
    data.value = null
  } finally {
    loading.value = false
  }
}

// 🆕 实时刷新：合并 adata 实时数据
async function onLiveRefresh() {
  if (loading.value) return  // 防抖
  loading.value = true
  try {
    data.value = await getConceptTabForSymbolMerged(props.symbol, {
      stock_name: props.stock_name,
    })
    merged.value = true
    ElMessage.success(
      `已合并 ${data.value?.total_count ?? 0} 个概念（含 adata 实时入选理由）`,
    )
  } catch (e) {
    ElMessage.error('实时刷新失败: ' + (e as Error).message)
    // 不重置 merged，保持上次状态
  } finally {
    loading.value = false
  }
}

// 🆕 Tag 点击：实时数据时弹入选理由
async function onTagClick(c: any) {
  if (c.is_realtime && c.reason) {
    await ElMessageBox.alert(
      c.reason,
      `${c.name} · 入选理由（adata 实时）`,
      {
        confirmButtonText: '关闭',
        type: 'info',
      },
    )
  } else {
    emit('conceptClick', c)
    ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
  }
}

// 🆕 相对时间格式化
function formatRelativeTime(iso: string): string {
  const t = new Date(iso).getTime()
  const diff = Date.now() - t
  if (diff < 60_000) return '刚刚'
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} 分钟前`
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} 小时前`
  return new Date(iso).toLocaleString('zh-CN')
}

watch(() => props.symbol, () => {
  merged.value = false  // 切换股票时重置
  load()
}, { immediate: true })
```

### 3.4 关键差异：`onTagClick` 处理合并视图

```typescript
// 06gainian（DB only）
function onTagClick(c: ConceptGroupedVO) {
  emit('conceptClick', c)
  ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
}

// 08concept（合并视图）
async function onTagClick(c: any) {
  // 实时数据有 reason 时弹入选理由
  if (c.is_realtime && c.reason) {
    await ElMessageBox.alert(c.reason, `${c.name} · 入选理由`, {
      confirmButtonText: '关闭',
    })
  } else {
    emit('conceptClick', c)
    ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
  }
}
```

---

## 四、`ConceptTag.vue`：双类型入参

### 4.1 设计目标

让 `ConceptTag` 同时支持：
- **列表行**：`ConceptMainVO`（无 description）
- **抽屉 Tab**：`ConceptGroupedVO`（有 description）或合并后的 dict（有 `is_realtime` + `reason`）

### 4.2 类型扩展（TypeScript union）

```typescript
// 列表行：ConceptMainVO（无 description）
// 抽屉 Tab：ConceptGroupedVO（有 description）
// 合并视图：dict（有 is_realtime / reason）
type ConceptLike =
  | ConceptMainVO
  | ConceptGroupedVO
  | (ConceptMainVO & { is_realtime?: boolean; reason?: string | null })
```

### 4.3 关键代码片段

```typescript
const tooltipContent = computed(() => {
  const c = props.concept as any
  // 优先级：reason（实时） > description（DB） > 默认文案
  if (c.reason) return c.reason
  if (c.description) return c.description
  return '点击查看概念详情'
})

const resolvedType = computed(() => {
  const c = props.concept as any
  return c.concept_type || 'other'  // 列表行的 ConceptMainVO 才有 type
})
```

### 4.4 视觉差异（实时标识）

可以在 `is_realtime=true` 时给 Tag 加一个微小的"实时"徽标：

```vue
<el-tag :type="tagType" :effect="hovered ? 'dark' : 'plain'" round>
  <el-icon v-if="iconForType" class="mr-1"><component :is="iconForType" /></el-icon>
  {{ concept.name }}
  <el-icon v-if="(concept as any).is_realtime" class="ml-1 text-xs">
    <Lightning />
  </el-icon>
</el-tag>
```

---

## 五、`api.ts`：类型扩展 + 新 API 封装

### 5.1 类型扩展

```typescript
// === 既有（扩展 concept_type 字段）===
export interface ConceptBrief {
  concept_id: number
  name: string
  source: ConceptSource
  concept_type?: ConceptType  // 🆕 可选（兼容旧响应）
}

// === 🆕 新增 ===
export interface ConceptMainVO {
  concept_id: number
  name: string
  source: ConceptSource
  concept_type: ConceptType     // 🆕
  display_order: number         // 🆕
}

export interface ConceptMergedVO {
  concept_id: number | null
  concept_code: string | null
  name: string
  source: ConceptSource
  concept_type: ConceptType
  is_realtime: boolean
  reason: string | null
  description: string | null
}

// === StockInfo 字段升级 ===
export interface StockInfo {
  // ... 既有字段 ...
  pools: PoolMembership[]
  concepts: ConceptMainVO[]           // 🆕 由 ConceptBriefVO[] 升级
  concepts_overflow: number          // 🆕
}

// === ConceptTabContentVO 扩展 ===
export interface ConceptTabContentVO {
  symbol: string
  stock_name: string
  sections: ConceptTabSectionVO[]
  total_count: number
  is_merged?: boolean                // 🆕
  last_merged_at?: string | null     // 🆕
}
```

### 5.2 新增 API 封装

```typescript
/** GET /api/v1/concepts/tab-by-symbol/{symbol}?merge_live=true  合并实时数据 */
export const getConceptTabForSymbolMerged = (
  symbol: string,
  params: { stock_name?: string } = {},
): Promise<ConceptTabContentVO> =>
  http.get<ConceptTabContentVO>(
    `/concepts/tab-by-symbol/${symbol}`,
    { params: { ...params, merge_live: true } },
  ).then(unwrap)
```

---

## 六、`StockDetailDrawer.vue`：透传 conceptClick

### 6.1 设计目标

保持 `StockDetailDrawer.vue` 极简，仅做事件透传（不重复业务逻辑）。

### 6.2 模板（不变）

```vue
<el-tab-pane label="概念" name="concepts">
  <ConceptTab
    v-if="stock"
    :symbol="stock.symbol"
    :stock-name="stock.name"
    @concept-click="onConceptClick"
  />
</el-tab-pane>
```

### 6.3 脚本（占位实现）

```typescript
function onConceptClick(c: ConceptGroupedVO) {
  // 占位：未来跳到概念详情页 / 打开新抽屉
  console.log('[StockDetailDrawer] concept click', c)
  // TODO: router.push(`/home/concept/${c.concept_id}`)
}
```

> **注意**：本期不实现概念详情页路由（属于 v1.1 范围）。`onConceptClick` 仅占位日志。

---

## 七、交互细节 & UX 兜底

### 7.1 列表行主概念列

| 场景 | 表现 |
|:---|:---|
| `row.concepts` 为空 | 显示 "暂无"（灰色 12px） |
| `row.concepts.length <= 3` | 仅显示 Tag，无 `+N` |
| `row.concepts.length > 3` | 显示前 3 + `+N`（hover 显示溢出名称列表）|
| `row.concepts` 字段缺失（向后兼容老响应） | `row.concepts || []` 兜底 |
| `with_concepts=false` | 后端不下发 `concepts` 字段 → 前端不渲染列 |

### 7.2 抽屉「概念」Tab

| 场景 | 表现 |
|:---|:---|
| 首次打开 | 加载 DB 数据（默认）；显示「数据库数据」标识 |
| 点击 🔄 实时刷新 | 切换为「实时数据（已合并 adata）」标识 + 绿色 ✓ |
| 切换股票 | `merged.value=false` 重置，重新加载 DB |
| adata 失败 | 维持上次状态 + `ElMessage.error` |
| 双路都为空 | `el-empty description="该股票暂无概念归属"` |

### 7.3 ConceptTag Tooltip 优先级

```
实时 reason（adata 独有）→  DB description（落库时写入）→  默认文案
```

> 合并视图下，`is_realtime=true` 的概念优先显示 reason。

---

## 八、可访问性（A11y）

| 元素 | 属性 |
|:---|:---|
| 主概念 Tag | `aria-label="概念：{name}，{concept_type}，{source} 数据源"` |
| `+N` 溢出 | `aria-label="还有 {N} 个概念"` |
| 🔄 实时刷新按钮 | `aria-label="刷新为实时数据（含入选理由）"` |
| 合并标识 | `aria-label="已合并 adata 实时数据"` |

---

## 九、测试要点

| 测试 | 类型 | 覆盖 |
|:---|:---|:---|
| `ConceptTag.spec.ts` | 单元 | 双类型入参：ConceptMainVO / ConceptGroupedVO / merged dict |
| `ConceptTab.spec.ts` | 单元 | 加载 / 实时刷新 / 切换股票重置 / 失败回退 |
| `StockInfoList.spec.ts` | 集成 | 主概念列渲染：`0 / 1 / 3 / 5+` 概念；Tag 点击不冒泡 |
| `StockDetailDrawer.spec.ts` | 集成 | 透传 conceptClick；合并视图状态切换 |

---

## 十、与 `06gainian/04-frontend-detail-design.md` 的关系

| 改动点 | `06gainian/04` 原设计 | `08concept/04` 本期 |
|:---|:---|:---|
| 列表主概念 | ❌ 移除（原 README §1.1 修订）| ✅ **回潮**（业务确认有价值） |
| 概念详情抽屉 | 已有（按 type 分组） | 不变 |
| 🔄 实时刷新 | ❌ 无 | ✅ 新增按钮 |
| ConceptTag 适配 | 单类型（ConceptGroupedVO）| ✅ 双类型 |
| 概念详情页 | ❌ 占位 | ❌ 仍占位（v1.1 范围） |

> **设计演变**：早期移除列表主概念列是出于"列拥挤"考虑；本期通过"仅显示 3 个 + 排序"折中方案回归，并复用 `with_concepts=true` 下发的数据（零额外网络开销）。

---

## 十一、相关文档

| 文档 | 路径 |
|:---|:---|
| 数据流 + 缓存策略 | `./03-data-flow.md` |
| 类设计 | `./02-class-design.md` |
| 命名规范 + ER 图 | `./01-naming-and-tables.md` |
| 总览 | `./README.md` |
| 概念一期前端设计 | `../06gainian/04-frontend-detail-design.md` |
