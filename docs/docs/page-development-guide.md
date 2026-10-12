# 页面开发指南（Agent 参考手册）

> 本文是 `layout-guide.md` 的**同伴文档**。`layout-guide.md` 讲 Shell / PageWrapper / 路由
> 这一层"骨架级"约束，本文聚焦"一页页面**内部**怎么写"——尤其是基于
> `views/stock-info/StockInfoList.vue` 样板抽象出来的"两层 rem 锚点架构"。
>
> **目标读者**：未来开发新页面、或继续演化现有页面的 Agent / 工程师。
>
> **何时读此文**：
> - 新建一个 `views/xxx/XxxList.vue` 页面时
> - 想给现有页面加密度调节、表格、分页时
> - 想复用 `StockInfoList` 的密度锚点方案到其他页面时

---

## 〇、文档地图

| 文档 | 层级 | 内容 |
|------|------|------|
| `适配性/01-rem全局密度方案.md` | 全站根 | rem 原理 + 全站 CSS 变量设计 + 根字号改造 |
| `layout-guide.md` | 骨架 | Shell / TopBar / LeftBar / MainContainer / PageWrapper / 路由结构 |
| **`page-development-guide.md`（本文）** | **页面内部** | **模板结构 / 密度锚点 / 四区实现 / Element Plus 集成** |

读完前三份文档，等于掌握了从"全站密度"到"页面局部密度"的完整链路。

---

## 一、页面锚点是什么

**页面锚点 = 整页放大缩小的单一开关**。

- 用户在标题旁的「⚙️ 页面设置」面板里拖一个 0.7 ~ 1.4 的滑块
- 这一行的控件（输入框 / 按钮 / 标签）+ 表格 + 分页器**全部**跟着等比缩放
- 实现方法：**JS 改 `<PageWrapper>` 上的 CSS 变量**，CSS 用 `calc(rem × var(--sil-page-density))` 派生

四组锚点，**整体只有 4 个数字**：

| 锚点 | 范围 | 影响范围 | 默认值 |
|------|------|---------|--------|
| **页面**（`--sil-page-density`） | 0.7 ~ 1.4 | 整页基准，下层默认跟随 | 1 |
| **顶部**（`--sil-top-density`） | 0.6 ~ 1.5 | 搜索栏 / 按钮 / 高级筛选 | `calc(var(--sil-page-density))` |
| **中部**（`--sil-middle-density`） | 0.7 ~ 1.4 | 表格 / 卡片 / 选中条 | `calc(var(--sil-page-density))` |
| **底部**（`--sil-bottom-density`） | 0.7 ~ 1.4 | 分页器 | `calc(var(--sil-page-density))` |

> **"局部锚点 = null 表示跟随"**：当用户没主动设顶部锚点，CSS 内部 `calc(var(--sil-page-density))` 自动接管，零 JS 开销。

---

## 二、为什么需要锚点（问题域）

| 痛点 | 没有锚点时 | 有锚点时 |
|------|-----------|---------|
| 屏幕小 / 用户 Win 缩放 125% | 表格行高挤、文字溢出 | 一键缩 0.8，密度立即合理 |
| 表格列多想紧凑 | 改一堆 `height: 40px` 写死 | 拖中部滑块，0.6 一刀切 |
| 顶部按钮太大、表格太小 | 不一致视觉 | 顶部 1.2 / 表格 0.8，单独调 |
| 每个尺寸都得 hardcode px | 改一个漏一片 | rem 派生，1 改全跟 |

**核心思想**：CSS 变量是 single source of truth，**所有可调尺寸只写一次 `calc(rem × density)`**，别的什么都不写。

---

## 三、完整页面骨架（伪代码 + 真实位置）

```vue
<template>
  <PageWrapper :style="densityStyle" class="my-page">
    <!-- ═══ Title Area（PagesWrapper #title 插槽）═══ -->
    <template #title>
      <el-icon class="mr-1"><SomeIcon /></el-icon>
      我的页面
      <button class="density-toggle" @click="showPanel = !showPanel">⚙️</button>
      <transition name="density-inline">
        <div v-if="showPanel" class="density-inline">
          <span>⚙️ 页面设置</span>
          <div class="density-inline__group">
            <span>页面</span>
            <el-slider v-model="pageDensity" :min="0.7" :max="1.4" />
            <span>{{ pageDensity.toFixed(2) }}</span>
          </div>
          <!-- top / middle / bottom 三个 local 锚点 -->
          <button @click="syncAreasToPage">区域跟随</button>
          <button @click="resetDensities">全部还原</button>
        </div>
      </transition>
    </template>

    <!-- ═══ Top Area（PagesWrapper #toolbar 插槽）═══ -->
    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-search">
          <el-input v-model="q" placeholder="搜索..." />
          <el-button @click="showAdv = !showAdv">高级筛选</el-button>
        </div>
        <div class="toolbar-actions">
          <el-button>操作按钮</el-button>
        </div>
      </div>
      <div class="advanced-wrapper" :class="{ open: showAdv }">
        <div class="advanced-filters">
          <!-- select / input-number 等 -->
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area（默认插槽）═══ -->
    <!-- 主要内容：表格 / 卡片 / 图表 -->
    <el-table class="my-table">...</el-table>

    <!-- ═══ Bottom Area（PagesWrapper #bottom 插槽，可选）═══ -->
    <template #bottom>
      <el-pagination v-model:current-page="page" :total="total" />
    </template>
  </PageWrapper>
</template>
```

---

## 四、密度锚点 JS 模板（粘贴即用）

<details>
<summary>展开：完整 JS 模块（含 localStorage 持久化 + 跟随逻辑 + Proxy 滑块）</summary>

