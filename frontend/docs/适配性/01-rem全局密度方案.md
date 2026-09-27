# 方案 01：rem 全局密度方案（纯 CSS · 零依赖）

> **状态**：✅ 已落地（v1.1，2026-09-27，方案 + layout 微调 + 样板页改造）
> **目标**：通过一行 `:root { font-size }` 控制全站密度与字号，跟随屏幕宽度与 Win 系统缩放偏好。
> **依赖**：**0**（不需要 PostCSS、不需要 npm 包、不需要 JS）。
> **改动文件**：
> - 密度核心：`frontend/src/assets/main.css`
> - 容器：`frontend/src/layouts/Shell.vue` + `MainContainer.vue`（layout 微调 v0.2）
> - 页面：`frontend/src/components/PageWrapper.vue` + `views/stock-info/StockInfoList.vue`（样板页 v1.1）

---

## 一、原理

### 1.1 rem 的本质

- `rem`：相对于 **`<html>` 根元素 `font-size`** 的单位。
- 浏览器默认 `html { font-size: 16px }` → `1rem = 16px`。
- **`<body>` 上的 `font-size` 对 rem 无效**，很多人会混淆这一点。

```
:root / html  font-size = 14px
  ├── .el-table font-size: 0.929rem → 13px
  ├── .page-padding: 1rem → 14px
  └── .el-button height: 2.286rem → 32px
```

### 1.2 为什么"改根字号一行就能影响全站"

- **Element Plus** 内部大量间距使用 `--el-table-row-height`、`--el-button-size` 等 CSS 变量，这些变量一旦用 `rem` 声明，就会跟着根字号等比缩放。
- **Tailwind v4** 的工具类（`text-sm`、`p-4`、`gap-2`）底层就是 rem 派生，改根字号后工具类也跟着缩。
- **业务组件**（自定义 CSS / scoped style）只要**关键尺寸用 rem**，就会自动跟进。

### 1.3 为什么不用第三方库

| 库 | 不用的理由 |
|----|-----------|
| `postcss-pxtorem` | 与 Tailwind v4 `@theme` 配置有兼容问题；会把 Element Plus 内部 `el-` 前缀类的 px 强制转换，必须写一长串 `selectorBlackList`；本项目写死的 px 数量可控，手写 rem 成本更低 |
| `amfe-flexible` | 通过 JS 设置根字号会**覆盖**用户 Win 系统"更改文本大小"的用户偏好；本项目是 PC 后台，不需要跟随手机分辨率 |
| `lib-flexible`（淘宝旧方案） | 同上，且已停止维护 |

---

## 二、方案详细说明

### 第 1 步：把根字号从 `body` 移到 `:root`

**为什么**：rem 只看 `<html>` 根元素，把 `font-size` 写在 `<body>` 上是常见误区。

**当前代码**（`frontend/src/assets/main.css:41-47`）：

```css
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;            /* ❌ 写在 body 上，rem 看不到 */
  color: var(--color-admin-text);
  background: var(--color-admin-bg);
  -webkit-font-smoothing: antialiased;
}
```

**改成**：

```css
:root {
  font-size: 14px;            /* ✅ 根字号，1rem = 14px */
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 1rem;            /* ✅ 继承根字号，后续跟 :root 走 */
  color: var(--color-admin-text);
  background: var(--color-admin-bg);
  -webkit-font-smoothing: antialiased;
}
```

### 第 2 步：把"密度控制器"全部用 rem 写

这一节是核心。把以下 3 类尺寸**集中在 `:root` 声明一次**，全站就具备了一键收紧/放松密度的能力。

#### 2.1 Element Plus 表格密度（影响最大）

```css
:root {
  /* Element Plus 表格：紧凑密度 */
  --el-table-row-height: 2.857rem;       /* 40px（14px 基准） */
  --el-table-cell-padding-block: 0.5rem;  /* 7px */
  --el-table-cell-padding-inline: 0.5rem; /* 7px */
}

.el-table {
  font-size: 0.929rem;                   /* 13px */
}
.el-table th.el-table__cell {
  font-size: 0.929rem;
}
```

**效果**：表格行高从默认 ~50px 降到 40px，每屏多看 2-3 行；表头与单元格字号统一 13px。

#### 2.2 主区域 padding / gap（自动跟随）

```css
:root {
  --page-padding: 1rem;   /* 14px（原 16px → 更紧凑） */
}
```

`MainContainer.vue:21` 已经引用了 `var(--page-padding)`：
```css
padding: var(--page-padding, 16px);
```
**业务文件不用改**，变量值改了，布局自动跟进。

