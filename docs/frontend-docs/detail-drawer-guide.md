# 详情抽屉开发规范

> 适用范围：所有"点一条记录 → 右侧滑出查看详情"的抽屉（股票详情、以后的概念详情、池详情等）。
> 纯列表 / 纯表单抽屉（如采集管理的「执行记录」、概念看板的「成分股」）不在此范围。
>
> 骨架组件：`frontend/src/components/DetailDrawer.vue`
> 参考实现：`frontend/src/views/stock-info/components/StockDetailDrawer.vue`

---

## 一、整体结构

详情抽屉固定分三个区域，自上而下：

```
┌──────┬──────┬────────────────────┬────┐
│  📁  │  📈  │                    │ ✕  │  ① top-button-area   固定 48px，不滚动
│加入池│K线分析│                    │    │     贴顶通栏，按钮无间距，竖线分隔
╞══════╧══════╧════════════════════╧════╡  ← 1px #cbd5e1 实线 + 下投影
│ ▍基本信息                              │  ② baseinfo-area     高度随内容
│ 股票名称：平安银行  股票代码：000001.SZ│     区块标题 + 2 列字段
│ 市场：主板          行业：银行         │
├░░░░░░░░░░░░ 8px 灰色色带 ░░░░░░░░░░░░░┤  ← 区块分隔（抽屉底色露出）
│ ▍数据面  技术面│资金面│基本面│新闻面│概念│  ③ main-area         高度随内容
│ ┌──────────────────────────────────┐ │     区块标题 + 右侧 Tab
│ │ 日 K  [60日][MA5,MA20]     60 根 │ │     ← 卡片标题栏（浅灰工具栏）
│ │  （图表 / 表格）                 │ │
│ └──────────────────────────────────┘ │
│ ┌──────────────────────────────────┐ │     卡片间距 6px
│ │ 复权因子                   30 条 │ │
└──────────────────────────────────────┘
```

| 区域 | 高度 | 滚动 | 内容 |
|---|---|---|---|
| ① `top-button-area` | **固定 48px** | 不滚动，始终可见 | 操作按钮 + 关闭按钮 |
| ② `baseinfo-area` | 随内容 | 与 ③ 一起整体滚动 | 区块标题 + 字段网格（+ 可选扩展插槽） |
| ③ `main-area` | 随内容 | 与 ② 一起整体滚动 | 区块标题 + Tab + 面板（由卡片组成） |

### 1.1 分隔层级（两种，不能混用）

| 位置 | 样式 | 含义 |
|---|---|---|
| ① 与下方之间 | `1px #cbd5e1` 实线 + `0 2px 8px rgba(15,23,42,.08)` 投影 | 固定层与滚动层 |
| ② 与 ③ 之间 | 抽屉底色 `#f1f5f9` 露出的 8px 色带，② ③ 都是白底 | 并列内容块 |
| 卡片之间 | 6px 间距，卡片自带 1px 边框 | 同一面板内的子块 |

### 1.2 内边距归属

**内边距只由各区域自己给**，`el-drawer__body` 的 padding 固定为 0：

- 按钮区要贴边通栏、灰色色带要横贯全宽，容器有 padding 这两点都做不到；
- 内容区块（② ③）统一 `4px 16px 12px`（标题行自带 40px 行高，顶部不需要再留大边距）；
- 面板组件**不要**再加外层 padding / margin。

`el-drawer__body` 的覆盖样式写在组件的**非 scoped** `<style>` 里，用 `.detail-drawer` 限定（`el-drawer` 的根节点不带本组件 scoped 属性，`:deep` 不生效）。

### 1.3 宽度约束

抽屉宽度只由 `size` 决定，**任何内部组件都不能撑宽或挤压抽屉**。组件已做的兜底：

- 滚动容器 `scrollbar-gutter: stable`：始终预留滚动条位置，切换到内容很短的 Tab（如新闻面）时宽度不跳动；
- 滚动容器 `overflow-x: hidden`；各区块 `min-width: 0; overflow-x: clip`；
- 区块 / 面板的直接子元素 `max-width: 100%`，字段网格用 `minmax(0, 1fr)`。

