# 04 — 前端详情抽屉与按钮强化设计

> 配套 UML：`docs/PlantUML/Concept/01-class.puml` 中「前端」package
> 所属：`docs/dev/06gainian/README.md` 第一节「目标」(2026-09-24 修订)
>
> 前置阅读：
> - [01-domain-design.md](./01-domain-design.md) — `ConceptBriefVO` / `ConceptGroupedVO` 定义
> - [03-application-and-route-design.md](./03-application-and-route-design.md) — `ConceptTabContentVO` / 接口约定

---

## 一、为什么改成抽屉 + 详情按钮

### 1.1 旧方案的痛点

| 痛点 | 描述 |
|------|------|
| **列拥挤** | 表格本就 13+ 列（最新价、市值、PE、行业、市场、交易所…），再塞概念列导致列宽被压缩。 |
| **信息丢失** | `+N` 溢出虽然能容下更多 tag，但用户看不到完整列表，也无法交互。 |
| **行展开体验差** | `el-table-column type="expand"` 用 `+` / `-` 箭头触发，视觉权重弱；与多选 / 排序 / 行高亮交互冲突。 |
| **KLine 看板抢眼** | 展开行的 KLine 图表占满两列，掩盖了"我要看这只股票的概念"这个真实意图。 |
| **刷新成本高** | 每行都带 KLine 缓存，页面滚动 + 切换筛选条件时频繁触发请求。 |

### 1.2 新方案的价值

| 优势 | 描述 |
|------|------|
| **表格清爽** | 表格回归"快速浏览"本职；概念相关字段全部下沉到抽屉。 |
| **详情深入** | 抽屉内可承载分组、点击、tooltip、跳转等多种交互。 |
| **按钮显性** | 行末「详情」按钮，颜色、尺寸、形状、动画全面强化。 |
| **按需加载** | 抽屉未打开时不请求概念 Tab 数据，列表请求负载降低。 |
| **可演进** | 抽屉可承载未来的更多 Tab（资金流向、机构调研、归因分析…）。 |

### 1.3 与既有 `StockDetailDrawer.vue` 的关系

> `StockDetailDrawer.vue` **已经存在**（位于 `frontend/src/views/stock-info/components/`），
> 当前包含三个 Tab：基本信息 / K 线图 / 归因分析。
>
> 本次新增**第四个 Tab：概念**。
> 不重写 `StockDetailDrawer.vue` 的现有逻辑，只在 `<el-tabs>` 中插入一个 `<el-tab-pane>`。

---

## 二、组件结构

### 2.1 文件清单

```
frontend/src/views/stock-info/
├── StockInfoList.vue                       ← ✏️ 改：移除 expand 列、移除概念列、新增按钮列
├── api.ts                                  ← ✏️ 改：新增 4 个 TS 类型 + 2 个 API
└── components/
    ├── StockDetailDrawer.vue               ← ✏️ 改：新增「概念」Tab 挂载点
    ├── ConceptTab.vue                      ← 🆕 新增：概念 Tab 内容（按类型分组）
    ├── ConceptTag.vue                      ← 🆕 新增：单概念 Tag（hover/click 反馈）
    ├── useStockDetailDrawer.ts             ← 🆕 新增：抽屉状态管理 composable
    ├── AddToPoolDialog.vue                 ← 不变
    ├── KLineDrawerTab.vue                  ← 不变
    ├── MiniKlineChart.vue                  ← 不变
    └── StockExpandRow.vue                  ← ❌ 删除：被详情按钮取代
```

### 2.2 组件层级