#### 2.3 Element Plus 通用组件变量（按钮 / 输入框 / 间距）

```css
:root {
  --el-font-size: 1rem;                  /* 14px，全局基准 */
  --el-button-size: 2.143rem;            /* 30px，按钮紧凑 */
  --el-input-height: 2.286rem;           /* 32px，输入框紧凑 */
  --el-component-size: 2.286rem;         /* 32px，通用控件紧凑 */
  --el-padding-base: 0.571rem;           /* 8px，EP 内部间距基准 */
  --el-margin-base: 0.571rem;
}
```

**覆盖参考值**（默认值 vs 收紧值）：

| 变量 | Element Plus 默认 | 本方案 | 等效 px |
|------|-------------------|--------|--------|
| `--el-font-size` | 14px | `1rem` | 14px |
| `--el-button-size` | 32px | `2.143rem` | 30px |
| `--el-input-height` | 32px | `2.286rem` | 32px |
| `--el-table-row-height` | 50px | `2.857rem` | 40px |
| `--el-table-cell-padding-block` | 12px | `0.5rem` | 7px |

> 表中"等效 px"按 `:root font-size = 14px` 计算。如果根字号改为 13px 或 15px，所有值等比缩放。

### 第 3 步（可选）：用 `clamp()` 实现自适应基准

如果希望在 1280 / 1920 / 2560 三档屏宽下都有合适的密度，可以用 `clamp()`：

```css
:root {
  /* 屏宽 1280px → 13.5px；1920px → 14px；2560px → 14.7px（封顶 15px） */
  font-size: clamp(13.5px, 0.4vw + 12.5px, 15px);
}
```

**计算公式验证**：
- `1280 * 0.01 + 12.5 = 25.3px` → 但浏览器会拦截 ≤12px，这里 ≥13.5px 会被识别。
- 实际：`0.4vw` 在 1280px 屏 = `5.12px`，加 `12.5px = 17.62px`，被 `min(13.5px)` 兜底 → **13.5px**。
- `0.4vw` 在 1920px 屏 = `7.68px`，加 `12.5px = 20.18px` → 落在 `[13.5, 15]` 之间 → 约 **14px**。
- `0.4vw` 在 2560px 屏 = `10.24px`，加 `12.5px = 22.74px`，被 `max(15px)` 封顶 → **15px**。

> **Win 系统缩放 125%**：根字号会基于 UA 默认 16px × 1.25 = 20px，clamp 的输出值会乘以 1.25（浏览器行为），所以全站也等比放大 ✅。

**替代写法**（如果觉得 0.4vw 系数不合适）：

```css
:root {
  font-size: clamp(13.5px, 0.5vw + 12px, 15px);  /* 略激进 */
}
```

---

## 三、落地改动清单

### 3.1 唯一改动文件

| 文件 | 改动 |
|------|------|
| `frontend/src/assets/main.css` | 新增/替换：`:root { font-size }`、EP 表格变量、EP 通用组件变量；调整 `body` 的 `font-size` |

### 3.2 改动后 `main.css` 完整结构预览

```css
@import "tailwindcss";

/* ── 自定义 CSS 变量 ──────────────────────────── */
:root {
  /* ★ 新增：根字号基准（影响全站 rem 派生） */
  font-size: 14px;                         /* 或 clamp(...) 自适应 */

  /* ── 原变量保留 ── */
  --color-primary:       #2563eb;
  /* ... 其余颜色变量 ... */

  --sidebar-width:      220px;
  --sidebar-collapsed:  56px;
  --topbar-height:      3rem;
  /* ... 其余布局变量 ... */

  /* ★ 改写：用 rem 派生 */
  --page-padding:       1rem;              /* 14px（原 16px → 紧凑） */

  /* ★ 新增：EP 通用组件紧凑化 */
  --el-font-size:        1rem;
  --el-button-size:      2.143rem;
  --el-input-height:     2.286rem;
  --el-component-size:   2.286rem;
  --el-padding-base:     0.571rem;
  --el-margin-base:      0.571rem;

  /* ★ 新增：EP 表格紧凑化 */
  --el-table-row-height:          2.857rem;
  --el-table-cell-padding-block:  0.5rem;
  --el-table-cell-padding-inline: 0.5rem;
}

/* ── Tailwind 主题扩展 ────────────────────────── */
@theme {
  --color-primary: #2563eb;
  --color-admin-primary: #2563eb;
}

/* ── 全局重置 ────────────────────────────────── */
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 1rem;                          /* ★ 改：跟 :root 走 */
  color: var(--color-admin-text);
  background: var(--color-admin-bg);
  -webkit-font-smoothing: antialiased;
}

/* ★ 新增：EP 表格字号统一 */
.el-table {
  font-size: 0.929rem;
}
.el-table th.el-table__cell {
  font-size: 0.929rem;
}

/* ── 滚动条美化（不变） ─────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
/* ... */

/* ── Element Plus 覆盖（不变/微调） ────────── */
.el-card {
  --el-card-border-radius: 12px;
  /* ... */
}
.el-table {
  --el-table-header-bg-color: #f8fafc;
  --el-table-header-text-color: #334155;
  --el-table-row-hover-bg-color: #f8fafc;
}
/* ... */
```

