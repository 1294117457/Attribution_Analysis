# 数据链路 UML 图设计规范

> 适用于后端业务数据流 / 跨层调用的"以表为源、以层为路"的 PlantUML 图绘制。
> 标准模板：`StockInfo/03-panel-compose.puml`。

---

## 0. 图型分类（先选型，再画图）

画图前必须先确定图型。**不同图型有不同模板，禁止混用。**

| 图型 | 用途 | 核心特征 | 模板章节 |
| --- | --- | --- | --- |
| **查询数据流图** | 一条 API 请求的完整链路（读取） | 四层一行 + 来源表（两行结构） | §9.1 |
| **同步/采集流图** | 外部数据源 → 本地持久化（写入） | 四层一行（层名调整） + 来源/目标表 | §9.2 |
| **类图概览** | 某功能模块的全部新增/修改类 | 按层分包、颜色区分增改，无强制四层一行 | §9.3 |
| **领域模型图** | 多个 API 共享的 Entity/VO 关系 | 聚焦实体关系，不画层 | 不在本规范内 |

### 0.1 图型选择决策树

```
你要描述的是：
├─ 一个 API 的请求→响应全链路？
│     → 查询数据流图（§9.1 模板）
├─ 一个外部数据源的采集→持久化？
│     → 同步/采集流图（§9.2 模板）
├─ 一个功能模块涉及的所有新增/修改类？
│     → 类图概览（§9.3 模板）
└─ 多个 API 共享的领域模型关系？
      → 领域模型图（不在本规范范围）
```

### 0.2 一图一链路原则

> **一张数据流图（查询/同步）只描述一条完整链路。**
> 如果一个功能有 3 个 API，就画 3 张数据流图，不要合并。

---

## 1. 设计目标

一张数据流图同时回答三个问题：

| 问题 | 对应区域 |
| --- | --- |
| 数据从哪里来？ | 第二行：来源表（仅关键字段） |
| 数据走过哪些层？ | 第一行：4 层主角类一字排开（请求 → 仓储 → 领域 → 应用） |
| 业务如何组装数据？ | 便签（组装关系 + 服务流伪代码） |

> **一句话**：第一行四层主角一字排开看链路，第二行来源表看数据源，便签看组装逻辑。

---

## 2. 总体布局（两行 + 便签）

```
┌────────────────────────────────────────────────────────────┐
│  ╔═══════════════════╗                                     │
│  ║ 便签 N_src        ║   ┐ 装配关系 + 服务流伪代码           │
│  ║ (组装 + 调用)     ║   ┘                                  │
│  ╚═══════════════════╝                                     │
│                                                            │
│  ╔═══ 模型层 ══════════════════════════════════════════╗   │
│  ║ [① 请求层] → [② 仓储层] → [③ 领域层] → [④ 应用层]  ║   │ ← 第一行（横向）
│  ╚═════════════════════════════════════════════════════╝   │
│           │           │           │           │            │
│           ↓ 虚线（聚合 / 组合 / 最新一行 / 最新一期）       │
│  ╔═══ 来源表 ══════════════════════════════════════════╗   │
│  ║ [T1] → [T2] → [T3] → [T4]                          ║   │ ← 第二行（横向）
│  ╚═════════════════════════════════════════════════════╝   │
└────────────────────────────────────────────────────────────┘
```

- **第一行**：模型层（4 个子 package），从左到右线性。
- **第二行**：来源表（≥ 1 张物理表 / 外部 API），从左到右排列。
- **便签**：说明领域对象如何由来源表组装，并附带 1 段服务层伪代码。

---

## 3. 硬性约束（数据流图必须遵守）

| 约束项 | 上限 | 违反时处理 |
| --- | --- | --- |
| 每层 package 内主角类 | **1 个** | 配角折叠到主角字段中（见 §3.1） |
| 每层 package 内总类数 | **≤ 3 个** | 超出则拆图或省略非核心类 |
| 第一行层间箭头 | **≤ 5 条** | 超出则合并为便签文字描述 |
| 来源表数量 | **≤ 6 张** | 超出则只保留主查询涉及的表 |
| 便签总行数 | **≤ 15 行** | 超出则精简伪代码或拆到配套 .md |
| 单个类的出射箭头 | **≤ 3 条** | 超出说明该类混入了多条链路，应拆图 |
| 顶层 package 数量 | **= 2** | 只允许"▌ 模型层"和"▌ 来源表" |