```ts
// ── 锚点状态 ─────────────────────────────
type DensityShape = {
  page: number
  top: number
  middle: number
  bottom: number
}

const DENSITY_KEY = 'my-page-density'

function loadDensity(): DensityShape {
  try {
    const raw = localStorage.getItem(DENSITY_KEY)
    if (!raw) return { page: 1, top: 1, middle: 1, bottom: 1 }
    const p = JSON.parse(raw) as Partial<DensityShape>
    return {
      page:   clamp(Number(p.page   ?? 1)),
      top:    clamp(Number(p.top    ?? 1)),
      middle: clamp(Number(p.middle ?? 1)),
      bottom: clamp(Number(p.bottom ?? 1)),
    }
  } catch {
    return { page: 1, top: 1, middle: 1, bottom: 1 }
  }
}

function clamp(v: number) {
  const n = Math.max(0.6, Math.min(1.5, Number.isFinite(v) ? v : 1))
  return Math.round(n * 100) / 100
}

const pageDensity   = ref<number>(loadDensity().page)
const topDensity    = ref<number | null>(loadDensity().top    === 1 ? null : loadDensity().top)
const middleDensity = ref<number | null>(loadDensity().middle === 1 ? null : loadDensity().middle)
const bottomDensity = ref<number | null>(loadDensity().bottom === 1 ? null : loadDensity().bottom)

// ── 把数字注入 CSS 变量 ─────────────────
// region 为 null 时不注入 → CSS 内 calc(var(--sil-page-density)) 自动接管
const densityStyle = computed<Record<string, string>>(() => {
  const s: Record<string, string> = { '--sil-page-density': String(pageDensity.value) }
  if (topDensity.value    != null) s['--sil-top-density']    = String(topDensity.value)
  if (middleDensity.value != null) s['--sil-middle-density'] = String(middleDensity.value)
  if (bottomDensity.value != null) s['--sil-bottom-density'] = String(bottomDensity.value)
  return s
})

// ── 持久化 ─────────────────────────────
watch(
  [pageDensity, topDensity, middleDensity, bottomDensity],
  ([p, t, m, b]) => {
    try {
      localStorage.setItem(DENSITY_KEY, JSON.stringify({
        page: p, top: t ?? 1, middle: m ?? 1, bottom: b ?? 1,
      }))
    } catch { /* quota */ }
  },
  { deep: false },
)

// ── "区域跟随页面"按钮：设 null（CSS 自动跟随）────
function syncAreasToPage() {
  topDensity.value = null
  middleDensity.value = null
  bottomDensity.value = null
}

// ── "全部还原"按钮：所有锚点回到默认 ─────
function resetDensities() {
  pageDensity.value = 1
  topDensity.value = null
  middleDensity.value = null
  bottomDensity.value = null
}

const allSynced = computed(() =>
  topDensity.value === null
  && middleDensity.value === null
  && bottomDensity.value === null,
)

// ── Proxy 滑块：拖动即断开跟随 ─────────
// 显示 = 实际值（null 时回退到 page）
// 写入 = 直接落到局部锚点，断开跟随
const topDensityProxy = computed<number>({
  get: () => topDensity.value ?? pageDensity.value,
  set: (v) => { topDensity.value = v },
})
const middleDensityProxy = computed<number>({
  get: () => middleDensity.value ?? pageDensity.value,
  set: (v) => { middleDensity.value = v },
})
const bottomDensityProxy = computed<number>({
  get: () => bottomDensity.value ?? pageDensity.value,
  set: (v) => { bottomDensity.value = v },
})

// ── 列宽缩放函数：表格列宽跟着中部锚点走 ──
function colW(px: number): number {
  return Math.round(px * middleDensityProxy.value)
}
```

</details>

> **这套 JS 模块是页面级的复制粘贴单元**。新建一个带密度面板的页面时，**只需改 `DENSITY_KEY` 和锚点名称**（`sil` → 你自己的前缀，比如 `kline` / `pool` / `concept`）。

---

## 五、底部密码：`style scoped` 的锚点架构

每个带密度面板的页面，`<style scoped>` 必须按下面的"两层楼"骨架写：

### 5.1 顶层声明（变量挂在 root 类名下）

```css
.my-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;

  /* ── 第一层（页面锚点）── */
  --my-page-density: 1;

  /* ── 第二层（区域锚点）── 默认跟随页面 */
  --my-top-density:    calc(var(--my-page-density));
  --my-middle-density: calc(var(--my-page-density));
  --my-bottom-density: calc(var(--my-page-density));

  /* ── 派生 token：顶部 ── */
  --my-top-gap:        calc(0.5rem * var(--my-top-density));
  --my-top-button-h:   calc(2rem   * var(--my-top-density));
  --my-top-button-fs:  calc(0.95rem * var(--my-top-density));
  --my-top-input-w:    calc(220px  * var(--my-top-density));
  /* … */

  /* ── 派生 token：中部（表格）── */
  --my-middle-row-h:        calc(2.5rem   * var(--my-middle-density));
  --my-middle-cell-pad-y:   calc(0.375rem * var(--my-middle-density));
  --my-middle-cell-pad-x:   calc(0.5rem   * var(--my-middle-density));
  --my-middle-table-fs:     calc(0.857rem * var(--my-middle-density));

  /* ── 派生 token：底部（分页器）── */
  --my-bottom-pagination-fs:    calc(0.857rem * var(--my-bottom-density));
  --my-bottom-pagination-btn-w: calc(1.857rem * var(--my-bottom-density));
  --my-bottom-pagination-btn-h: calc(1.857rem * var(--my-bottom-density));
}
```

### 5.2 命名约定

| 项目 | 约定 | 例子 |
|------|------|------|
| 锚点变量 | 前缀（页面英文缩写） | `--sil-*` / `--kline-*` / `--pool-*` |
| 派生 token | `<prefix>-<area>-<attr>` | `--sil-top-button-h` |
| anchor 注入位 | 组件 root 上 `:style="densityStyle"` | `<PageWrapper :style="densityStyle" class="my-page">` |

> **为什么用前缀**：避免不同页面变量互相污染。CSS 变量沿 DOM 子树继承，
> 不前缀的话两个相邻页面会"串台"。

### 5.3 "Element Plus 写死 px"的覆盖策略

EP 大量 sass 变量在编译时写成 px，**`--el-table-row-height` 等 token 是有效的**，
但很多**内部用 px 直接写死在 class 上**（如 `.el-table .cell { padding: 0 12px }`）。

**覆盖方法**：在 `.my-table` / `.my-pagination` 标记类内，**用 `:deep()` 强覆盖**：

```css
.my-table :deep(.el-table__cell) {
  padding-block: calc(8px * var(--my-middle-density));
}
.my-table :deep(.el-table .cell) {
  padding-inline: calc(12px * var(--my-middle-density));
  line-height:   calc(23px * var(--my-middle-density));
}
.my-pagination :deep(.btn-prev),
.my-pagination :deep(.btn-next),
.my-pagination :deep(.el-pager li) {
  padding: 0 calc(4px * var(--my-bottom-density));
  font-size: var(--my-bottom-pagination-fs);
}
```

> ⚠️ **不能用 `--el-font-size-base`**：那是 EP 全局字号源，**改了会反向影响其他页面的按钮 / 输入框**。每个页面**只覆盖自己**用到的 EP token。

---

## 六、Title Area · 标题区实现规范

### 6.1 标准结构