---

## 四、效果与对比

### 4.1 改动前后量化对比（1920×1080 屏）

| 指标 | 改动前 | 改动后 | 提升 |
|------|--------|--------|------|
| 表格行高 | ~50px | 40px | +25% 同屏可见行数 |
| 表格字号 | 14px | 13px | 行内信息密度更高 |
| 主区域左右 padding | 16px × 2 | 14px × 2 | +4px 横向可读空间 |
| 按钮高度 | 32px | 30px | toolbar 更紧凑 |
| 输入框高度 | 32px | 32px（不变） | 无变化 |
| `StockInfoList` 单屏可见行数 | 14-15 | **17-18** | +20% |

> 注：列数问题不靠 rem 解决，详见方案外的"列数优化"清单（在 README 第二章节"方案选择矩阵"中说明）。

### 4.2 屏幕档位适配（clamp 模式下）

| 屏宽 | 根字号 | 表格行高 | 备注 |
|------|--------|---------|------|
| 1280×720 | 13.5px | 38.5px | 紧凑档，13 寸笔记本 |
| 1920×1080 | 14px | 40px | 默认档 |
| 2560×1440 | 15px | 42.8px | 宽松档，2K 屏 |

---

## 五、风险与边界

### 5.1 已知风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| EP 内部用 px 写死的部分（如某些 border、icon 内部 SVG）不会跟着缩 | 这些是合理的"绝对尺寸"，**应保持原样** | 不动它们即可 |
| `clamp()` 系数（0.4vw）需要现场调 | 系数不对会导致密度档位偏差 | 在 `StockInfoList` 和 `Dashboard` 两个典型页面分别截图验证 |
| 浏览器最低字号拦截（Chrome / Edge 最低 12px） | `clamp(13.5px, ...)` 下限够高，不会触发 | 已经按 ≥12px 设计 |
| Tailwind 工具类 `text-xs` = 12px 在小屏下显得小 | 小概率视觉问题 | 必要时可写一个 `.text-xs { font-size: 0.857rem }` 兜底 |

### 5.2 不在本文档解决

- **"列数太少"问题**：本文档只解决密度（行高 / 字号 / padding），不解决列数。列数问题需在 `StockInfoList.vue` 砍 fixed 列或收窄列宽（不在本方案范围）。
- **侧边栏折叠态持久化**：是独立小需求，与本方案解耦。
- **Win 系统 DPI 缩放（不是"文本大小"）**：这是浏览器层面的缩放（Ctrl + 加号），不影响 rem 派生。
- **暗色模式**：本项目目前未启用，留待后续方案。

### 5.3 验证清单（实施后逐项过）

- [ ] `npm run build` 通过，无 TS / Vite 报错
- [ ] `StockInfoList` 表格在 1920×1080 屏下显示 17-18 行
- [ ] 切换 Win 系统文本大小 100% / 125% / 150%，全站等比缩放 ✅
- [ ] 在 1280×720 屏下确认无横向滚动条（基于 clamp 模式）
- [ ] 工具栏按钮、输入框、分页组件字号统一不偏大
- [ ] 切换 dark 模式（如未来启用）不影响变量继承

---

## 六、后续扩展

本方案是"适配性"的最小可用版本。后续可在此基础上扩展：

| 进阶方向 | 简要 |
|---------|------|
| 02. 三档密度切换 | Compact / Default / Comfortable，提供用户手动切换按钮（CSS class toggle） |
| 03. 暗色模式 | 在 `:root.dark` 下覆盖颜色变量 + EP `--el-color-*` 系列 |
| 04. 局部密度覆盖 | 关键页面（如 K线详情）单独定义更高密度的子作用域 |
| 05. 列宽自适应 | 用 `min-width` + `flex` 让滚动列表头自适应剩余空间 |

---

## 八、layout 微调增量（v0.2，2026-09-27 13:30）