> **核心判定**：如果一个类需要向 4+ 个目标画箭头，说明你在一张图里混了多条链路，必须拆分。

### 3.1 主角类原则

每层选定 **1 个主角类**，四个主角构成主链路：

```
请求层主角 ──→ 仓储层主角 ──→ 领域层主角 ──→ 应用层主角
```

其他类（如 `PoolMembershipVO`、`ConceptBriefVO`）作为**配角**：

- 配角优先以字段引用的方式出现在主角类内（`+ concepts : list[ConceptBriefVO]`）
- 配角不参与主链路箭头
- 如果配角复杂到需要单独展开字段，可在同层内放置（但受"每层≤3 类"约束）
- 如果配角有自己的独立链路，另开一张子数据流图

---

## 4. 命名与标识规范

### 4.1 类 Stereotype（必须）

| Stereotype | 含义 | 示例 |
| --- | --- | --- |
| `<<NEW>>` | 本次新引入的类 | `<<NEW>>` |
| `<<CHANGED>>` | 本次修改的既有类 | `<<CHANGED>>` |
| `<<UNCHANGED>>` | 不变的既有类 | `<<UNCHANGED>>` |
| `<<Protocol>>` | 领域层接口契约（Python `Protocol`） | `<<Protocol, NEW>>` |
| `<<frozen>>` | 不可变值对象（`@dataclass(frozen=True)`） | `<<值对象, NEW, frozen>>` |
| `<<Generic>>` | 泛型类（如 `Page[T]`） | `<<Generic, NEW>>` |
| 无标记 | 复用既有类（简写） | — |

> 多个 stereotype 用逗号分隔：`<<Protocol, NEW>>`。

### 4.2 类名 / 别名

- **领域层值对象**：首字母大写，名词化（`StockPanelRow`）。
- **请求 / VO / 仓储 Protocol**：以层名结尾（`QueryRequest`、`ItemVO`、`ListVO`、`Repository`）。
- **物理表**：用双引号小写蛇形命名（`"stock_infos"`），并用 `as T1, T2, …` 取短别名。

### 4.3 字段写法

```puml
class Foo <<NEW>> {
  + 字段名 : 类型
  + 必填字段 : str                 ' 不带 ? 表示必填
  + 可选字段 : str?                ' 带 ? 表示可空
  + 列表字段 : list[Item]
  + 泛型字段 : dict[str, int]
  + 数值字段 : float = 0.0         ' 带默认值
}
```

- `+` = public；只在内部流转的字段不写 `+/-` 而用 `note` 注释。
- **计算字段**用分隔线 `----` + 注释说明公式：

```puml
+ n_income
+ revenue
----
+ profit_margin    ' = n_income / revenue × 100
```

### 4.4 颜色方案

| 元素 | 背景色 | 用途 |
| --- | --- | --- |
| 新增类 | `#C8E6C9` 浅绿 | 本次新引入 |
| 修改类 | `#FFE0B2` 浅橙 | 本次修改 |
| 不变类 | `#E0E0E0` 浅灰 | 复用既有 / 来源表 |
| 删除类 | `#FFCDD2` 浅红 | 本次移除（仅类图概览用） |
| 模型层、便签 | 默认 | — |

> 数据流图中若无增改区分需求，来源表统一用 `#E0E0E0`，模型层类用默认色。

---

## 5. 皮肤参数

```puml
skinparam linetype ortho           ' 直线（避免曲线干扰阅读）
skinparam classAttributeIconSize 0 ' 关闭字段图标
skinparam classFontSize 11
skinparam packageFontSize 13
```

---

## 6. 布局指令（关键）

```puml
left to right direction   ' 顶层水平方向
```

为保证来源表横向排列，必须在其 package 内**重复声明方向**，并使用**隐藏链接**强制同行：