```
StockInfoList.vue
└── 表格（el-table）
    ├── el-table-column type="selection"        ← 固定列
    ├── el-table-column prop="symbol"            ← 固定列
    ├── el-table-column prop="name"              ← 固定列
    ├── el-table-column label="已加入池"          ← 固定列
    ├── el-table-column ... (其他滚动列)          ← 滚动列
    └── el-table-column label="操作"             ← 固定列（右侧）🆕
        └── el-button "详情"                      ← 🆕 强化按钮

StockInfoList.vue（模板根部）
└── <StockDetailDrawer />                       ← 🆕 绑定
    └── <el-tabs>
        ├── el-tab-pane label="基本信息"
        ├── el-tab-pane label="K 线图"
        ├── el-tab-pane label="概念"            ← 🆕 新增
        │   └── <ConceptTab />                  ← 🆕 组件
        │       └── <ConceptTag v-for="c" />   ← 🆕 组件
        └── el-tab-pane label="归因分析"
```

### 2.3 组件职责

| 组件 | 职责 | 输入（props） | 输出（emits） |
|------|------|--------------|--------------|
| `StockInfoList.vue` | 表格 + 工具栏 + 抽屉容器 | （页面级） | （无） |
| `StockDetailDrawer.vue` | 抽屉容器 + Tab 切换 | `modelValue`、`stock`、`prefetchConcepts?` | `update:modelValue`、`addToPool`、`goAnalysis`、`close` |
| `ConceptTab.vue` | 概念 Tab 内容（拉数据 + 分组渲染） | `symbol`、`stock_name?` | `conceptClick` |
| `ConceptTag.vue` | 单概念 Tag（hover/click） | `concept: ConceptGroupedVO` | `click` |
| `useStockDetailDrawer.ts` | 抽屉状态管理 composable | （无） | `{ visible, currentStock, open, close }` |

### 2.4 完整组件代码

#### 2.4.1 `ConceptTag.vue`

```vue
<!--
 * components/ConceptTag.vue
 *
 * 单个概念 Tag，带 hover/click 反馈、tooltip、按 concept_type 染色。
 -->
<template>
  <el-tooltip
    :content="concept.description || '点击查看概念详情'"
    placement="top"
    :show-after="200"
  >
    <el-tag
      :type="tagType"
      :effect="hovered ? 'dark' : 'plain'"
      round
      class="concept-tag"
      :class="{ 'is-clickable': true }"
      @mouseenter="hovered = true"
      @mouseleave="hovered = false"
      @click.stop="$emit('click', concept)"
    >
      <el-icon v-if="iconForType" class="mr-1"><component :is="iconForType" /></el-icon>
      {{ concept.name }}
    </el-tag>
  </el-tooltip>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  OfficeBuilding,    // industry
  MagicStick,        // theme
  TrendCharts,      // style
  Location,         // region
  Bell,             // event
  Question,         // other
} from '@element-plus/icons-vue'
import type { ConceptGroupedVO, ConceptType } from '@/views/stock-info/api'

const props = defineProps<{ concept: ConceptGroupedVO }>()
defineEmits<{ click: [c: ConceptGroupedVO] }>()

const hovered = ref(false)

const tagType = computed(() => {
  const map: Record<ConceptType, 'primary' | 'success' | 'warning' | 'info' | 'danger'> = {
    industry: 'primary',
    theme:    'success',
    style:    'warning',
    region:   'info',
    event:    'danger',
    other:    'info',
  }
  return map[props.concept.concept_type] || 'info'
})

const iconForType = computed(() => {
  const map: Record<ConceptType, any> = {
    industry: OfficeBuilding,
    theme:    MagicStick,
    style:    TrendCharts,
    region:   Location,
    event:    Bell,
    other:    Question,
  }
  return map[props.concept.concept_type]
})
</script>

<style scoped>
.concept-tag {
  margin: 0 4px 6px 0;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.concept-tag.is-clickable:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
</style>
```

#### 2.4.2 `ConceptTab.vue`