```vue
<template #title>
  <el-icon class="mr-1"><Stock /></el-icon>
  我的页面
  <span class="page-title-text">{{ TITLE }}</span>

  <button class="density-toggle" :class="{ active: showPanel }" @click="showPanel = !showPanel">
    <el-icon><Setting /></el-icon>
  </button>

  <transition name="density-inline">
    <div v-if="showPanel" class="density-inline">
      <!-- 4 个滑块 + 2 个按钮 -->
    </div>
  </transition>
</template>
```

### 6.2 ⚙️ 按钮 + 内联面板规范

**按钮（`density-toggle`）**：

| 属性 | 值 | 原因 |
|------|------|------|
| `width / height` | `1.625rem` 固定 | 不参与 density 缩放，永远紧凑 |
| `active` 类背景 | `linear-gradient(135deg, #dbeafe, #bfdbfe)` | 表示"已展开" |
| 颜色 / 边框 / 阴影 | hover / active 两态 | 见样板 |

**内联面板（`density-inline`）**：见下文"内联面板：横向滚动模式"。

### 6.3 标题文字防溢出

标题区域是 `display: flex`，**长标题可能撑高 / 换行**，必须有：

```css
.page-title-text {
  white-space: nowrap;  /* 永远单行 */
}
```

---

## 七、Top Area · 顶部区实现规范

### 7.1 标准结构

```vue
<template #toolbar>
  <!-- 第一行：搜索 + 操作 -->
  <div class="toolbar-row">
    <div class="toolbar-search">
      <el-input v-model="q" placeholder="..." />
      <el-button @click="showAdv = !showAdv">高级筛选</el-button>
      <el-button v-if="hasActive" type="danger" link>重置</el-button>
    </div>
    <div class="toolbar-actions">
      <el-button>操作</el-button>
    </div>
  </div>

  <!-- 第二行：高级筛选（grid-rows 动画，无 v-if）-->
  <div class="advanced-wrapper" :class="{ open: showAdv }">
    <div class="advanced-filters">
      <el-select>...</el-select>
      <el-input-number>...</el-input-number>
    </div>
  </div>
</template>
```

### 7.2 toolbar-row 三件套

```css
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--my-top-gap);
}
.toolbar-search {
  display: flex;
  align-items: center;
  gap: var(--my-top-gap);
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--my-top-gap);
  flex-shrink: 0;          /* 操作按钮不被压缩 */
}
```

### 7.3 高级筛选 grid-rows 动画

**禁止使用 `<transition>` + `v-if` + `max-height`**（详见 `layout-guide.md` §3.2）。

```vue
<div class="advanced-wrapper" :class="{ open: showAdv }">
  <div class="advanced-filters">
    <!-- 筛选控件，DOM 一直在，只是被收起 -->
  </div>
</div>
```

```css
.advanced-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.advanced-wrapper.open {
  grid-template-rows: 1fr;
}
.advanced-wrapper > .advanced-filters {
  overflow: hidden;
  min-height: 0;
  padding: 0 var(--my-top-filter-px);
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.advanced-wrapper.open > .advanced-filters {
  padding: var(--my-top-filter-py) var(--my-top-filter-px);
}
```

### 7.4 EP select / input-number 的"像素级一致"

```css
/* 强制覆盖 sass 固化的 padding，让 select 与 input-number 像素级一致 */
.advanced-filters :deep(.el-select__wrapper),
.advanced-filters :deep(.el-input-number .el-input__wrapper) {
  min-height: var(--my-top-control-h);
  padding: 4px 11px;
  line-height: calc(var(--my-top-control-h) - 8px);
  box-sizing: border-box;
}
.advanced-filters :deep(.el-input-number .el-input__inner) {
  height: calc(var(--my-top-control-h) - 8px);
  line-height: calc(var(--my-top-control-h) - 8px);
}
```

### 7.5 搜索规范

| 规则 | 原因 |
|------|------|
| 每个页面**只有一个**主搜索 | 避免歧义，UX 统一 |
| 高级筛选默认折叠 | 大部分用户用不到 |
| 高级筛选有激活条件时按钮显示 badge | 视觉提示 |
| 重置按钮**始终可见且一键全清** | 降低挫败感 |

---

## 八、Middle Area · 中部区实现规范

### 8.1 一般原则

- 中部是 `flex: 1` 自动撑满上下之间的空间
- **内容超出时**中部自身 `overflow: auto`（已由 PageWrapper 提供）
- 表格 / 卡片 / 图表都在中部，**它们自己的滚动交给自身处理**

### 8.2 表格（`el-table`）容器规范

**核心不变式（5 条，全局稳定）**：

```css
/* (1) 表格外层容器必须 min-width:0，否则被 inner 撑爆 */
.my-table {
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

/* (2) outer <el-table>：宽度严格 = 父宽，不让 inner 撑出去
 *    当列宽总和 > outer 时，inner-wrapper 自行 overflow-x:auto 滚动 */
.my-table :deep(.el-table) {
  display: block;
  width: 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  overflow: hidden;
}

/* (3) inner-wrapper 维持外层滚动控制 */
.my-table :deep(.el-table__inner-wrapper) {
  width: 100%;
  max-width: 100%;
  overflow: visible;        /* 不能 max-width 截断，否则 colspan 的 expand cell 被压窄 */
}

/* (4) body / header table：table-layout:fixed + max-width:100% */
.my-table :deep(.el-table__header),
.my-table :deep(.el-table__body) {
  table-layout: fixed;
  width: 100%;
  max-width: 100%;
}

/* (5) header-wrapper 也跟着 100% */
.my-table :deep(.el-table__header-wrapper) {
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}
```

### 8.3 表格与 density 的集成

```css
/* 中部锚点 → EP 表格主题变量重声明（仅本页生效） */
.my-page :deep(.el-table) {
  --el-table-row-height:          var(--my-middle-row-h);
  --el-table-cell-padding-block:  var(--my-middle-cell-pad-y);
  --el-table-cell-padding-inline: var(--my-middle-cell-pad-x);
  --el-table-font-size:           var(--my-middle-table-fs);
  --el-table-header-font-size:    var(--my-middle-table-fs);
  --el-table-cell-font-size:      var(--my-middle-table-fs);
}

/* EP "写死 px" 的逐项覆盖 */
.my-table :deep(.el-table__cell) {
  padding-block: calc(8px * var(--my-middle-density));
}
.my-table :deep(.el-table .cell) {
  padding-inline: calc(12px * var(--my-middle-density));
  line-height:   calc(23px * var(--my-middle-density));
}
.my-table :deep(.el-table__expand-icon) {
  width:  calc(23px * var(--my-middle-density));
  height: calc(23px * var(--my-middle-density));
}
.my-table :deep(.el-table__expanded-cell) {
  padding: calc(16px * var(--my-middle-density)) calc(20px * var(--my-middle-density));
}
```