面板自身仍需遵守：不写死大于抽屉的宽度；宽表格交给 `el-table` 自己横向滚动；长文本 `word-break: break-all`；图表按容器宽度自适应。

---

## 二、使用方式

```vue
<DetailDrawer
  v-model="visible"
  v-model:active="activeTab"
  :actions="actions"
  :fields="fields"
  main-title="数据面"
  :panels="PANELS"
  @action="onAction"
>
  <template #panel-overview>...</template>
  <template #panel-history>...</template>
</DetailDrawer>
```

### 2.1 Props

| Prop | 类型 | 默认 | 说明 |
|---|---|---|---|
| `v-model` | `boolean` | 必填 | 抽屉显隐 |
| `v-model:active` | `string` | 第一个面板 | 当前 Tab；每次打开抽屉重置为第一个面板 |
| `size` | `string \| number` | `'480px'` | 抽屉宽度 |
| `actions` | `DetailDrawerAction[]` | `[]` | 顶部按钮 |
| `baseinfoTitle` | `string` | `'基本信息'` | ② 区块标题 |
| `fields` | `DetailDrawerField[]` | — | ② 字段，2 列网格，渲染为 `标签：值` |
| `mainTitle` | `string` | `'详细数据'` | ③ 区块标题 |
| `panels` | `DetailDrawerPanel[]` | `[]` | ③ 面板列表；1 个直接显示，≥2 个自动出 Tab |

```ts
interface DetailDrawerAction {
  key: string                    // @action 回传
  label: string                  // ≤ 5 个汉字
  icon: Component                // @element-plus/icons-vue
  type?: 'default' | 'primary' | 'success' | 'warning' | 'danger'
  disabled?: boolean
}
interface DetailDrawerField { label: string; value?: string | number | null }  // 空值显示 —
interface DetailDrawerPanel { name: string; label: string }
```

### 2.2 插槽与事件

| 名称 | 说明 |
|---|---|
| `#panel-<name>` | 每个面板的内容，`<name>` 与 `panels[].name` 对应 |
| `#baseinfo` | ② 的扩展内容（字段网格之后），用于标签云、简介等无法用 `fields` 表达的内容 |
| `@action(key)` | 点击顶部按钮，回传 `actions[].key` |
| 其余 attrs | 透传给 `el-drawer`（如 `@close`、`append-to-body`） |

---

## 三、① top-button-area 规范

| 项 | 规范 |
|---|---|
| 高度 | 固定 48px，白底；底部 `1px #cbd5e1` 实线 + 投影 |
| 布局 | **贴顶通栏**：无上 / 左 / 右边距；按钮撑满区域高度、**无间距**，每个按钮右侧 `1px #cbd5e1` 竖线 |
| 操作按钮 | 宽 60px，无圆角；上图标 16px、下文字 11px；按 `type` 显示浅色底（`-light-9`）+ 同色图标文字，悬停底色加深（`-light-8`），按下内阴影 |
| 关闭按钮 | 由组件提供，宽 48px，**始终固定在最右侧**，左侧一条竖线；悬停变红 |
| 溢出 | 操作按钮过多时只在左侧区域横向滚动，**不换行**，不挤走关闭按钮 |

- 只放**对当前记录的操作**（加入池、跳转分析页、编辑、删除……），不放筛选或说明文字。
- 文字 ≤ 5 个汉字（"打开 K 线分析页"写成"K线分析"），完整含义放悬浮提示（组件已自动设置 `title`）。
- 颜色表达语义：主要跳转 `primary`、增加类 `success`、危险操作 `danger`、其余 `default`；同一抽屉内强调色不超过 2 种。
- **不要**自己再画关闭按钮，也不要开启 `el-drawer` 自带 header。

---

## 四、② baseinfo-area 规范