```vue
<!--
 * components/ConceptTab.vue
 *
 * 详情抽屉「概念」Tab 的内容组件。
 *
 * 数据流：
 *   props.symbol → watch → getConceptTabForSymbol(symbol) → data
 *   data.sections → v-for 渲染分组
 *   ConceptTag 点击 → emit('conceptClick', c) → 由 StockDetailDrawer 上抛
 */
<template>
  <div v-loading="loading" class="concept-tab">
    <!-- 骨架屏：抽屉刚打开、用户尚未看热词时 -->
    <div v-if="!data && loading" class="concept-skeleton">
      <el-skeleton :rows="4" animated />
    </div>

    <!-- 正常渲染 -->
    <template v-else-if="data">
      <!-- 空状态 -->
      <el-empty
        v-if="data.sections.length === 0"
        description="该股票暂无概念归属"
        :image-size="80"
      />

      <!-- 分组渲染 -->
      <div v-else>
        <div v-for="section in data.sections" :key="section.type" class="concept-section">
          <div class="section-title">
            <span class="title-text">{{ section.type_label }}</span>
            <el-tag size="small" type="info" effect="plain">{{ section.concepts.length }}</el-tag>
          </div>
          <div class="concept-list">
            <ConceptTag
              v-for="c in section.concepts"
              :key="c.concept_id"
              :concept="c"
              @click="onTagClick"
            />
          </div>
        </div>

        <!-- 底部汇总 + 刷新 -->
        <div class="concept-footer">
          <span class="text-xs text-gray-500">
            共 <b class="text-gray-900">{{ data.total_count }}</b> 个概念
            <span class="text-gray-300 ml-2">最近一次同步：{{ data.last_synced_at || '—' }}</span>
          </span>
          <el-link type="primary" :underline="false" @click="reload">
            <el-icon class="mr-1"><Refresh /></el-icon>刷新
          </el-link>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getConceptTabForSymbol,
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

async function load() {
  if (!props.symbol) return
  loading.value = true
  try {
    data.value = await getConceptTabForSymbol(props.symbol, {
      stock_name: props.stock_name,
    })
  } catch (e) {
    ElMessage.error('加载概念失败: ' + (e as Error).message)
    data.value = null
  } finally {
    loading.value = false
  }
}

async function reload() {
  await load()
}

function onTagClick(c: ConceptGroupedVO) {
  emit('conceptClick', c)
  // 未来可路由到 /home/concept/{id}
  // 当前阶段仅占位反馈：
  ElMessage.info(`点击了概念：${c.name}（${c.source}）`)
}

watch(() => props.symbol, load, { immediate: true })
</script>

<style scoped>
.concept-tab {
  min-height: 200px;
}

.concept-skeleton {
  padding: 8px 0;
}

.concept-section {
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
  border-left: 3px solid #3b82f6;
  padding-left: 8px;
}

.title-text {
  letter-spacing: 0.5px;
}

.concept-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  min-height: 24px;
}

.concept-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed #e5e7eb;
  margin-top: 8px;
}
</style>
```

#### 2.4.3 `StockDetailDrawer.vue`（节选新增 Tab 部分）

> 完整文件保留现有逻辑，仅在 `<el-tabs>` 中插入新增 Tab。

```diff
   <el-tabs v-model="activeTab" class="drawer-tabs">
     <el-tab-pane label="基本信息" name="info">...</el-tab-pane>
     <el-tab-pane label="K 线图" name="kline">
       <KLineDrawerTab :symbol="stock.symbol" />
     </el-tab-pane>
+    <el-tab-pane label="概念" name="concepts">
+      <ConceptTab
+        v-if="stock"
+        :symbol="stock.symbol"
+        :stock-name="stock.name"
+        @concept-click="onConceptClick"
+      />
+    </el-tab-pane>
     <el-tab-pane label="归因分析" name="analysis">...</el-tab-pane>
   </el-tabs>
```

```diff
   <script setup lang="ts">
   import { ref, watch } from 'vue'
   import { Folder, DataLine } from '@element-plus/icons-vue'
   import KLineDrawerTab from './KLineDrawerTab.vue'
+  import ConceptTab from './ConceptTab.vue'
+  import type { ConceptGroupedVO } from '@/views/stock-info/api'
   import type { StockInfo } from '@/views/stock-info/api'

   const props = defineProps<{
     modelValue: boolean
     stock: StockInfo | null
+    prefetchConcepts?: boolean  // 🆕
   }>()

   defineEmits<{
     'update:modelValue': [value: boolean]
     addToPool: []
     goAnalysis: []
   }>()

   const activeTab = ref('info')

   watch(() => props.modelValue, (visible) => {
     if (visible) activeTab.value = 'info'
   })

+  function onConceptClick(c: ConceptGroupedVO) {
+    // 占位：未来跳到概念详情页 / 打开新抽屉
+    console.log('[StockDetailDrawer] concept click', c)
+  }
   </script>
```