### 8.4 表格列宽跟着中部锚点走

```vue
<el-table-column :width="colW(100)" />
```

```ts
function colW(px: number) { return Math.round(px * middleDensityProxy.value) }
```

### 8.5 选中提示条（如有）

中部常需要一个 selection-bar（"已选 3 / 取消"），**它是 flex 父级中的 `flex-shrink: 0` 子项**：

```css
.selection-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: var(--my-middle-sel-gap);
  padding: var(--my-middle-sel-py) var(--my-middle-sel-px);
  font-size: var(--my-middle-sel-fs);
}
```

---

## 九、Bottom Area · 底部区实现规范

### 9.1 标准结构

```vue
<template #bottom>
  <div class="bottom-area-inner">
    <el-pagination
      class="my-pagination"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[20, 50, 100, 200]"
      layout="total, sizes, prev, pager, next, jumper"
      small
      background
    />
  </div>
</template>
```

### 9.2 分页器容器

```css
.bottom-area-inner {
  display: flex;
  justify-content: flex-end;       /* 永远靠右 */
  align-items: center;
  padding-top: var(--my-bottom-pagination-pt);
}
```

### 9.3 分页器与 density 集成

```css
/* EP 主题变量重声明（仅本页生效） */
.my-page :deep(.el-pagination) {
  --el-pagination-font-size:      var(--my-bottom-pagination-fs);
  --el-pagination-button-width:   var(--my-bottom-pagination-btn-w);
  --el-pagination-button-height:  var(--my-bottom-pagination-btn-h);
  /* small 模式 */
  --el-pagination-font-size-small:     var(--my-bottom-pagination-fs);
  --el-pagination-button-width-small:  var(--my-bottom-pagination-btn-w);
  --el-pagination-button-height-small: var(--my-bottom-pagination-btn-h);
  --el-pagination-item-gap: calc(16px * var(--my-bottom-density));
}

/* 内部 "写死 px" 逐项覆盖（用 .my-pagination 标记类精准锁定） */
.my-pagination :deep(.btn-prev),
.my-pagination :deep(.btn-next),
.my-pagination :deep(.el-pager li) {
  padding: 0 calc(4px * var(--my-bottom-density));
  font-size: var(--my-bottom-pagination-fs);
}
.my-pagination :deep(.el-pagination__editor.el-input) {
  width: calc(56px * var(--my-bottom-density));
}
.my-pagination :deep(.el-pagination .el-select) {
  width: calc(128px * var(--my-bottom-density));
}
```

### 9.4 分页器位置约定

| 场景 | 布局 |
|------|------|
| 有 `#bottom` 插槽 | 分页器**固定在底部**，表格区域自动压缩 |
| 没传 `#bottom` 插槽 | PageWrapper 自动让 middle 延伸到页面底部 |

---

## 十、内联面板 · `density-inline` 横向滚动模式（重点）

> 这是本项目特有的"密度面板与标题同行"实现，**当面板内容超出 main-container 宽度时，横向滚动而不是撑高 / 遮盖**。

### 10.1 设计目标

1. 面板与标题、⚙️ 按钮**同一行**展示，节省垂直空间
2. 面板总高度固定 40px（2.5rem），**不反向撑高 .top-area__header**
3. 面板宽度受 main-container 宽度约束，**永不超出**
4. 内容超出时**横向溢出滚动**，可见可交互
5. flex 子项能让父级压缩（min-width: 0），内层 group 不被压缩

### 10.2 完整 CSS（直接复用）

```css
.density-inline {
  /* ── 高度锁定（不撑高父 .top-area__header）── */
  height: 2.5rem;
  max-height: 2.5rem;
  display: flex;
  align-items: center;
  align-self: center;        /* cross-axis 锁定位置 */

  /* ── 宽度：让父级（.top-area__title）能压缩自身 ── */
  flex-grow: 1;
  flex-basis: 0;             /* 忽略内容尺寸，按比例分配 */
  min-width: 0;              /* ⭐ 关键：让 flex 子项能收缩到内容 min-content 以下 */
  flex-wrap: nowrap;
  overflow-x: auto;          /* ⭐ 关键：内部超出时滚动 */
  overflow-y: hidden;

  scrollbar-width: thin;
  scrollbar-color: #93c5fd transparent;

  gap: 0.5rem;
  padding: 0 0.625rem;
  margin-left: 0.357rem;
  background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
  border: 1px dashed #93c5fd;
  border-radius: 6px;
  font-size: 0.857rem;
  color: #1e40af;
}

/* ── 内层 group 保持 flex-shrink:0（保持 slider / button 原始尺寸）── */
.density-inline__group {
  display: inline-flex;
  align-items: center;
  gap: 0.357rem;
  white-space: nowrap;
  flex-shrink: 0;            /* ⭐ 关键：让外层压缩到这个 group 时不再继续压缩 */
}

/* ── WebKit 滚动条美化（与顶栏主题一致）── */
.density-inline::-webkit-scrollbar { height: 4px; }
.density-inline::-webkit-scrollbar-track { background: transparent; }
.density-inline::-webkit-scrollbar-thumb { background: #93c5fd; border-radius: 2px; }
.density-inline::-webkit-scrollbar-thumb:hover { background: #60a5fa; }

/* ── 内部 slider / button 锁死尺寸，避免被 density 缩放 ── */
.density-inline :deep(.el-slider) { width: 60px; height: 16px; margin: 0; }
.density-inline :deep(.el-slider__runway) { height: 4px; }
.density-inline :deep(.el-slider__bar) { height: 4px; }
.density-inline :deep(.el-slider__button) { width: 12px; height: 12px; }
.density-inline :deep(.el-button) {
  height: 22px;
  padding: 0 10px;
  font-size: 0.78rem;
  margin: 0;
}
```

### 10.3 配套的父级覆盖（.top-area__header 自适应）

页面级有 density-inline 时，必须覆盖两个父级 class：

```css
/* 让 .top-area__header 高度自适应内容（不被写死 32px 裁切）*/
.my-page :deep(.top-area__header) {
  min-height: var(--density-title-min);  /* 最小 32px 兜底 */
  height: auto;                          /* 自然撑到 max(32px, 40px) */
}

/* 让 .top-area__title flex 容器可收缩（min-width:0）*/
.my-page :deep(.top-area__title) {
  min-width: 0;
}
```