```puml
package "▌ 来源表" {
  left to right direction   ' 覆盖外部方向，强制横排

  T1 -[hidden]- T2          ' 隐藏链接强制同 rank
  T2 -[hidden]- T3
  T3 -[hidden]- T4

  class "stock_infos" as T1 #E0E0E0 { ... }
  class "tech_kline_dailys" as T2 #E0E0E0 { ... }
  ...
}
```

> **坑**：仅在外层 `left to right direction` 不够，PlantUML 会按依赖图自动重排，必须 `-[hidden]-` + 内层方向声明同时使用。

---

## 7. 箭头与关系

| 场景 | 写法 | 示例 |
| --- | --- | --- |
| 同层调用（请求 → 仓储） | 实线 + 单箭头 | `A --> B` |
| 跨层产出（仓储 → 领域） | 虚线 + 单箭头 | `A ..> B : <<产出>>` |
| 字段一对一映射 | 实线 + 单箭头 | `A --> B : <<1:1 字段映射>>` |
| 领域对象 ⇢ 来源表 | 虚线，无标签（细节见便签） | `A ..> T1` |
| 继承 | 空心三角 | `Page <|-- ListVO : <<继承>>` |
| 泛型参数 | 虚线 + 标签 | `ItemVO ..> Page : <<T 参数>>` |
| 同行同 rank（强制横排） | 隐藏线 | `T1 -[hidden]- T2` |

> **约定**：标签内用 `<<...>>` 包围"角色"，与 stereotype 风格一致。

---

## 8. 便签规范

### 8.1 数量与位置

每个数据流图**最多 2 个便签**：

1. **`note as N_src`**：写"领域对象 ⇢ 来源表"的组装关系 + 服务层伪代码。
2. **`note bottom of ...`**：仅用于 1~2 行的简短注释（如"4 表 JOIN + 聚合的投影"）。

### 8.2 内容规范（≤ 15 行）

便签必须回答且**只回答两个问题**：

1. **组装关系**：领域对象由哪些表/API 组装（≤ 5 行）
2. **服务伪代码**：AppService 方法的核心步骤（≤ 5 行，最多 5 个步骤）

**以下内容禁止放入便签**（应写在配套 `.md` 文档中）：

- SQL 细节、索引说明
- 性能估算、耗时分析
- 优劣势对比
- 错误处理逻辑
- 并发/重试策略

### 8.3 便签格式

```puml
note as N_src
  <b>StockPanelRow 由 4 张表组装：</b>
  • stock_infos       → 组合（基本信息）
  • tech_kline_dailys → 聚合（COUNT / MIN / MAX）
  • fin_daily_basics  → 最新一行
  • fin_reports       → 最新一期（profit_margin = n_income / revenue × 100）
  ────────────────
  <b>StockPanelAppService.query_panels(req)</b>
  ① repo.list_paginated(req) → (list[StockPanelRow], int)
  ② items = [_to_vo(r) for r in rows] → list[StockPanelItemVO]
  ③ StockPanelListVO.from_list(items, total, page, page_size)
end note
```

便签内支持的标签：`<b>`、`•` 圆点、`────` 分隔线、`①②③` 编号、`→` 箭头、`...` 占位符。

---

## 9. 复用模板

### 9.1 查询数据流模板（读取链路）

适用于：一个 API 的 请求→仓储→领域→应用 响应全链路。