| 项 | 规范 |
|---|---|
| 区块标题 | 默认「基本信息」；左侧 3px × 16px 主色竖条 + 16px / 600 标题，行高 40px |
| 字段 | 固定 2 列网格，列间距 16px、行间距 6px；12px，渲染为 `标签：值`，标签 `#94a3b8`、值 `#1e293b` |
| 长值 | 自动换行（`word-break: break-all`），不截断、不省略 |
| 空值 | 统一 `—`（组件对 `null / undefined` 兜底，页面组装时也应处理空串） |

- **名称、编码也作为字段**放进 `fields` 并排在最前（如 `股票名称：平安银行`、`股票代码：000001.SZ`），不另做大标题行。
- **同一信息只出现一次**（有了 `000001.SZ` 就不再单独写 `000001`）。
- 不使用 `el-descriptions` 带边框表格；不在这里放图表或表格。

---

## 五、③ main-area 规范

### 5.1 标题与 Tab

```
▍数据面   📈 技术面 │ 💰 资金面 │ 📊 基本面 │ 📰 新闻面 │ 概念
└ 标题 ┘  └──────────── Tab 头：占满标题右侧剩余宽度 ────────────┘
```

| 项 | 规范 |
|---|---|
| 区块标题 | 用 `mainTitle` 概括面板集合（股票详情为「数据面」）；样式与 ② 标题一致 |
| Tab 位置 | 与标题**同一行**，放在标题右侧，`stretch` 平分剩余宽度 |
| Tab 文案 | ≤ 3 个汉字，可带 1 个 emoji 前缀；13px，左右内边距 6px |
| Tab 数量 | 480px 下 ≤ 5 个可一次看全；超过时合并面板或加宽抽屉 |
| 吸顶 | **不吸顶**，Tab 头随内容一起滚走 |
| 单面板 | 只有 1 个面板时不出 Tab，标题行只有标题 |
| 切换 | 所有面板始终挂载、`v-show` 切换，切回不重新请求数据 |

### 5.2 面板

- 面板组件放在页面自己的目录下（如 `data-board-tabs/*`），抽屉只负责组装。
- 面板根元素为单列网格（股票详情中传 `columns="1"`），卡片间距由抽屉统一为 6px。
- 面板内部**不要**再设固定高度 + `overflow: auto`，交给抽屉整体滚动；表格确需限高时用 `el-table` 的 `max-height`。

### 5.3 卡片

面板内的卡片统一使用 `InfoCard`，规范见 **[`card-guide.md`](./card-guide.md)**。

抽屉内的特殊约定：

- 日 K 不提供副图（`kline-sub="false"`），图高 180px。
- 卡片间距 `var(--info-card-gap)`（6px）由抽屉统一设置。

---

## 六、新增一个详情抽屉的步骤

1. 在页面目录下建 `XxxDetailDrawer.vue`，根元素用 `<DetailDrawer>`。
2. 定义 `actions`、`PANELS` 常量；用 `computed` 从记录组装 `fields`（名称、编码在最前）。
3. 每个面板写一个 `#panel-<name>` 插槽，面板组件需要的参数（`symbol`、`id`……）在插槽内用 `v-if="record"` 保护。
4. 面板内卡片按 `card-guide.md` 组织标题栏与内容区。
5. `@action` 里按 `key` 分发为页面自己的 emit 或路由跳转。
6. 父页面只关心 `v-model`、记录对象和业务事件，不感知抽屉内部结构。

---

## 七、检查清单

- [ ] 按钮区贴顶通栏、按钮间无间距且有竖线分隔，高度 48px 不变，底部有实线 + 投影
- [ ] 右上角只有一个关闭按钮，且始终在最右侧
- [ ] `el-drawer__body` 无 padding，面板组件没有额外的外层边距
- [ ] ② ③ 都有区块标题，二者之间是灰色色带分隔
- [ ] 名称 / 编码以 `标签：值` 形式出现在字段里，没有重复信息；长值正常换行
- [ ] 1 个面板时没有 Tab；多个面板时 Tab 在标题右侧一次看全，滚动时不悬浮
- [ ] 卡片通过 `card-guide.md` 的检查清单
- [ ] 逐个切换所有 Tab，抽屉宽度、Tab 头位置不跳动，无横向滚动条
- [ ] 面板内部没有固定高度的滚动容器