> **关键原理链**：
> ```
> .main-container (Shell 主区)
>   └── .page-slot (flex: 1, width: 100%)
>        └── PageWrapper (.page-wrapper)
>             └── .top-area__header (height: auto, min-width:0)
>                  └── .top-area__title (display:flex, min-width:0)  ← 父级可收缩
>                       └── .density-inline (max-width:100%, flex:1 1 0, min-width:0, overflow-x:auto) ← 不撑爆
>                            └── .density-inline__group (flex-shrink:0)  ← 子项保持尺寸
> ```

### 10.4 进入 / 离开动画

```css
.density-inline-enter-active,
.density-inline-leave-active {
  transition: opacity 0.22s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.22s cubic-bezier(0.4, 0, 0.2, 1);
}
.density-inline-enter-from,
.density-inline-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
```

### 10.5 ⚠️ 反面教材

| 错误 | 后果 |
|------|------|
| `.density-inline { flex-shrink: 0 }` | 不能被压缩 → min-content 撑大父 → 横向溢出 main-container |
| `.density-inline { max-width: calc(100vw - 24rem) }` | 用 viewport 估算，不准，会算错 |
| `.density-inline { white-space: nowrap }` | 与 overflow-x 冲突，且 flex-wrap:nowrap 已强制单行 |
| `.density-inline { overflow: hidden }` | 内容被硬切断，看不到 |
| `.top-area__title { /* 默认 flex }` | 缺 `min-width: 0`，子项 min-content 撑大整个链 |

### 10.6 内部高度锁死是防线的"外层"——`expand-row` 一类"内联展开型组件"的外部高度锁死原则

> **核心原则（一句话）**：**内部能多小做多小，但只要外容器不定，内部就有机会撑爆**。
>
> 这条原则适用于**所有"内联展开型组件"**——典型场景：
> - `expand-row`（表格行内嵌展开区：chips / 摘要 / 子表 / toolbar）
> - `density-inline`（已在 §十.2 落实）
> - 任何"在同一行 / 同一卡片内、由数据异步驱动内容显隐"的内联区

#### 10.6.1 为什么这是"核心"

数据驱动的内联组件有**两个时态**：

1. **初始态**：数据未到达 / 数据为空 / 数据加载中
2. **数据态**：数据到达 / 列表长度变化 / 加载完成

**只要外层容器高度随这两个时态变化，整个父布局链就会抖动**——表格行高、卡片高度、面板高度都会随之伸缩。

**正解**：**外层容器高度锁死**，内部用 `v-show` / `min-height` / 占位元素控制内容显隐。**内容变化只在外层内部发生，外层永远是同一个高度**。

#### 10.6.2 三条落地规则

**规则 1：外层 div 始终渲染（无 `v-if`）**

```vue
<!-- ✅ 正确：div 始终在 DOM 里 -->
<div class="expand-concepts">
  <span class="expand-concepts__label">概念</span>
  <span v-show="loading">加载中…</span>
  <el-tag v-for="c in chips" v-show="!loading" :key="c.code">{{ c.name }}</el-tag>
  <span v-if="!loading && chips.length === 0">—</span>
</div>

<!-- ❌ 错误：div 在数据态切换时进出 DOM -->
<div v-if="chips.length > 0 || loading" class="expand-concepts">...</div>
```

**规则 2：高度锁死用 `height` + `min-height` + `max-height` 三连锁**

```css
.expand-concepts {
  height: 30px;        /* 固定高度（行内 chip 22 + 上下 padding 4×2）*/
  min-height: 30px;    /* 锁下限：chip=0 / 加载中保持 30px → 父容器位置不变 */
  max-height: 30px;    /* 锁上限：chip 数量增加时绝不撑高 */
  flex-wrap: nowrap;   /* 锁单行：chip 数变不影响高度 */
  overflow-x: auto;    /* 超出横滚，不换行 */
  overflow-y: hidden;
  box-sizing: border-box;
}
```

**规则 3：内部子元素按"是否影响外层高度"分类用 `v-show` / `v-if`**

| 子元素类型 | 用法 | 原因 |
|-----------|------|------|
| **占位元素**（label / 骨架屏 / 空态） | `v-show` | DOM 始终在，但可见性受状态控制 |
| **数据列表**（chip / 行 / tag） | 父 `template v-for` + 子元素 `v-show` | DOM 始终在，列表长度变化只影响横向滚动 |
| **条件性元素**（+N tooltip / hint / 错误提示） | `v-if` | 纯条件性元素，无副作用 |

> **核心区分**：
> - **`v-show`**：DOM 始终在，靠 `display:none` 控制可见。**用于"出现/消失"会改变父布局的元素。**
> - **`v-if`**：DOM 在条件为 true 时才创建。**用于"依赖于具体数据值"的元素。**

#### 10.6.3 完整参考实现 · `expand-concepts`（展开行顶部 chips 区）

模板：

```vue
<template>
  <div class="expand-row">
    <!-- 概念 chips 区：div 始终渲染，外部高度锁 30px -->
    <div class="expand-concepts">
      <span class="expand-concepts__label">概念</span>
      <span v-show="chipsLoading && chips.length === 0" class="concept-skeleton-chip">
        <el-icon class="is-loading"><Loading /></el-icon>
        加载中…
      </span>
      <template v-for="c in chips.slice(0, MAX_CHIPS_VISIBLE)" :key="c.index_code">
        <el-tag
          v-show="!chipsLoading || chips.length > 0"
          size="small"
          :type="chipTagType(c)"
          class="concept-chip"
        >{{ c.concept_name }}</el-tag>
      </template>
      <el-tooltip v-if="chips.length > MAX_CHIPS_VISIBLE" :content="...">
        <span class="concept-chip concept-chip--more">+{{ chips.length - MAX_CHIPS_VISIBLE }}</span>
      </el-tooltip>
      <span v-if="chips.some(c => c.stale)" class="expand-concepts__hint">行情源暂不可用</span>
      <span v-if="!chipsLoading && chips.length === 0" class="expand-concepts__empty">—</span>
    </div>

    <div class="expand-charts">...</div>
  </div>
</template>
```

样式：

```css
/* 外层高度锁死是核心 */
.expand-concepts {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 6px;

  height: 30px;        /* ⭐ 三连锁 */
  min-height: 30px;
  max-height: 30px;

  padding: 4px 8px;
  margin-bottom: 6px;   /* 与 .expand-charts 视觉分隔 */
  border-bottom: 1px dashed #e2e8f0;

  overflow-x: auto;     /* chip 多于可见区时横滚 */
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: #cbd5e1 transparent;
  box-sizing: border-box;
}

.expand-concepts__empty {
  font-size: 11px;
  color: #cbd5e1;       /* 弱占位色 */
  white-space: nowrap;
  flex-shrink: 0;
  user-select: none;
}
```

