# 树形选择器开发规范

> 适用范围：页面左侧"分组 → 子分组 → 条目"三层的导航 / 选择树，点击条目切换右侧内容。
> 当前使用方：采集管理 `views/collect-manage/components/CatalogTree.vue`（采集接口目录）。
> 页面级容器（PageWrapper）与左右两栏布局见 `layout-guide.md` / `page-development-guide.md`。
>
> 参考实现：`frontend/src/views/collect-manage/components/CatalogTree.vue`

---

## 一、原则

1. **三层，层层可辨**：每层有各自的背景色 + 边框，由深到浅；字号逐层递减；逐层缩进。
2. **高度统一**：三层行高一致（26px），层级靠背景 / 边框 / 字号 / 缩进区分，不靠高度。
3. **条目只显示名称**：描述、默认参数等放 hover tooltip，不在树里常驻，保证信息密度。
4. **独立滚动**：树自身纵向滚动，与右侧内容区互不带动。

---

## 二、结构

```
aside.catalog-tree（220px，#f8fafc 底，内边距 12px 8px，overflow-y:auto）
│
├─ .facet-header        第一层：▾ 图标 分组名                 [12] [3]   ← 数量徽标靠右
│   └─ .sub-facet-list（左缩进 8px）
│       ├─ .sub-facet-label   第二层：▾ 子分组名                    5   ← 数量靠右
│       │   ├─ .task-btn      第三层：条目名称（再缩进 8px）
│       │   └─ .task-btn
│       └─ .sub-facet-label …
└─ .facet-header …
```

---

## 三、三层规范

| 项 | 第一层（分组 `.facet-header`） | 第二层（子分组 `.sub-facet-label`） | 第三层（条目 `.task-btn`） |
|---|---|---|---|
| 高度 | 26px | 26px | 26px（`line-height: 24px`，含上下 1px 边框） |
| 字号 / 字重 | 14px / 名称加粗 | 13px / 600 | 12px / 常规 |
| 文字色 | `#1e293b` | `#475569` | `#475569` |
| 背景 | `#e2e8f0` | `#f1f5f9` | `#fff` |
| 边框 | `1px #94a3b8` + 左侧 `3px #3b82f6` 主色条 | `1px #cbd5e1` | `1px #e2e8f0` |
| 圆角 | 4px | 4px | 4px |
| 左缩进 | 0 | 8px | 16px（子分组内再缩进 8px） |
| 内边距 | `0 8px` | `0 8px` | `0 8px` |
| 右侧信息 | 数量徽标（已实现 / 待实现） | 条目数（12px 灰字） | 无 |
| hover | 背景 `#cbd5e1` | 背景 `#e2e8f0` | 背景 `#eff6ff`、边框 `#bfdbfe`、文字 `#1e40af` |

间距：分组之间 10px，子分组之间 4px，条目之间 2px；子分组列表距分组头 4px。

### 3.1 条目状态

| 状态 | 样式 |
|---|---|
| 选中 `.active` | 背景 `#dbeafe`、边框 `#60a5fa`、文字 `#1d4ed8` 加粗 |
| 待实现 `.planned` | 文字 `#94a3b8` 斜体（仍可点击查看） |
| 名称过长 | 单行省略（`.task-btn-label`：`overflow:hidden; text-overflow:ellipsis; white-space:nowrap`） |

> 选中态用浅色背景 + 主色边框，不要用实心主色底白字——三层都有背景色时，实心块会显得突兀。

### 3.2 折叠

- 第一层、第二层都可折叠，左侧 `ArrowDown` 箭头，折叠时 `rotate(-90deg)`，`transition: transform 0.15s`。
- 折叠 key：第一层用 `facet`，第二层用 `facet/subKey`。
- 折叠状态存 `localStorage`（key 带页面前缀，如 `collect-manage:collapsed`），刷新后保留。
- 用 `v-show` 折叠，不用 `v-if`（避免展开时重新创建 tooltip 等子组件）。
- 可点击的头部加 `role="button"` 与 `:aria-expanded`。

### 3.3 Tooltip

- 条目 hover 显示：描述 + 默认参数 + 其他补充信息，`placement="right"`、`:show-after="300"`。
- 多行内容用 `\n` 拼接，`popper-class` 指定专用类，并用 `:global()` 设置 `white-space: pre-line`、`max-width: 340px`。

---

## 四、数据与用法

```vue
<CatalogTree v-model="activeTaskType" :catalog="catalog" :loading="catalogLoading" />
```

| 名称 | 类型 | 说明 |
|---|---|---|
| `v-model` | `string` | 当前选中条目的 key（`task_type`） |
| `catalog` | `FacetGroup[]` | 第一层数组；`sub_groups: Record<subKey, TaskDef[]>` 为第二 / 三层 |
| `loading` | `boolean` | 加载中显示"加载中..."；空数组显示"无采集任务" |

- 第二层显示名查 `SUB_FACET_LABELS[subKey]`，没有则显示 key。
- 数量统计（`countReady` / `countPlanned`）与标签表放在 composable 模块级导出，树组件直接 import，不经父组件传入。

---

## 五、布局：左右独立滚动

```css
/* 父级：占满剩余高度，自身不滚动 */
.layout-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
  overflow: hidden;
}

/* 树：固定宽度，自身滚动 */
.catalog-tree {
  width: 220px;
  flex-shrink: 0;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
}
```

- 右侧内容区同样 `flex: 1; min-height: 0`，其内部表格用 `height="100%"` 自己滚动。
- **不要**给树写 `max-height: 80vh` 之类的视口估算值。

---

## 六、⚠️ 坑：`el-badge` 数量气泡不居中

第一层的数量徽标用不带默认插槽的 `el-badge`，此时：

1. EP **不会**给气泡加 `is-fixed`（只有带默认插槽才加），所以覆盖 `.is-fixed` 无效；
2. 气泡是 `<sup>` 元素，**Tailwind preflight** 对 `sup` 设了
   `position: relative; top: -0.5em; line-height: 0`，气泡会整体上移半行。

正确写法：徽标包一层推到右侧，并重置气泡的 `sup` 样式：

```vue
<span class="facet-badges">
  <el-badge :value="ready" type="success" />
  <el-badge :value="planned" type="info" />
</span>
```

```css
.facet-badges {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;          /* 靠右 */
}
.facet-header :deep(.el-badge) {
  display: flex;
  align-items: center;
  line-height: 1;
}
.facet-header :deep(.el-badge__content) {
  position: static;           /* 抵消 preflight 的 relative + top:-0.5em */
  top: auto;
  line-height: 1;
  vertical-align: middle;
}
```

> 站内其他"无默认插槽的 `el-badge`"（如「高级筛选」按钮上的计数）同样受 preflight 影响，遇到上偏按此处理。

---

## 七、检查清单

- [ ] 三层行高都是 26px，字号 14 / 13 / 12 递减
- [ ] 三层背景 `#e2e8f0` / `#f1f5f9` / `#fff`，边框 `#94a3b8` / `#cbd5e1` / `#e2e8f0`，各不相同
- [ ] 第一层左侧有 3px 主色条；逐层缩进 8px
- [ ] 条目只显示名称，描述等在 tooltip 中
- [ ] 选中态为浅蓝底 + 主色边框，不是实心主色块
- [ ] 第一层数量徽标靠右且垂直居中（已重置 `sup` 的 preflight 样式）
- [ ] 折叠状态持久化到 localStorage，key 带页面前缀
- [ ] 树宽 220px、自身 `overflow-y: auto`，滚动右侧内容不会带动树