#### 2.4.4 `useStockDetailDrawer.ts` composable

```typescript
// composables/useStockDetailDrawer.ts
/**
 * 详情抽屉状态管理 composable
 *
 * 解耦 StockInfoList 与 StockDetailDrawer 的状态：
 * - visible：抽屉开关
 * - currentStock：当前展示的股票
 * - open(row)：打开抽屉
 * - close()：关闭抽屉（延迟清空避免动画闪屏）
 */
import { ref } from 'vue'
import type { StockInfo } from '@/views/stock-info/api'

export function useStockDetailDrawer() {
  const visible = ref(false)
  const currentStock = ref<StockInfo | null>(null)

  function open(stock: StockInfo) {
    currentStock.value = stock
    visible.value = true
  }

  function close() {
    visible.value = false
    // 延迟清空，等抽屉关闭动画（约 300ms）结束
    setTimeout(() => {
      currentStock.value = null
    }, 300)
  }

  return { visible, currentStock, open, close }
}
```

---

## 三、详情按钮的强化设计

### 3.1 设计目标

让用户在任何一行都能**一眼定位**「详情」按钮，鼠标滑过时**立即感知**这是可点击的入口。

### 3.2 视觉对比

```
─── 旧：type="expand" 列（行首） ─────────────────
┌─────────────────────────────────────────────────────────┐
│ ⊞ │ 002229 │ 鸿博股份 │ + 其它 13 列... │ <空白行>      │
└─────────────────────────────────────────────────────────┘
↑
默认小箭头，灰色，与背景同色，几乎"看不见"


─── 新：「详情」按钮列（行末，fixed="right"） ─────────
┌─────────────────────────────────────────────────────────┐
│   002229 │ 鸿博股份 │ ... │ 已加入 2 个池 │ 🔍 详情 🟦   │
└─────────────────────────────────────────────────────────┘
                                              ↑
                                  primary 蓝色、圆角、带图标
```

### 3.3 多维度强化清单

| 维度 | 取值 | 理由 |
|------|------|------|
| **位置** | `fixed="right"`（行末） | 用户读完一行基本信息后，视线自然落到右侧 |
| **颜色** | `type="primary"`（Element Plus 蓝色） | 与工具栏的「同步最新数据」按钮同色，认知一致 |
| **形状** | `round`（圆角） | 比方角更亲和，比纯圆更专业 |
| **尺寸** | `size="default"` | 比 `small` 大 30%，足够醒目 |
| **图标** | `<el-icon><View /></el-icon>` | 视觉锚点，提示"查看"语义 |
| **文字** | 「详情」 | 直接告诉用户点开会发生什么 |
| **变体** | `plain`（淡色填充） | 不喧宾夺主，hover 时变 `dark` 强反馈 |
| **间距** | 按钮间 4px gap | 多按钮时仍清晰 |
| **动画** | hover 提升 +1px + box-shadow | 微动效暗示可点击 |
| **无障碍** | `aria-label="打开 ${stock.symbol} 详情抽屉"` | 屏幕阅读器友好 |
| **键盘** | Tab 可聚焦 + Enter 触发 | 键盘可达性 |
| **阻止冒泡** | `@click.stop` | 不触发行选中 / 高亮 |

### 3.4 模板代码

```vue
<el-table-column
  label="操作"
  width="110"
  fixed="right"
  align="center"
>
  <template #default="{ row }">
    <el-button
      type="primary"
      size="default"
      round
      plain
      class="row-detail-btn"
      :aria-label="`打开 ${row.symbol} 详情抽屉`"
      @click.stop="openDetailDrawer(row)"
    >
      <el-icon class="mr-1"><View /></el-icon>
      详情
    </el-button>
  </template>
</el-table-column>
```