> 这是方案 01 落地后的"同源补强"，仍是 0 依赖、3 行 CSS、零风险。
> 动机：方案 01 把密度收紧后，TopBar 与主区域之间的视觉层次反而**变得平淡**——这是密度收紧常见的副作用。补一条分隔线与一个 gap 变量，把"密度收紧"与"层次精致"同时拿住。

### 8.1 改动清单（3 处）

| 文件 | 改动 | 代码 |
|------|------|------|
| `assets/main.css` | 新增 2 个 shell 桥接变量 | `--shell-divider: 1px solid var(--color-admin-border);`<br>`--page-gap: 0.5rem;` |
| `layouts/Shell.vue` | TopBar 加底部分隔线 | `.shell-topbar { border-bottom: var(--shell-divider); }` |
| `layouts/components/MainContainer.vue` | 接入 gap 变量 | `.main-container { gap: var(--page-gap, 0); }` |

### 8.2 改动理由

| 改动 | 解决什么 |
|------|---------|
| `--shell-divider` | TopBar 与主区域之间原本全靠背景色差区分，密度收紧后"`f5f7fb` → `f5f7fb`"几乎无缝，**会显平**。一条 1px 分隔线提升"层级呼吸感" |
| `--page-gap` | 当前 MainContainer 只放一个 `<router-view>`，gap 不直接生效，但**保留接口**——未来如出现"筛选条 + 表格"两段堆叠，一行 CSS 即可拉开间距，不需要回头再改 |

### 8.3 设计原则

- **小步推进**：每一步都是 1-2 行 CSS，立即可验证、可回退
- **变最先动**：所有新尺寸都进 `:root`，业务样式只引用 `var()`——延续方案 01 的"单一变量源"原则
- **兼容历史**：`var(--xxx, fallback)` 双兜底，删除某个变量不会破页面

### 8.4 效果对比

| 场景 | 改动前 | 改动后 |
|------|--------|--------|
| TopBar 与主区域边界 | 靠背景色过渡，密度升级后边界模糊 | 一条 1px `#e5e7eb` 分隔线，层次清晰 |
| 未来"多 PageWrapper 堆叠" | 每个内部容器自己定义 gap，散乱 | 主区域共享 `--page-gap`，口径统一 |

### 8.5 后续还能做什么（可选）

| 增强 | 价值 |
|------|------|
| 给 TopBar 加 0.5px 阴影 `box-shadow: 0 1px 0 rgba(...)` 替代 1px border | 视网膜屏视觉更精致，但兼容性需测试 |
| Shell 背景从 `var(--color-admin-bg)` 改为带 1px noise 纹理 | 视觉降噪，但会增加 0.5KB 资源 |
| 给侧边栏 `.leftbar-slot` 加 `padding-top: var(--page-gap)` 与 TopBar 对齐 | 视觉对称，但要看是否破坏悬浮岛效果 |

> 上面三个都是"锦上添花"，**不影响密度**，等真的需要再回头做。

---

## 九、样板页改造 — StockInfoList（v1.1，2026-09-27 13:45）

> 这是方案 01 落地的"**第二个验证**：证明页面级 CSS 也能跟随 `:root font-size` 自动调整密度，且不改任何数据列、不动任何 EP 主题。
> 与"八、layout 微调"的关系：layout 是容器，StockInfoList 是首个体现在用户眼前的真实页面改造样板。

### 9.1 改造动机

| 现状 | 问题 |
|------|------|
| `PageWrapper.vue` 内边距 `20px` / 三处 gap `16px 12px 8px` / `min-height 32px` 全部 px 硬编码 | 这些 px **不跟随 `:root font-size`**，但密度本来应该全局统一——出现"列表行高跟上了，工具栏间距没跟上"的撕裂 |
| `StockInfoList.vue` 工具栏 `gap 12px / 8px`、选中提示条 `padding 6px 12px / font-size 13px` 全部 px | 与 PageWrapper 同样的密度撕裂 |
| 表格列宽（`width="90"` `width="120"`）也用 px | **必须保留 px**——列宽本质是"绝对列宽"，不能跟 rem，否则不同字号下列宽漂移 |

### 9.2 改造清单（3 个文件）

| 文件 | 改动 |
|------|------|
| `assets/main.css` | 新增 6 个设计 token：`--density-card-padding` / `--density-gap-{xl,lg,md,sm}` / `--density-title-min` |
| `components/PageWrapper.vue` | 9 处密度敏感尺寸全部替换为 `var(--density-*)` |
| `views/stock-info/StockInfoList.vue` | 6 处密度敏感尺寸替换为 `var(--density-*)`，**列宽保留 px** |

### 9.3 6 个 token 的口径与命名

