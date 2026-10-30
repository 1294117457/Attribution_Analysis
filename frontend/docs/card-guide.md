# 信息卡片开发规范

> 适用范围：页面中"标题 + 一块数据"的信息卡片——表格卡片、K 线 / 图表卡片、空状态卡片。
> 当前使用方：`data-board-tabs/*` 面板（详情抽屉数据面 / 数据看板）、股票列表展开行的日 K / 分 K。
> 页面级容器（PageWrapper）不属于这里，见 `page-development-guide.md`。
>
> 组件：`frontend/src/components/InfoCard.vue`
> 设计变量：`frontend/src/assets/main.css` 中的「信息卡片 InfoCard 设计变量」

---

## 一、唯一原则

**所有信息卡片都用 `InfoCard`**，卡片顶部只有一种样式（`.info-card__header`）。

- 不再使用 `el-card` + `#header`，也不再在组件里自己画 `chart-toolbar` 之类的标题条。
- 标题栏里有控件（下拉框、状态 tag）时，用 `InfoCard` 的 `#tools` 插槽放进去，而不是另起一条工具栏。

---

## 二、结构

```
┌──────────────────────────────────────────┐  ← 1px #e2e8f0 边框，圆角 8px，白底，无阴影
│ 标题 [tools…]                      extra │  ← 标题栏：35px，#e2e8f0 底，左 12 / 右 8
├──────────────────────────────────────────┤  ← 1px #cbd5e1
│ 内容区（默认插槽）                       │  ← 内边距 6px 8px；含 el-table 时为 0
└──────────────────────────────────────────┘
```

| 部分 | 规范 |
|---|---|
| 卡片 | 白底，`1px #e2e8f0` 边框，圆角 8px，**无阴影**，`overflow: hidden` |
| 标题栏 | 高 35px（含底边框），`padding: 0 8px 0 12px`，背景 `#e2e8f0`，底边 `1px #cbd5e1`，单行不换行 |
| 标题 | 13px / 700，`#1e293b`，最左；过长省略；可在标题后带一个关键数值（如最新价，等宽字体） |
| tools | 紧跟标题，`gap: 4px`；下拉框统一压到 22px 高、11px 字 |
| extra | 推到**最右侧**，11px 常规字重、`#64748b`；放条数 / 根数 / 更新时间 / 状态 tag |
| 内容区 | 内边距 `6px 8px`；**含 `el-table` 时自动为 0**，表格撑满卡片宽度（单元格自带内边距） |
| 卡片间距 | 由容器决定：详情抽屉内 6px（`--info-card-gap`），数据看板沿用面板网格间距 |

---

## 三、用法

### 3.1 Props / 插槽

| 名称 | 类型 | 说明 |
|---|---|---|
| `title` | `string` | 纯文本标题；标题需要富内容时改用 `#title` |
| `#title` | 插槽 | 自定义标题（如 `日 K <b>12.34</b>`），覆盖 `title` |
| `#tools` | 插槽 | 标题后的控件：`el-select size="small"`、状态 `el-tag` 等 |
| `#extra` | 插槽 | 标题栏最右侧的附加信息；不传则不渲染 |
| 默认插槽 | 插槽 | 内容区 |

### 3.2 表格卡片

```vue
<InfoCard title="复权因子">
  <template #extra><el-tag size="small" type="info">{{ list.length }} 条</el-tag></template>
  <div v-loading="loading">
    <el-table :data="list" size="small" stripe max-height="200">...</el-table>
  </div>
</InfoCard>
```

- 内容区自动无内边距，**不要**再给表格包裹层加 padding。
- `el-table` 用 `size="small"`、`stripe`；限高用 `max-height`，不在外面套固定高度的滚动容器。
- 条数放 `#extra`，标题里不再重复写数量（如 `日频估值` + extra `最新 30 天`，而不是 `日频估值（最新 30 天）`）。
- `title` 是普通属性，**不能**写 `{{ }}` 插值；动态内容放 `#extra` 或 `#title`。

### 3.3 带控件的卡片（K 线等）

```vue
<InfoCard>
  <template #title>分 K <b>{{ last }}</b></template>
  <template #tools>
    <el-select v-model="interval" size="small" style="width: 68px">...</el-select>
    <el-tag size="small" type="danger" effect="plain">实时 · 15 秒</el-tag>
  </template>
  <template #extra>{{ klines.length }} 根</template>
  <MiniKlineChart hide-header :klines="klines" :height="145" />
</InfoCard>
```

- K 线统一用 `MiniKlineChart` 并传 `hide-header`：标题、加载中、根数都放进卡片标题栏，图表区只画图。
- `MiniKlineChart` 以 `compact` 模式使用 `CandleChart`：价格 / VOL / 副图刻度画在图内，左右各留 8px；无副图时主图与成交量占满高度。
- 日 K 直接用 `DailyKlineChart`，它**本身就是一张 InfoCard**（含周期 / 主图指标 / 副图选择），直接放进布局即可：

  | Prop | 默认 | 说明 |
  |---|---|---|
  | `symbol` | 必填 | 股票代码 |
  | `height` | `145` | 无副图时图高 |
  | `subHeight` | `35` | 开启副图时额外增加的高度 |
  | `sub` | `true` | 是否提供副图选择 |

### 3.4 空状态 / 占位卡片

- 内容区保持默认内边距，内部用 `el-empty`，说明文字简短；"待实现"等状态放 `#extra` 的 `el-tag`。

---

## 四、设计变量（`main.css` `:root`）

| 变量 | 值 | 用途 |
|---|---|---|
| `--info-card-radius` | `8px` | 卡片圆角 |
| `--info-card-border` | `#e2e8f0` | 卡片边框 |
| `--info-card-header-h` | `35px` | 标题栏高度（含底边框） |
| `--info-card-header-bg` | `#e2e8f0` | 标题栏背景 |
| `--info-card-header-border` | `#cbd5e1` | 标题栏底边 |
| `--info-card-header-pl` / `--info-card-header-pr` | `12px` / `8px` | 标题栏左 / 右内边距 |
| `--info-card-title-fs` | `13px` | 标题字号 |
| `--info-card-title-color` | `#1e293b` | 标题颜色 |
| `--info-card-body-padding` | `6px 8px` | 内容区内边距 |
| `--info-card-gap` | `6px` | 卡片间距（由容器使用） |

**数值只改这里**；使用方不要覆盖 `InfoCard` 内部样式，也不要在组件里写死同类数值。

---

## 五、检查清单

- [ ] 卡片用的是 `InfoCard`，没有 `el-card` + `#header` 或自绘的标题条
- [ ] 标题栏 35px、`#e2e8f0` 底、左 12 / 右 8，标题 13px 粗体
- [ ] 控件在 `#tools`，条数 / 根数 / 更新时间在 `#extra`（最右侧），内容区没有重复显示
- [ ] 表格卡片内容区无内边距，表格撑满卡片宽度；表格外没有额外 padding 包裹层
- [ ] 非表格卡片内容区有 `6px 8px` 内边距
- [ ] K 线卡片左右边距对称，图下方没有副图留白
- [ ] 卡片无阴影，圆角 8px