### 3.5 样式强化（可选追加）

```scss
<style scoped>
.row-detail-btn {
  font-weight: 600;
  letter-spacing: 1px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.row-detail-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25);
}

.row-detail-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 4px rgba(59, 130, 246, 0.2);
}

/* 暗色主题适配（如果未来需要） */
@media (prefers-color-scheme: dark) {
  .row-detail-btn {
    background: rgba(59, 130, 246, 0.15);
  }
}
</style>
```

### 3.6 多入口设计

为兼顾不同用户习惯，**保留两条触发路径**：

| 入口 | 实现 | 触发场景 |
|------|------|---------|
| **行末「详情」按钮**（主要） | `@click.stop="openDetailDrawer(row)"` | 精确点击 |
| **行点击**（辅助） | `@row-click="(row) => openDetailDrawer(row)"` | 整行点击爱好者 |

两条路径等价进入同一抽屉，避免用户混淆"点行 vs 点按钮"的差异。

### 3.7 可访问性 / 体验兜底

| 兜底 | 描述 |
|------|------|
| **首次打开预热** | 抽屉打开时同时调 `/concepts/by-symbol/{symbol}` 拉简略版（如 `row.concepts` 为空），避免 Tab 切到「概念」时空白闪烁 |
| **空状态** | `ConceptTab` 内部 `el-empty description="该股票暂无概念归属"` |
| **错误状态** | `ElMessage.error('加载概念失败: ...')`，并把 `data` 置 null 触发重新加载 |
| **加载状态** | `v-loading="loading"` 全局 + 骨架屏占位 |
| **键盘 Escape** | Element Plus `el-drawer` 默认支持 |
| **路由复用** | 未来可支持 `?drawer=002229` 直接打开特定股票抽屉（详见 §6） |

---

## 四、StockInfoList.vue 改造 diff 总览

```diff
 <script setup lang="ts">
 import { ref, computed, onMounted } from 'vue'
 import { useRouter } from 'vue-router'
 import { ElMessage } from 'element-plus'
-import { Search, Refresh, Folder, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
+import {
+  Search, Refresh, Folder, ArrowDown, ArrowUp, View,
+} from '@element-plus/icons-vue'

 import PageWrapper from '@/components/PageWrapper.vue'
-import StockExpandRow from './components/StockExpandRow.vue'
 import AddToPoolDialog from './components/AddToPoolDialog.vue'
+import StockDetailDrawer from './components/StockDetailDrawer.vue'
+import { useStockDetailDrawer } from './composables/useStockDetailDrawer'
+import type { StockInfo, StockMeta, StockQueryParams, PoolMembership } from '@/views/stock-info/api'
```

```diff
   // ── 展开行 / 弹窗 ──────────────────────────────
   const tableRef = ref()
-  const expandedRows = ref<string[]>([])
   const addToPoolVisible = ref(false)
+  // 🆕 详情抽屉
+  const {
+    visible: detailDrawerVisible,
+    currentStock: detailDrawerStock,
+    open: openDetailDrawer,
+    close: closeDetailDrawer,
+  } = useStockDetailDrawer()
```

```diff
-  // ── 展开行 ─────────────────────────────
-  function toggleExpand(row: StockInfo) {
-    const idx = expandedRows.value.indexOf(row.symbol)
-    if (idx >= 0) {
-      expandedRows.value.splice(idx, 1)
-    } else {
-      expandedRows.value = [row.symbol]
-    }
-  }
+  // ── 详情抽屉 ─────────────────────────────
+  // 由 composable 接管 open/close
+  function onDrawerAddToPool() {
+    // 把当前股票加入池（复用既有逻辑）
+    if (detailDrawerStock.value) {
+      // 把抽屉股票作为唯一选中项
+      selectedStocks.value = [detailDrawerStock.value]
+      addToPoolVisible.value = true
+      // 关闭抽屉，让 AddToPoolDialog 居中显示
+      closeDetailDrawer()
+    }
+  }
+  function onDrawerGoAnalysis() {
+    if (detailDrawerStock.value) {
+      router.push(`/home/stock/${detailDrawerStock.value.symbol}/analysis`)
+      closeDetailDrawer()
+    }
+  }
```