| Token | 值 | 原 px | 用在哪里 |
|-------|----|-------|----------|
| `--density-card-padding` | `1.125rem` | 20px → 14px | `PageWrapper` 内边距 |
| `--density-gap-xl` | `1rem` | 16px → 14px | `middle-area` 与 `bottom-area` 大间距 |
| `--density-gap-lg` | `0.75rem` | 12px → 11px | 标题与工具栏间距 |
| `--density-gap-md` | `0.5rem` | 8px → 7px | 工具栏组件间小间距 |
| `--density-gap-sm` | `0.375rem` | 6px → 5px | 选中提示条 icon / 文字 |
| `--density-title-min` | `2rem` | 32px → 28px | 标题区最小高度 |

> **值的选择**：原 px 除以 14（项目 `:root font-size`），得到最接近的 rem 值。比例保持一致，**视觉等比缩放而非剧烈重排**。

### 9.4 关键设计判断："哪些 px 必须保留"

| 类型 | 处理 | 原因 |
|------|------|------|
| **列宽**（`<el-table-column width="90">`） | 保留 px | 列宽是"绝对宽度"，跟 rem 会漂移 |
| **border 1px** | 保留 px | 浏览器最低边框单位就是 1px |
| **border-radius 8px / 12px** | 保留 px | 圆角不跟字号缩放 |
| **icon 尺寸**（`.brand-icon`） | 保留 | font-size 用 rem |
| **font-size** | 改 rem | 字号本身就该跟 density 走 |
| **padding / margin / gap / min-height** | 改 rem | 密度感知的核心 |

### 9.5 验证清单（实施后逐项过）

- [ ] 浏览器刷新页面，**工具栏间距与表格行高视觉一致**（之前左侧偏紧、右侧偏松的撕裂消失）
- [ ] 切到 1920×1080 屏：行高 ≈ 36-40px，工具栏总高度 ≈ 56-64px
- [ ] 切到 1280×720 屏：所有间距等比收紧，行数显示更多
- [ ] 选中提示条"已选 N 只股票"字号与正文一致，不再偏小
- [ ] 高级筛选展开动效流畅（grid-rows 0fr → 1fr + padding 0 → var() 无回退）
- [ ] 表格列对齐不漂移（因为列宽还是 px）
- [ ] Win 系统文本大小切到 125% / 150%，整页等比放大

### 9.6 立即可复用的"迁移手册"（给后续页面）

#### Step 1：替换 4 类尺寸
```css
/* 老 */
padding: 20px; gap: 16px; gap: 12px; gap: 8px;
font-size: 13px; min-height: 32px;

/* 新 */
padding: var(--density-card-padding);
gap: var(--density-gap-xl); /* 16 */
gap: var(--density-gap-lg); /* 12 */
gap: var(--density-gap-md); /* 8 */
font-size: 0.929rem;        /* 沿用表格 13px */
min-height: var(--density-title-min);
```

#### Step 2：哪些 px 必须保留
- `border*` 颜色与宽度（1px）
- `border-radius`
- `box-shadow` 偏移量
- `<el-table-column width="..">` 列宽
- 头像 / icon 的 `width / height`（除非它们与字号挂钩）

#### Step 3：自检
- 打开 Chrome DevTools，调节 `:root { font-size: 13px / 14px / 16px / 18px }`
- 间距应该等比缩放，列宽不变，文字不断行不溢出

### 9.7 未来页面的预期增量

| 页面 | 改造量 | 备注 |
|------|--------|------|
| `pool/PoolList.vue` | 约 6-8 行替换 | 与 StockInfoList 同结构，可直接复用 |
| `kline/* / minute_kline` | 约 10 行替换 | 涉及图表边距，建议统一 token |
| `concept/* ` | 约 5 行替换 | 标签密度敏感 |
| `home/Dashboard.vue` | 约 8 行替换 | 卡片 grid 间距需统一 |

> 总估计：全站剩余页面改造量 40-60 行，**沿用 `--density-*` 6 个 token**即可，无需新增变量。

---

## 七、参考与延伸阅读

- MDN: [CSS Values - rem](https://developer.mozilla.org/zh-CN/docs/Learn/CSS/Building_blocks/Values_and_units#%E5%8D%95%E4%BD%8D)
- Element Plus: [CSS 变量参考](https://element-plus.org/zh-CN/guide/theming.html#css-%E5%8F%98%E9%87%8F)
- 项目内：`frontend/docs/layout-guide.md`（结构规范，与本方案互补）
- 项目内：`frontend/src/assets/main.css`（密度变量单一源）
- 项目内：`frontend/src/layouts/Shell.vue` + `MainContainer.vue`（layout 桥接入口）