#### 10.6.4 四状态对照表（"外部高度锁死"的最终验证）

| 状态 | 内部可见 | 外层 div 高度 | 父布局影响 |
|------|---------|--------------|----------|
| **未开始加载** | `概念 —`（占位）| **30px** | chart 起点 = 30px（不变） |
| **加载中** | `概念 ⟳ 加载中…` | **30px** | chart 起点 = 30px（不变） |
| **加载完成 chip>0** | `概念 chip1 chip2 ...` | **30px** | chart 起点 = 30px（不变） |
| **加载完成 chip=0** | `概念 —` | **30px** | chart 起点 = 30px（不变） |

> **唯一允许的副作用**：外部容器**首次进入 DOM 时**（即组件 mount / 表格行展开瞬间），高度从 0 变为 30px。
> **不允许的副作用**：数据态切换时（加载中 → 完成；chip=0 → chip>0）任何高度变化。

#### 10.6.5 ⚠️ 反面教材

| 错误 | 后果 |
|------|------|
| `<div v-if="data.length || loading">` | 数据态切换时 div 进出 DOM，外层高度从 0 → 30px → 0 抖动 |
| `height: auto; min-height: 30px` | 缺 `max-height` 锁上限，chip 多时撑高外层 |
| `flex-wrap: wrap` | chip 多时换行，外层高度 +chip行高，破坏锁高 |
| 用 `position: absolute` 把内联区浮起来 | 看似解决了高度问题，但**遮挡父布局其他元素**（如 kline 的 select 框） |
| `transition + max-height` 做展开/折叠动画 | max-height 必须猜一个固定上限值，要么偏小裁切、要么偏大抖动 |

#### 10.6.6 适用范围检查清单

写任何"内联展开型组件"前，问自己：

- [ ] 这个组件的**外层容器 div 是否始终在 DOM**？（无 `v-if`，或者 `v-show`）
- [ ] 这个组件的**高度是否三连锁**（`height` + `min-height` + `max-height`）？
- [ ] **内部子元素**是否按 `v-show`（占位型）/ `v-if`（条件型）正确分类？
- [ ] **数据态切换**时（空 → 加载中 → 有数据 → 数据增减），外层高度是否完全不变？
- [ ] **父布局**（展开行 / 卡片 / 表格行）是否因为这个组件而出现抖动？

只要有一条没满足，**就有可能在数据动态变化时撑爆父布局**——回到本文档 §十.6，重新设计。

---

## 十一、Element Plus 集成备忘

### 11.1 重声明主题变量的"两不原则"

| 不做 | 原因 |
|------|------|
| 不重声明 `--el-font-size-base` | 这是 EP **全局字号源**，改了会影响所有页面 |
| 不在 scoped 顶层 `:deep(.el-button)` | 应限定在自己的 `my-` 标记类下，避免影响其他页面 |

**正确做法**：在自己的 `.my-page :deep(.el-xxx)` 里重声明，本作用域内生效。

### 11.2 sass 固化 px 的覆盖清单

| 组件 | 写死 px | 覆盖写法 |
|------|--------|---------|
| `el-table .cell` | `padding: 0 12px; line-height: 23px` | `:deep(.cell) { padding-inline: calc(12px * var(--d)); line-height: calc(23px * var(--d)); }` |
| `el-table__cell` | `padding-block: 8px` | `:deep(.el-table__cell) { padding-block: calc(8px * var(--d)); }` |
| `el-table__expanded-cell` | `padding: 20px 50px` | 改小且跟密度 |
| `el-table__expand-icon` | `23×23` | `:deep(...) { width: calc(23px * var(--d)); height: calc(23px * var(--d)); }` |
| `el-table .sort-caret` | `border-width: 5px` | `:deep(...) { border-width: calc(5px * var(--d)); }` |
| `el-table__empty-block` | `min-height: 60px` | `:deep(...) { min-height: calc(60px * var(--d)); line-height: calc(60px * var(--d)); }` |
| `el-pagination .btn-prev` 等 | `font-size: 14px` | `:deep(...) { font-size: var(--my-bottom-pagination-fs); }` |
| `el-pagination .el-select` | `width: 128px` | `:deep(...) { width: calc(128px * var(--d)); }` |
| `el-pagination__editor.el-input` | `width: 56px` | `:deep(...) { width: calc(56px * var(--d)); }` |

### 11.3 输入框 / 选择器 / 数字输入框的"像素级一致"

```css
/* 强制覆盖 sass 固化的 padding，让 el-select 和 el-input-number 看起来一致 */
.my-advanced :deep(.el-select__wrapper),
.my-advanced :deep(.el-input-number .el-input__wrapper) {
  min-height: var(--my-top-control-h);
  padding: 4px 11px;                       /* 与 EP default 一致 */
  line-height: calc(var(--my-top-control-h) - 8px);
  box-sizing: border-box;
}
.my-advanced :deep(.el-input-number .el-input__inner) {
  height: calc(var(--my-top-control-h) - 8px);
  line-height: calc(var(--my-top-control-h) - 8px);
}
```

### 11.4 placeholder 字号（必须单独覆盖）

```css
/* sass 默认 14px 写死，不会跟 font-size 走 */
.my-advanced :deep(.el-input__inner::placeholder),
.my-advanced :deep(.el-select__placeholder),
.my-advanced :deep(.el-input-number .el-input__inner::placeholder) {
  font-size: var(--my-top-select-fs);
  color: #a8abb2;
}
```

---

## 十二、密度文件组织清单

```
src/
├── assets/main.css
│   ├── :root { font-size: 14px }               ← 全站基准根字号
│   ├── :root { --el-* 紧凑化变量 }              ← EP 默认值（不覆盖就靠这里）
│   └── :root { --density-* 页面级 token }       ← top-card/gap/title-min 等
│
├── components/PageWrapper.vue
│   └── top-area / middle-area / bottom-area 公共样式
│
└── views/<module>/
    ├── <Module>List.vue                        ← 样板：views/stock-info/StockInfoList.vue
    ├── api.ts
    └── components/                              ← 子组件（Dialog / Drawer / 子表格等）
```

---

## 十三、复制粘贴起点（新页面模板）