```diff
   <el-table
     ref="tableRef"
     v-loading="loading"
     :data="stocks"
     stripe
     class="flex-1"
     highlight-current-row
     empty-text="没有匹配的股票"
     row-key="symbol"
-    :expand-row-keys="expandedRows"
-    @row-click="toggleExpand"
+    @row-click="openDetailDrawer"
     @selection-change="onSelectionChange"
   >
-    <el-table-column type="expand">
-      <template #default="{ row }">
-        <StockExpandRow :symbol="row.symbol" />
-      </template>
-    </el-table-column>

     <!-- 固定列（左侧） -->
     <el-table-column type="selection" width="50" fixed="left" />
     ...
```

```diff
+    <!-- 行末「详情」按钮列（强化） -->
+    <el-table-column
+      label="操作"
+      width="110"
+      fixed="right"
+      align="center"
+    >
+      <template #default="{ row }">
+        <el-button
+          type="primary"
+          size="default"
+          round
+          plain
+          class="row-detail-btn"
+          :aria-label="`打开 ${row.symbol} 详情抽屉`"
+          @click.stop="openDetailDrawer(row)"
+        >
+          <el-icon class="mr-1"><View /></el-icon>
+          详情
+        </el-button>
+      </template>
+    </el-table-column>
   </el-table>
```

```diff
   <AddToPoolDialog
     v-model="addToPoolVisible"
     :stocks="selectedStocks"
     @done="onPoolDone"
   />
+
+  <!-- 🆕 详情抽屉 -->
+  <StockDetailDrawer
+    v-model="detailDrawerVisible"
+    :stock="detailDrawerStock"
+    @add-to-pool="onDrawerAddToPool"
+    @go-analysis="onDrawerGoAnalysis"
+    @close="closeDetailDrawer"
+  />
```

---

## 五、API 调用时机优化

### 5.1 请求时序图

```
时间轴 ─────────────────────────────────────────────────────────→

[用户进入列表页]
  │ GET /api/v1/stock-panel/?page=1&with_concepts=true
  │ ─→ items[].concepts: ConceptBrief[]
  ▼
[用户滚动 / 切筛选]  ─→ 重复请求（防抖 300ms）

[用户点击某行「详情」按钮]
  │ openDetailDrawer(row)
  │ 抽屉打开，row 注入到 StockDetailDrawer
  ▼
[抽屉渲染] activeTab 默认 "info"
  │ 不发请求（基本信息已在 row 中）
  ▼
[用户切到「概念」Tab]
  │ ConceptTab 挂载 → watch(symbol, immediate=true)
  │ GET /api/v1/concepts/tab-by-symbol/{symbol}?stock_name=鸿博股份
  │ ─→ ConceptTabContentVO
  ▼
[ConceptTab 渲染分组]
  │ v-for section in data.sections
  │ ConceptTag v-for
  ▼
[用户点击 ConceptTag]
  │ emit('conceptClick', c)
  │ 当前占位 ElMessage.info；未来跳概念详情页
```

### 5.2 缓存层级

| 层级 | 数据 | 时机 | 失效策略 |
|------|------|------|---------|
| **L1：StockPanelItemVO.concepts** | `ConceptBrief[]`（简略） | 列表请求时下发 | 翻页 / 筛选切换即失效 |
| **L2：ConceptTabContentVO** | `ConceptTabSectionVO[]`（分组） | 抽屉切到「概念」Tab | `Reload` 按钮手动失效；窗口关闭后失效 |

> **未来优化**：可接入 `useQuery` / `swrv` 做请求缓存（避免同一 symbol 重复打开抽屉重复请求）。
> 本期先以本地 ref 实现，预留 composable 抽象。

---

## 六、未来演进（Roadmap）

