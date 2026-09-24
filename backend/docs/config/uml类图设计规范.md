# UML 类图设计规范（数据流型）

> 适用于后端业务数据流 / 跨层调用的"以表为源、以层为路"的类图绘制。
> 本文档以 `StockInfo/03-panel-compose.puml` 为标准模板，所有后续类图均应参照。

---

## 1. 设计目标

一张类图同时回答三个问题：

| 问题 | 对应区域 |
| --- | --- |
| 数据从哪里来？ | 第二行：来源表（仅关键字段） |
| 数据走过哪些层？ | 第一行：4 个模型层（请求 → 仓储 → 领域 → 应用） |
| 业务如何组装数据？ | 左上角黄色便签（组装关系 + 服务流伪代码） |

> **一句话**：左行四层，右行四表，便签讲清"谁组装了谁、谁调用了谁"。

---

## 2. 总体布局（两行 + 一个便签）

```
┌────────────────────────────────────────────────────────────┐
│  ╔═══════════════════╗                                     │
│  ║ 黄色便签 N_src    ║   ┐ 装配关系 + 服务流伪代码           │
│  ║ (组装 + 调用)     ║   ┘                                    │
│  ╚═══════════════════╝                                     │
│                                                            │
│  ╔═══ 模型层 ══════════════════════════════════════════╗   │
│  ║ [① 请求层] → [② 仓储层] → [③ 领域层] → [④ 应用层]  ║   │ ← 第一行（横向）
│  ╚═════════════════════════════════════════════════════╝   │
│           │           │           │           │           │
│           ↓ 虚线（聚合 / 组合 / 最新一行 / 最新一期）      │
│  ╔═══ 来源表 ══════════════════════════════════════════╗   │
│  ║ [T1] → [T2] → [T3] → [T4]                          ║   │ ← 第二行（横向）
│  ╚═════════════════════════════════════════════════════╝   │
└────────────────────────────────────────────────────────────┘
```

- **第一行**：模型层（4 个子 package），从左到右线性。
- **第二行**：来源表（≥ 1 张物理表），从左到右排列。
- **左下/上便签**：说明领域对象如何由来源表组装，并附带 1 段服务层伪代码。

---

## 3. 命名与标识规范

### 3.1 类 Stereotype（必须）

| Stereotype | 含义 | 示例 |
| --- | --- | --- |
| `<<NEW>>` | 本次新引入的类 | `<<NEW>>` |
| `<<Protocol>>` | 领域层接口契约（Python `Protocol`） | `<<Protocol, NEW>>` |
| `<<frozen>>` | 不可变值对象（`@dataclass(frozen=True)`） | `<<值对象, NEW, frozen>>` |
| `<<Generic>>` | 泛型类（如 `Page[T]`） | `<<Generic, NEW>>` |
| 无标记 | 复用既有类 | — |

> 多个 stereotype 用逗号分隔：`<<Protocol, NEW>>`。

### 3.2 类名 / 别名

- **领域层值对象**：首字母大写，名词化（`StockPanelRow`）。
- **请求 / VO / 仓储 Protocol**：以层名结尾（`QueryRequest`、`ItemVO`、`ListVO`、`Repository`）。
- **物理表**：用双引号小写蛇形命名（`"stock_infos"`），并用 `as T1, T2, …` 取短别名。

### 3.3 字段写法

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
- **计算字段**用分隔线 `----` + 注释说明公式，例如：

```puml
+ n_income
+ revenue
----
+ profit_margin    ' = n_income / revenue × 100
```

---

## 4. 颜色与皮肤

```puml
skinparam linetype ortho           ' 直线（避免曲线干扰阅读）
skinparam classAttributeIconSize 0 ' 关闭字段图标
skinparam classFontSize 11
skinparam packageFontSize 13
```

| 元素 | 背景色 | 用途 |
| --- | --- | --- |
| 来源表 | `#E0E0E0` 浅灰 | 与领域层模型区分，强调"非内存对象" |
| 模型层、便签 | 默认 | — |
| 私有/内部类 | `#LightYellow` 等自定义 | 可选 |