```puml
@startuml <Name>_DataFlow

title <Name> 数据流 — 四层 + 来源表

left to right direction

skinparam linetype ortho
skinparam classAttributeIconSize 0
skinparam classFontSize 11
skinparam packageFontSize 13

' ── 第一行：模型层 ──────────────────────────────
package "▌ 模型层" {
  package "① 请求层"  { class <Name>QueryRequest <<NEW>> { ... } }
  package "② 仓储层"  { class <Name>Repository <<Protocol, NEW>> { ... } }
  package "③ 领域层"  { class <Name>Row <<值对象, NEW, frozen>> { ... } }
  package "④ 应用层"  {
    class "Page[T] <<Generic, NEW>>" as Page { ... }
    class <Name>ItemVO <<NEW>> { ... }
    class <Name>ListVO <<NEW>> { ... }
    Page <|-- <Name>ListVO : <<继承>>
  }
}

' ── 线性依赖（主链路）──────────────────────────
<Name>QueryRequest --> <Name>Repository
<Name>Repository   ..> <Name>Row : <<产出>>
<Name>Row          --> <Name>ItemVO : <<1:1 字段映射>>

' ── 第二行：来源表 ──────────────────────────────
package "▌ 来源表" {
  left to right direction
  T1 -[hidden]- T2 -[hidden]- T3 -[hidden]- T4

  class "<table_a>" as T1 #E0E0E0 { ... }
  class "<table_b>" as T2 #E0E0E0 { ... }
  class "<table_c>" as T3 #E0E0E0 { ... }
  class "<table_d>" as T4 #E0E0E0 { ... }
}

' ── 领域对象 → 来源表 ─────────────────────────
<Name>Row ..> T1
<Name>Row ..> T2
<Name>Row ..> T3
<Name>Row ..> T4

' ── 便签 ──────────────────────────────────────
note as N_src
  <b><Name>Row 由 N 张表组装：</b>
  • table_a → ...
  • table_b → ...
  ────────────────
  <b><Name>AppService.<method>(req)</b>
  ① ...
  ② ...
end note

@enduml
```

### 9.2 同步/采集流模板（写入链路）

适用于：外部数据源 → BO → Entity → 本地持久化。

与查询流的关键区别：
- 数据方向：外部 → 内部（写入），而非 请求 → 响应（读取）
- 层语义调整：① 触发层 → ② 采集层 → ③ 领域层 → ④ 持久层

```puml
@startuml <Name>_SyncFlow

title <Name> 同步数据流 — 采集 → 持久化

left to right direction

skinparam linetype ortho
skinparam classAttributeIconSize 0
skinparam classFontSize 11
skinparam packageFontSize 13

' ── 第一行：模型层（同步流四层）──────────────────
package "▌ 模型层" {
  package "① 触发层" {
    class <Name>SyncRequest <<NEW>> { ... }
  }
  package "② 采集层" {
    class <Name>Fetcher <<Protocol, NEW>> {
      + fetch_list() : list[<Name>BO]
      + fetch_detail(key) : list[<Name>DetailBO]
    }
  }
  package "③ 领域层" {
    class <Name>BO <<NEW>> {
      + ...
      --
      + to_entity() : <Name>
    }
    class <Name> <<Entity, NEW>> { ... }
  }
  package "④ 持久层" {
    class <Name>Repository <<Protocol, NEW>> {
      + upsert(entity) : <Name>
      + upsert_members(id, members) : int
    }
    class <Name>SyncResult <<NEW>> {
      + total : int
      + failed : list[str]
      + elapsed_ms : int
    }
  }
}

' ── 线性依赖（主链路）──────────────────────────
<Name>SyncRequest  --> <Name>Fetcher
<Name>Fetcher      ..> <Name>BO          : <<采集产出>>
<Name>BO           --> <Name>            : <<to_entity>>
<Name>             --> <Name>Repository  : <<写入>>

' ── 第二行：来源/目标表 ─────────────────────────
package "▌ 数据源 & 目标表" {
  left to right direction
  S1 -[hidden]- T1 -[hidden]- T2

  class "外部 API\n(<source_name>)" as S1 #C8E6C9 { ... }
  class "<target_table_a>" as T1 #E0E0E0 { ... }
  class "<target_table_b>" as T2 #E0E0E0 { ... }
}

' ── 采集层 → 数据源 / 持久层 → 目标表 ──────────
<Name>Fetcher    ..> S1 : <<HTTP>>
<Name>Repository ..> T1 : <<upsert>>
<Name>Repository ..> T2 : <<upsert>>

' ── 便签 ──────────────────────────────────────
note as N_src
  <b><Name> 同步流程：</b>
  • <source_name> → <Name>BO → <Name> Entity
  • Entity → <target_table_a> + <target_table_b>
  ────────────────
  <b><Name>SyncOperation.sync_all()</b>
  ① fetch_list() → list[BO]
  ② for bo in bos: upsert + fetch_detail + upsert_members
  ③ return SyncResult
end note

@enduml
```