### 6.1 概念详情页 / 抽屉（v1.1）

- 当前：`ConceptTag` 点击 → 仅 `ElMessage.info` 占位
- 未来：跳到 `/home/concept/{concept_id}` 概念详情页
  - 显示：成分股列表 + 该概念的 KLine / 涨跌幅
  - 复用 `StockDetailDrawer.vue` 的 Tab 结构（基本信息 / K线 / 成分股 / 同步状态）

### 6.2 概念筛选（v1.1）

- 在工具栏高级筛选区新增「概念」多选下拉
- `GET /api/v1/stock-panel/?concepts=1042,1088` 后端过滤
- 仓储新增 `list_concepts_by_panel_filters`

### 6.3 路由支持（v1.2）

- 支持 `?drawer=002229` 直接打开特定股票详情抽屉
- 路由变化触发 `openDetailDrawer(stock)`
- 抽屉关闭清除 URL 参数（避免污染历史栈）

### 6.4 概念热力图（v1.3）

- 在 `ConceptTab` 顶部加一行「概念热度柱状图」
- 数据来源：`GET /api/v1/concepts/?order_by=pct_change&limit=10`
- 点击柱状图项 → 跳转该概念详情

---

## 七、测试要点（设计阶段先列）

| 测试 | 类型 | 覆盖 |
|------|------|------|
| `ConceptTag.spec.ts` | 单元 | 各 `concept_type` 对应正确的 `tagType` / icon；hover 效果；click 通过 emit |
| `ConceptTab.spec.ts` | 单元 | 加载 / 成功 / 空 / 错误四态；reload 按钮触发；emit 上抛 |
| `useStockDetailDrawer.spec.ts` | 单元 | open / close / 清空延迟 |
| `StockInfoList.spec.ts`（可选） | 集成 | 点击按钮 / 行点击均能打开抽屉；按钮不被选中影响 |
| `StockDetailDrawer.spec.ts`（可选） | 集成 | 概念 Tab 切换触发数据加载 |

## 八、设计取舍

### 8.1 为什么不用 `<el-popover>` 展示概念？

| 选项 | 优 | 劣 |
|------|----|----|
| **A. 列内 Popover** | 即点即看 | ❌ 桌面端点击区域小，移动端易误触；多概念场景拥挤 |
| **B. 列内 tooltip** | 极轻量 | ❌ 只读，无法跳转 / 操作 |
| **C. 抽屉 Tab** ⭐ | 空间充足、可交互、可扩展 | 需要一次点击进入 |

### 8.2 为什么删 `StockExpandRow.vue` 而不是保留？

| 选项 | 优 | 劣 |
|------|----|----|
| **A. 保留** | 用户可继续用展开行看 KLine | ❌ 双入口导致用户困惑（点行展开 vs 点按钮开抽屉）；KLine 抢眼；维护两套交互 |
| **B. 删除** ⭐ | 单一入口更清晰 | 老用户需要重新适应 |

### 8.3 为什么 `with_concepts=true` 默认还要传？

虽然概念不在列里渲染了，但抽屉打开时若 `row.concepts` 已带简略版，
可立即渲染骨架屏（避免 Tab 切换空白闪烁）。

如果未来统计发现 `with_concepts=true` 带来的请求体积显著大于收益，
可改为「抽屉打开时再按需请求 `/by-symbol/{symbol}`」。

## 九、相关文档

| 文档 | 路径 | 说明 |
|------|------|------|
| 统一设计文档 | `docs/dev/06gainian/README.md` | 总览 |
| 领域层 | `docs/dev/06gainian/01-domain-design.md` | VO 定义 |
| 基础设施层 | `docs/dev/06gainian/02-infrastructure-design.md` | ORM / Repo |
| 应用层 + 路由 | `docs/dev/06gainian/03-application-and-route-design.md` | DTO / API / Service |
| 类图 | `docs/PlantUML/Concept/01-class.puml` | 跨层修改概览 |
| 数据流 | `docs/PlantUML/Concept/02-data-flow.puml` | 4 层 + 2 表 |