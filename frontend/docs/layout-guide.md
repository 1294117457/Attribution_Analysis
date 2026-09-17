# 前端页面布局开发规范

> 本文档定义了项目的整体布局结构与页面开发规范，所有新页面必须遵循此规范。

## 一、技术栈

- **框架**：Vue 3 + TypeScript（Composition API `<script setup>`）
- **UI 组件库**：Element Plus
- **CSS**：Tailwind CSS v4 + scoped CSS 变量
- **路由**：Vue Router，所有业务页面挂载在 `/home` 下，使用 `Shell.vue` 布局

## 二、整体布局结构（Shell）

页面整体采用三区域布局，由 `src/layouts/Shell.vue` 控制：

```
┌─────────────────────────────────────────────────┐
│                   TopBar（导航栏）                 │  高度: var(--topbar-height) = 3rem
├────────┬────────────────────────────────────────┤
│        │                                        │
│LeftBar │           MainContainer                │
│(菜单栏) │             (主区域)                    │
│        │                                        │
│ 宽度:   │   flex: 1, 自由展开填满剩余空间          │
│ 展开    │   padding: var(--page-padding) = 16px  │
│ 220px  │                                        │
│ 折叠    │                                        │
│ 56px   │                                        │
└────────┴────────────────────────────────────────┘
```

### 2.1 TopBar（`src/layouts/components/TopBar.vue`）

- 顶部导航栏，固定高度 `3rem`
- z-index: 100，始终位于最上层

### 2.2 LeftBar（`src/layouts/components/LeftBar.vue`）— 悬浮岛

- 左侧菜单栏，深色背景 `#1d2128`
- 使用 Element Plus `el-menu` 组件
- z-index: 50

**悬浮岛效果**：展开时四周有间距、圆角 16px、阴影投影，折叠时贴边无阴影。

**双层结构**（性能优化）：

```
.leftbar-slot（外层）         .leftbar（内层）
├─ 控制 flex 布局占位宽度       ├─ 深色条本体
├─ width + padding 带 transition  ├─ width + border-radius + box-shadow 带 transition
└─ 展开 232px → 折叠 56px       └─ 展开：圆角+阴影 → 折叠：方角+无阴影
```

- **外层 `.leftbar-slot`**：`width` 和 `padding` 带 `0.3s` transition，控制 flex 布局中的占位空间平滑过渡
- **内层 `.leftbar`**：`width`、`border-radius`、`box-shadow` 带 `0.3s` transition，控制视觉效果平滑过渡

**重排防护**（`contain: layout style`）：

侧边栏宽度变化会导致右侧 `.shell-content` 宽度逐帧变化。如果不做处理，表格等复杂子元素会**每帧重排**（几百个 DOM 节点），造成卡顿。

解决方案：在 `Shell.vue` 的 `.shell-content` 上设置 `contain: layout style`，告诉浏览器该容器内部布局与外部隔离——侧边栏动画期间，内部的表格、卡片等**不会逐帧重排**，动画结束后一次性更新。

```
左侧 width 变化 → flex 重算（2个子项，轻量）→ .shell-content 外框变宽
                                               ↓
                                    contain: layout style
                                               ↓
                                    内部表格/卡片 不重排 ✅
```

### 2.3 MainContainer（`src/layouts/components/MainContainer.vue`）

- 主内容区容器，承载 `<router-view>`
- `flex: 1` + `min-width: 0`，自动填满侧边栏右侧全部空间
- `contain: layout style`，隔离内部布局，防止侧边栏动画连锁触发表格重排
- 内边距由 CSS 变量 `--page-padding` 控制（默认 16px）
- 路由切换带 fade 过渡动画

### 关键 CSS 变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `--topbar-height` | `3rem` | 导航栏高度 |
| `--sidebar-width` | `220px` | 菜单栏展开宽度 |
| `--sidebar-collapsed` | `56px` | 菜单栏折叠宽度 |
| `--page-padding` | `16px` | 主区域内边距 |
| `--color-admin-bg` | `#f5f7fb` | 页面背景色 |
| `--color-admin-border` | `#e5e7eb` | 分隔线颜色 |

## 三、页面内部结构（PageWrapper）