```vue
<template>
  <PageWrapper :style="densityStyle" class="my-page">
    <!-- ═══ Title Area ═══ -->
    <template #title>
      <el-icon class="mr-1"><SomeIcon /></el-icon>
      我的页面
      <span class="page-title-text">标题</span>

      <button class="density-toggle" :class="{ active: showPanel }" @click="showPanel = !showPanel">
        <el-icon><Setting /></el-icon>
      </button>

      <transition name="density-inline">
        <div v-if="showPanel" class="density-inline">
          <span class="density-inline__label">⚙️ 页面设置</span>
          <span class="density-inline__divider"></span>
          <div class="density-inline__group">
            <span>页面</span>
            <el-slider v-model="pageDensity" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ pageDensity.toFixed(2) }}</span>
          </div>
          <div class="density-inline__group">
            <span>顶部</span>
            <el-slider v-model="topDensityProxy" :min="0.6" :max="1.5" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ topDensityProxy.toFixed(2) }}</span>
          </div>
          <div class="density-inline__group">
            <span>表格</span>
            <el-slider v-model="middleDensityProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ middleDensityProxy.toFixed(2) }}</span>
          </div>
          <div class="density-inline__group">
            <span>分页</span>
            <el-slider v-model="bottomDensityProxy" :min="0.7" :max="1.4" :step="0.05" :show-tooltip="false" />
            <span class="density-inline__value">{{ bottomDensityProxy.toFixed(2) }}</span>
          </div>
          <el-button size="small" :disabled="pageDensity === 1 && allSynced" @click="syncAreasToPage">区域跟随</el-button>
          <el-button size="small" type="primary" :disabled="pageDensity === 1 && allSynced" @click="resetDensities">全部还原</el-button>
        </div>
      </transition>
    </template>

    <!-- ═══ Top Area ═══ -->
    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-search">
          <el-input v-model="q" placeholder="搜索..." clearable :prefix-icon="Search" @input="onSearch" />
          <el-button :type="showAdv ? 'primary' : 'default'" :text="!showAdv" @click="showAdv = !showAdv">高级筛选</el-button>
          <el-button v-if="hasActive" type="danger" link @click="resetFilters">重置</el-button>
        </div>
        <div class="toolbar-actions">
          <el-button type="primary">主操作</el-button>
        </div>
      </div>
      <div class="advanced-wrapper" :class="{ open: showAdv }">
        <div class="advanced-filters">
          <el-select v-model="filters.x">...</el-select>
          <el-input-number v-model="filters.y">...</el-input-number>
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area ═══ -->
    <el-table v-loading="loading" class="my-table" :data="rows">...</el-table>

    <!-- ═══ Bottom Area ═══ -->
    <template #bottom>
      <div class="bottom-area-inner">
        <el-pagination class="my-pagination" v-model:current-page="page" v-model:page-size="size" :total="total" small background />
      </div>
    </template>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Search, Setting } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'

// ── 密度锚点（粘贴即可，按需改 DENSITY_KEY 与前缀） ──
const DENSITY_KEY = 'my-density'
const showPanel = ref(false)
const pageDensity = ref(1)
const topDensity = ref<number | null>(null)
const middleDensity = ref<number | null>(null)
const bottomDensity = ref<number | null>(null)
// ... loadDensity / clamp / densityStyle / watcher / resetDensities / syncAreasToPage / Proxy / colW ...

// ── 业务逻辑 ──
const q = ref('')
const filters = ref<any>({})
const showAdv = ref(false)
const rows = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const loading = ref(false)

async function load() { loading.value = true; /* ... */; loading.value = false }
onMounted(load)
</script>

<style scoped>
.my-page {
  display: flex;
  flex-direction: column;
  height: 100%; min-height: 0;

  --my-page-density: 1;
  --my-top-density:    calc(var(--my-page-density));
  --my-middle-density: calc(var(--my-page-density));
  --my-bottom-density: calc(var(--my-page-density));

  --my-top-gap:                calc(0.5rem * var(--my-top-density));
  --my-top-button-h:           calc(2rem * var(--my-top-density));
  --my-top-button-fs:          calc(0.95rem * var(--my-top-density));
  --my-top-button-px:          calc(0.75rem * var(--my-top-density));
  --my-top-icon-fs:            calc(0.95rem * var(--my-top-density));
  --my-top-icon-mr:            calc(0.25rem * var(--my-top-density));
  --my-top-filter-py:          calc(0.55rem * var(--my-top-density));
  --my-top-filter-px:          calc(0.85rem * var(--my-top-density));
  --my-top-control-h:          calc(2rem * var(--my-top-density));
  --my-top-input-fs:           calc(0.95rem * var(--my-top-density));
  --my-top-input-w:            calc(220px * var(--my-top-density));
  --my-top-select-fs:          calc(0.95rem * var(--my-top-density));
  --my-top-select-w:           calc(130px * var(--my-top-density));
  --my-top-input-num-fs:       calc(0.95rem * var(--my-top-density));
  --my-top-input-num-w:        calc(130px * var(--my-top-density));

  --my-middle-row-h:           calc(2.5rem * var(--my-middle-density));
  --my-middle-cell-pad-y:      calc(0.375rem * var(--my-middle-density));
  --my-middle-cell-pad-x:      calc(0.5rem * var(--my-middle-density));
  --my-middle-table-fs:        calc(0.857rem * var(--my-middle-density));
  --my-middle-sel-fs:          calc(0.857rem * var(--my-middle-density));
  --my-middle-sel-py:          calc(0.357rem * var(--my-middle-density));
  --my-middle-sel-px:          calc(0.625rem * var(--my-middle-density));
  --my-middle-sel-gap:         calc(0.357rem * var(--my-middle-density));

  --my-bottom-pagination-fs:    calc(0.857rem * var(--my-bottom-density));
  --my-bottom-pagination-btn-w: calc(1.857rem * var(--my-bottom-density));
  --my-bottom-pagination-btn-h: calc(1.857rem * var(--my-bottom-density));
  --my-bottom-pagination-pt:    calc(0.5rem * var(--my-bottom-density));
}

/* ── 密度 toggle 按钮 + 内联面板 + 横向滚动（直接复用本文档 §10）── */
/* ... 复制本文档 §10.2 ... */

/* ── 自适应 .top-area__header / .top-area__title ── */
.my-page :deep(.top-area__header) {
  min-height: var(--density-title-min);
  height: auto;
}
.my-page :deep(.top-area__title) {
  min-width: 0;
}

/* ── toolbar-row 风格（直接复用本文档 §7.2）── */
/* ... */

/* ── 高级筛选 grid-rows 动画（直接复用本文档 §7.3）── */
/* ... */

/* ── 选中条 / 表格 / 分页器（直接复用本文档 §8 / §9）── */
/* ... */
</style>
```

> **复制起点后必做**：把 `my-` 前缀改成你页面的英文字母缩写（如 `--kline-*`），
> `DENSITY_KEY` 改成 `'模块-density'`。其它全部照搬。