---

## 5. 布局指令（关键）

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

## 6. 箭头与关系

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

## 7. 便签使用规范

每个数据流图**最多 2 个便签**：

1. **左上 / 右下 黄底便签 `N_src`**：写"领域对象 ⇢ 来源表"的组装关系 + 服务层伪代码。
2. **类内 `note bottom of ...`**：仅用于 1~2 行的简短注释（如"前端 → 后端"、"4 表 JOIN + 聚合的投影"）。

便签内 Markdown：

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
  ③ StockPanelListVO.from_list_to_page(items, total,
       req.pageNum, req.pageSize) → StockPanelListVO
end note
```

便签内支持的标签：`<b>`、`•` 圆点、`────` 分隔线、`①②③` 编号、`→` 箭头、`...` 占位符。

---

## 8. 复用模板（直接复制）

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

' ── 第二行：来源表 ──────────────────────────────
package "▌ 来源表" {
  left to right direction
  T1 -[hidden]- T2 -[hidden]- T3 -[hidden]- T4

  class "<table_a>" as T1 #E0E0E0 { ... }
  class "<table_b>" as T2 #E0E0E0 { ... }
  class "<table_c>" as T3 #E0E0E0 { ... }
  class "<table_d>" as T4 #E0E0E0 { ... }
}

' ── 线性依赖 ────────────────────────────────────
<Name>QueryRequest --> <Name>Repository
<Name>Repository   ..> <Name>Row : <<产出>>
<Name>Row          --> <Name>ItemVO : <<1:1 字段映射>>

<Name>Row ..> T1
<Name>Row ..> T2
<Name>Row ..> T3
<Name>Row ..> T4

' ── 关系便签 ────────────────────────────────────
note as N_src
  <b><Name>Row 由 N 张表组装：</b>
  • ...
  ────────────────
  <b><Name>AppService.<method>(req)</b>
  ① ...
end note

@enduml
```

---

## 9. 渲染与命名约定

| 项 | 约定 |
| --- | --- |
| 文件命名 | `<NN>-<topic>.puml`（编号 + 主题） |
| 输出 PNG | 与 `.puml` 同目录、同名 `<topic>.png` |
| 渲染命令 | `plantuml -tpng <file>.puml` 或 `java -jar plantuml.jar -tpng <file>.puml` |
| `title` | 写"业务 + 数据流类型"，例如 `StockPanel 列表数据流 — 四层 + 来源表` |

---

## 10. 常见坑位（必读）

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| 来源表竖向排列 | 默认按依赖图 rank 自动布局 | 包内 `left to right direction` + `-[hidden]-` 双重锁 |
| 标签 `<<xxx>>` 跑到图最底部 | PlantUML 把箭头绕到空间最大处 | 把详细标签写进便签，箭头只留 `..>` 无标签 |
| 类太多导致图超宽 | 单类字段过多 | 字段超过 20 个的类拆分为 `Page[T]` + `Item` + `List` 三类，或省略重复字段 |
| 多层包嵌套空白多 | 包裹 `rectangle` 与 `package` 混用 | 全用 `package`，只在标题前加 `▌` 字符 |
| 第一行与第二行顺序颠倒 | 任意 `..>` 跨层依赖会被强制升序 | 只在便签里写组装说明，箭头只保留"本行"内的关系 |

---

## 11. 参考实例

| 实例 | 路径 | 用途 |
| --- | --- | --- |
| StockPanel 数据流 | `backend/docs/PlantUML/StockInfo/03-panel-compose.puml` | 标准模板 |
| StockInfo 类图 | `backend/docs/PlantUML/StockInfo/01-class.puml` | 单层领域类图参考 |
| 修改记录 | `backend/docs/PlantUML/StockInfo/02-modification.md` | 设计演进过程 |

> 新建业务的数据流类图时，请把 `03-panel-compose.puml` 复制为目标文件，按 §8 模板替换类名 / 字段 / 表名即可。