每个路由页面必须使用 `src/components/PageWrapper.vue` 组件包裹，它提供标准化的三区域垂直布局：

```
┌─────────────────────────────────────────┐
│  el-card.page-wrapper (圆角 12px)        │
│ ┌─────────────────────────────────────┐ │
│ │  top-area（固定，不滚动）              │ │
│ │  ├── header 行: #title + #actions   │ │
│ │  └── toolbar 行: #toolbar（可选）    │ │
│ ├─────────────────────────────────────┤ │
│ │  middle-area（flex:1，自动撑满）      │ │
│ │  默认插槽，放置页面主要内容            │ │
│ │  当无 bottom 时自动延伸至底部          │ │
│ ├─────────────────────────────────────┤ │
│ │  bottom-area（可选，固定在底部）       │ │
│ │  #bottom 插槽，如分页组件             │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 3.1 插槽说明

| 插槽名 | 必需 | 说明 |
|--------|------|------|
| `#title` | 是 | 页面标题，显示在 top-area 第一行左侧 |
| `#actions` | 否 | 标题行右侧的操作按钮（与 title 同行） |
| `#toolbar` | 否 | top-area 第二行，完整宽度，放置搜索和操作按钮 |
| 默认插槽 | 是 | middle-area 内容（表格、卡片等主体内容） |
| `#bottom` | 否 | 底部固定区域（分页等），不传时 middle-area 自动铺满 |

### 3.2 top-area 标准布局

top-area 分为两行：

**第一行（header）**：
- 左侧：页面标题（`#title`），如 "📋 股票信息"
- 右侧：页面级操作按钮（`#actions`），一般留空，标题行保持简洁

**第二行（toolbar）**：通过 `#toolbar` 插槽实现，内部标准结构如下：

```
┌──────────────────────────────────────────────────┐
│ [主搜索框] [高级筛选▼] [重置]     [操作B] [操作A]   │  toolbar-row
├──────────────────────────────────────────────────┤
│ [行业▼] [市场▼] [交易所▼] [沪深港通▼] [状态▼]       │  advanced-filters（折叠/展开）
└──────────────────────────────────────────────────┘
```

- **左侧**（`.toolbar-search`）：主搜索输入框 + "高级筛选" 折叠/展开按钮 + 重置按钮
- **右侧**（`.toolbar-actions`）：操作按钮从右到左排列
- **高级筛选区**（`.advanced-filters`）：默认隐藏，点击"高级筛选"按钮展开，使用 `grid-template-rows` 动画（见下方性能说明）

#### 高级筛选动画（grid-template-rows）

使用 CSS Grid 的 `grid-template-rows: 0fr → 1fr` 动画替代 `<transition>` + `v-if` + `max-height`：

```html
<!-- 不用 <transition> 和 v-if，用 class 切换 -->
<div class="advanced-wrapper" :class="{ open: showAdvanced }">
  <div class="advanced-filters">
    <!-- 筛选控件 -->
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
}
```

**为什么不用 `max-height` / `<transition>`**：
- `max-height` 每帧触发 layout 重排，下方表格会逐帧抖动
- `v-if` 每次展开/收起要创建/销毁 DOM，和 CSS transition 抢帧
- `grid-template-rows` 是浏览器原生优化过的动画属性，能自适应内容高度，不需要硬编码数值

**为什么不用 `contain`**（与侧边栏的区别）：
- 筛选区和表格在同一个 flex 列中，表格必须实时响应筛选区高度变化
- 但这里重排范围很小（只有 wrapper 高度 + 表格高度），不会连锁到表格列宽和单元格

#### 搜索规范

1. 每个页面只保留 **一个主搜索框**，支持最常用的模糊搜索
2. 其他筛选条件归入 **高级筛选**，默认折叠
3. 高级筛选按钮在有激活的高级条件时，显示 `el-badge` 数字提示
4. 提供"重置"按钮，一键清空所有筛选条件

### 3.3 middle-area

- `flex: 1`，自动撑满 top-area 和 bottom-area 之间的空间
- `overflow: auto`，内容超出时自动出现滚动条
- 放置页面主要内容：表格、卡片列表、图表等
- 当无 `#bottom` 插槽时，自动延伸到页面底部

### 3.4 bottom-area