---

## 十四、Antipattern 速查

| 错误 | 现象 | 正确做法 |
|------|------|---------|
| 写 `padding: 12px` | 改 density 不响应 | `padding: calc(12px * var(--d))` |
| 写 `font-size: 14px` | 缩放失效 | `font-size: calc(0.857rem * var(--d))` |
| 用 `--el-font-size-base` 全局改字号 | 整个站点联动 | 在自己的 `.my-page` 里重声明需要的 `--el-*-font-size` |
| 用 `<transition>` + `v-if` 折叠高级筛选 | 中部表格逐帧抖动 | grid-rows 动画（永远 DOM 在） |
| density-inline 用 `flex-shrink: 0` | 撑爆 main-container | 让外层可缩、内层不可缩 |
| density-inline 用 `max-width: calc(100vw - 24rem)` | 视区估算不准 | `flex: 1 1 0` + `min-width: 0` 继承父宽 |
| `top-area__header` 硬锁 `height: 32px` | density-inline 40px 被裁 | `min-height: 32px; height: auto` 自适应 |
| 表格列宽写死像素 | density 拖不动表格宽度 | 列宽用 `colW(px)` 函数缩放 |
| 中部内容 `<div height: 600px>` | 表格被压扁、底部留白 | 让 flex 自动撑满 |
| 顶部搜索框有多个 `<el-input>` | UX 混乱 | 统一一个主搜索 + 高级筛选 |
| **内联展开区用 `<div v-if="data">`** | **数据态切换时外层高度从 0→N 抖动** | **外层 div 始终渲染 + 三连锁高度锁死（详见 §十.6）** |
| **内联区只设 `min-height`，缺 `max-height`** | **数据多时撑高外层，破坏锁高** | **`height` + `min-height` + `max-height` 三连锁** |

---

## 十五、变更检查表（PR Review Checklist）

新建/修改带密度面板的页面时，确认以下事项：

### 骨架层
- [ ] 用了 `PageWrapper` 而不是裸 `<div>`
- [ ] `:style="densityStyle"` 绑在 PageWrapper 上
- [ ] 自定义 class（如 `class="my-page"`）挂在 PageWrapper 上
- [ ] `#title` / `#toolbar` / 默认插槽 / `#bottom` 插槽对应四个区域

### JS 层
- [ ] 锚点状态用 `ref` 保存
- [ ] `densityStyle` computed 正确注入 4 个变量（区域为 null 时不注入）
- [ ] watch 持久化到 localStorage（key 加页面前缀）
- [ ] Proxy computed 三件套（topDensityProxy / middleDensityProxy / bottomDensityProxy）
- [ ] `colW(px)` 函数用于表格列宽
- [ ] `allSynced` 用于 UI 状态提示

### CSS 层（变量）
- [ ] 顶层声明 4 层 `--my-{page|top|middle|bottom}-density`
- [ ] 每个区域的派生 token 都用 `calc(rem × var(--my-xxx-density))`
- [ ] 三类 EP 主题变量重声明（表格 / 分页器）作用域限定在 `.my-page :deep(.el-*)`

### CSS 层（结构）
- [ ] `density-toggle` 锁定 1.625rem 固定尺寸
- [ ] `density-inline` 用横向滚动模式（`flex: 1 1 0; min-width: 0; overflow-x: auto`）
- [ ] `density-inline__group` `flex-shrink: 0`
- [ ] `.top-area__header` 改为自适应（页面级有 density-inline 时）
- [ ] `.top-area__title` 加 `min-width: 0`
- [ ] toolbar-row / toolbar-search / toolbar-actions 三件套
- [ ] advanced-wrapper 用 grid-rows 动画，不用 transition+v-if
- [ ] 表格 .my-table 五条不变式齐全
- [ ] 分页器 .my-pagination 内部 px 覆盖齐全
- [ ] **内联展开型组件（chips / 摘要 / 子表 / 内联 toolbar）**：外层 div 始终渲染，无 `v-if`
- [ ] **内联展开型组件**：高度锁死用 `height` + `min-height` + `max-height` 三连锁（详见 §十.6）

### EP 集成
- [ ] el-select / el-input-number 像素级一致
- [ ] placeholder 字号单独覆盖
- [ ] 表格内部 cell 各种 px 覆盖齐全（cell / expanded-cell / expand-icon / sort-caret / empty-block）
- [ ] 分页器 btn-prev / btn-next / pager / editor / select 宽度都覆盖

### 其他
- [ ] `page-title-text { white-space: nowrap }`
- [ ] 所有滚动条美化（4px thin + WebKit 自定义）
- [ ] 没有用 `--el-font-size-base`
- [ ] 没有用 viewport 估算（`calc(100vw - X)`）
- [ ] 没有 `transition + v-if + max-height` 折叠高级筛选

---

## 十六、相关文档索引

| 文档 | 何时读 |
|------|--------|
| `docs/适配性/01-rem全局密度方案.md` | 改全站根字号、调 EP 紧凑化时 |
| `docs/layout-guide.md` | 改 Shell / PageWrapper / 路由时 |
| `docs/page-development-guide.md`（本文） | **写新页面 / 调现有页面密度时** |
| `src/views/stock-info/StockInfoList.vue` | **所有"标准实现"的活体参照** |

---

## 附录 A · 完整文件位置映射

| 本文 §       | 活体参照位置（StockInfoList.vue）         |
|--------------|------------------------------------------|
| §四 JS 模板  | 行 385–504（`DensityShape` / `densityStyle` / Proxy） |
| §五.1 顶层声明 | 行 805–853（`.stock-info-page` 变量声明） |
| §六 Title    | 行 1043–1038（`.page-title-text`）        |
| §六.2 ⚙️ 按钮 + 面板 | 行 858–923（`.density-toggle` / `.density-inline`） |
| §六.3 标题防溢出 | 行 1036–1038（`.page-title-text`）        |
| §七 Top      | 行 1043–1189（`.toolbar-row` / `.advanced-wrapper`） |
| §八 Middle   | 行 1194–1360（`.selection-bar` / `.sil-table`） |
| §九 Bottom   | 行 1362–1435（`.bottom-area-inner` / `.sil-pagination`） |
| §十 内联面板  | 行 893–1033（`.density-inline` 全套）     |
| §十.3 父级覆盖 | 行 925–941（`.top-area__header` / `.top-area__title`） |
| §十.6 外部高度锁死 | `src/views/stock-info/components/StockExpandRow.vue` `.expand-concepts` 全套 |
| §十一 EP 集成 | 行 1207–1220 / 1372–1435（主题变量重声明） |
</content>
</invoke>