### 9.3 类图概览模板

适用于：展示某功能模块涉及的全部新增/修改类。

**不强制四层一行**，按逻辑层分 package，颜色区分增改。

```puml
@startuml <Name>_ClassOverview

title <Name> — 跨层类图概览

left to right direction

skinparam linetype ortho
skinparam classAttributeIconSize 0
skinparam classFontSize 12
skinparam packageFontSize 13

legend right
  |= 颜色 |= 含义 |
  | <#C8E6C9>绿 | 新增（NEW） |
  | <#FFE0B2>橙 | 修改（CHANGED） |
  | <#E0E0E0>灰 | 不变（UNCHANGED） |
endlegend

' ── 按逻辑层分包，每层列出关键类 ────────────────
package "持久层 (Persistence)" #ECEFF1 { ... }
package "采集层 (Collectors)" #ECEFF1 { ... }
package "领域层 (Domain)" #ECEFF1 { ... }
package "应用层 (Application)" #ECEFF1 { ... }
package "路由层 (Route)" #ECEFF1 { ... }
package "前端 (Frontend)" #ECEFF1 { ... }

@enduml
```

> 类图概览不受"每层≤3 类"限制，但单图总类数建议 **≤ 30**，超出则按子域拆分。

---

## 10. 渲染与命名约定

| 项 | 约定 |
| --- | --- |
| 文件命名 | `<NN>-<topic>.puml`（编号 + 主题） |
| 输出 PNG | 与 `.puml` 同目录、同名 `<topic>.png` |
| 渲染命令 | `plantuml -tpng <file>.puml` 或 `java -jar plantuml.jar -tpng <file>.puml` |
| `title` | 写"业务 + 图型"，例如 `StockPanel 列表数据流 — 四层 + 来源表` |

推荐的编号惯例：

| 编号 | 图型 |
| --- | --- |
| `01-class.puml` | 类图概览 |
| `02-*.puml` | 数据流图（查询链路） |
| `03-*.puml` | 数据流图（同步/采集链路） |

---

## 11. 常见坑位（必读）

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| 来源表竖向排列 | 默认按依赖图 rank 自动布局 | 包内 `left to right direction` + `-[hidden]-` 双重锁 |
| 标签 `<<xxx>>` 跑到图最底部 | PlantUML 把箭头绕到空间最大处 | 把详细标签写进便签，箭头只留 `..>` 无标签 |
| 类太多导致图超宽 | 单类字段过多 | 字段超过 20 个的类拆分为 `Page[T]` + `Item` + `List` 三类，或省略重复字段 |
| 多层包嵌套空白多 | 包裹 `rectangle` 与 `package` 混用 | 全用 `package`，只在标题前加 `▌` 字符 |
| 第一行与第二行顺序颠倒 | 任意 `..>` 跨层依赖会被强制升序 | 只在便签里写组装说明，箭头只保留"本行"内的关系 |
| 一个类射出 4+ 箭头 | 一张图混入了多条链路 | 按 §3 约束拆图，每图只描述一条链路 |
| 模型层外出现额外 package | 数据流图混入了采集层/路由层包 | 只允许两个顶层包（§3），其他内容写便签或用类图概览 |
| 便签过长（20+ 行） | 便签塞入了 SQL/性能/错误处理 | 只保留组装关系 + 伪代码（§8.2），其余拆到 .md |

---

## 12. 参考实例

| 实例 | 路径 | 图型 |
| --- | --- | --- |
| StockPanel 查询数据流 | `StockInfo/03-panel-compose.puml` | 查询数据流（标准模板） |
| StockInfo 类图 | `StockInfo/01-class.puml` | 类图概览 |
| 修改记录 | `StockInfo/02-modification.md` | 设计演进文档 |

> 新建业务的数据流图时，按 §0 决策树选择图型，复制对应模板（§9.1 / §9.2 / §9.3），替换类名 / 字段 / 表名即可。