- 可选区域，通过 `#bottom` 插槽传入
- 固定在底部，不随内容滚动
- 上方有 `1px` 分隔线
- 典型用途：分页组件（`el-pagination`）
- **不需要分页的页面不传此插槽**，middle-area 会自动铺满

## 四、页面文件结构规范

以 `stock-info` 模块为例：

```
views/stock-info/
├── StockInfoList.vue              ← 主页面（路由入口，使用 PageWrapper）
├── api.ts                         ← API 接口定义 + 类型导出
└── components/                    ← 页面子组件
    ├── StockDetailDrawer.vue      ← 详情抽屉
    ├── AddToPoolDialog.vue        ← 加入操作池弹窗
    └── KLineDrawerTab.vue         ← K线Tab子组件
```

### 4.1 命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 主页面 | `[模块名]List.vue` / `[模块名]Detail.vue` | `StockInfoList.vue` |
| 子组件 | 功能描述性命名 | `StockDetailDrawer.vue` |
| API 文件 | `api.ts` | `api.ts` |
| 目录 | kebab-case | `stock-info/` |

### 4.2 组件拆分原则

- **弹窗（Dialog）**：独立为子组件，使用 `v-model` 控制显示
- **抽屉（Drawer）**：独立为子组件，使用 `v-model` 控制显示
- **主页面**：只保留页面级状态管理和编排逻辑，UI 结构保持在 PageWrapper 三区域内
- **子组件通信**：`props` 传入数据，`emit` 回传事件

## 五、完整页面模板

新建页面时复制此模板：

```vue
<template>
  <PageWrapper>
    <!-- ═══ Top Area ═══ -->
    <template #title>📋 页面标题</template>

    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-search">
          <el-input
            v-model="searchQuery"
            placeholder="搜索..."
            clearable
            style="width: 260px"
            :prefix-icon="Search"
            @input="onSearchInput"
          />
          <el-button
            :type="showAdvanced ? 'primary' : 'default'"
            :text="!showAdvanced"
            @click="showAdvanced = !showAdvanced"
          >
            <el-icon class="mr-1">
              <ArrowDown v-if="!showAdvanced" />
              <ArrowUp v-else />
            </el-icon>
            高级筛选
          </el-button>
        </div>
        <div class="toolbar-actions">
          <!-- 操作按钮从右到左排列 -->
          <el-button type="primary">主操作</el-button>
        </div>
      </div>

      <!-- grid-rows 展开动画，不用 <transition> + v-if -->
      <div class="advanced-wrapper" :class="{ open: showAdvanced }">
        <div class="advanced-filters">
          <!-- 高级筛选条件 -->
        </div>
      </div>
    </template>

    <!-- ═══ Middle Area ═══ -->
    <!-- 主要内容：表格 / 卡片列表 / 图表等 -->

    <!-- ═══ Bottom Area（可选） ═══ -->
    <template #bottom>
      <el-row justify="end">
        <el-pagination ... />
      </el-row>
    </template>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Search, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'

const showAdvanced = ref(false)
const searchQuery = ref('')

function onSearchInput() {
  // 防抖搜索逻辑
}
</script>

<style scoped>
.toolbar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-search {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 高级筛选：grid-rows 展开动画 */
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  background: var(--color-admin-bg);
  border-radius: 8px;
  transition: padding 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.advanced-wrapper.open > .advanced-filters {
  padding: 12px 16px;
}
</style>
```

## 六、关键文件索引

| 文件 | 说明 |
|------|------|
| `src/layouts/Shell.vue` | 整体三区域布局（TopBar + LeftBar + MainContainer） |
| `src/layouts/components/TopBar.vue` | 顶部导航栏 |
| `src/layouts/components/LeftBar.vue` | 左侧菜单栏（支持折叠） |
| `src/layouts/components/MainContainer.vue` | 主内容区容器（承载 router-view） |
| `src/components/PageWrapper.vue` | 页面标准容器（top/middle/bottom 三区域） |
| `src/assets/main.css` | 全局样式 + CSS 变量定义 |
| `src/router/home.ts` | 业务路由定义 |
| `src/views/stock-info/StockInfoList.vue` | **标准参考页面**（完整示范） |
