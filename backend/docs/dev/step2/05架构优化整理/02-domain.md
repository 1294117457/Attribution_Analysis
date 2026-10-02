# domain/ 领域层分析

> 关联：[`00-总览与建议清单.md`](00-总览与建议清单.md) · [`../config/DDD.md` §2.1](../../config/DDD.md)

---

## 1. 当前文件清单（共 78 个）

```
backend/src/domain/
├── __init__.py
├── base.py                     ← 领域基类（Entity / AggregateRoot / ValueObject / DomainError / DomainEvent）
├── repository.py               ← BaseSymboledDatedRepository 通用仓储协议
├── market/                     ← 跨聚合根领域服务（交易时段、缓存 TTL）
│   ├── __init__.py
│   └── market_session.py       ← MarketSessionService / is_trading_time / ttl_for / market_now
├── concept/
│   └── collection_policy.py      ← ConceptCollectionPolicy（采集保护策略）
├── service/                    ← 跨聚合根领域服务（指标 / 信号 / 概念摘要）
│   ├── __init__.py
│   ├── concept_brief_service.py
│   ├── indicator_calculator.py
│   └── signal_detector.py
└── entitys/                    ← 22 个聚合根（按业务对象一字排开）
    ├── stock_info/             {entity, repository, vo}
    ├── stock_pool/             {entity, repository, vo}
    ├── kline/                  {entity, repository, vo, service}
    │                              └── service/_legacy_init.py   ← 旧占位
    ├── panel/                   {repo, vo}                  ← 无 entity（值对象即核心）
    ├── concept/                {entity, repository, vo}
    ├── fin_report/             {entity, repository}
    ├── fin_daily_basic/        {entity, repository}
    ├── fin_top10_float/        {entity, repository}
    ├── fin_top10_holders/      {entity, repository}
    ├── base_adj_factor/        {entity, repository}
    ├── base_dividend/          {entity, repository}
    ├── base_name_change/       {entity, repository}
    ├── base_suspend/           {entity, repository}
    ├── cap_block_trade/        {entity, repository}
    ├── cap_holder_num/         {entity, repository}
    ├── cap_margin/             {entity, repository}
    ├── cap_margin_detail/      {entity, repository}
    ├── cap_moneyflow/          {entity, repository}
    ├── cap_top_inst/           {entity, repository}
    ├── cap_top_list/           {entity, repository}
    ├── mkt_calendar/           {entity, repository}
    ├── mkt_index_member/       {entity, repository}
    ├── mkt_market_daily/       {entity, repository}
    └── mkt_sector_daily/       {entity, repository}
```

---

## 2. 质量评估（**严格符合 DDD §2.1**）

### 2.1 已做到的

✅ **零外部依赖**：domain 层只允许 `dataclasses`、`enum`、`datetime`、`typing`、`zoneinfo`、`re`、项目内子包。

✅ **聚合根有身份与生命周期**：`Kline`、`StockInfo`、`StockPool`、`Concept` 均继承 `AggregateRoot`，支持 `add_event()`、`clear_events()`。

✅ **值对象不可变**：`PoolType`、`PoolColor`、`PoolMember`、`Industry`、`Market`、`ConceptBriefVO`、`ConceptMainVO`、`StockPanelRow` 等都 `@dataclass(frozen=True)`。

✅ **仓储接口在 domain**：`StockPoolRepository`、`ConceptRepository`、`KlineRepository`、`StockPanelComposeRepository` 都是 `Protocol`。

✅ **跨聚合根服务抽到 `domain/service/`**：
- `IndicatorCalculator`：纯算法（MA/EMA/MACD/RSI/KDJ/BOLL）
- `SignalDetector`：基于 Kline 列表生成形态摘要
- `ConceptBriefService`：按 concept_type 业务优先级排序

✅ **领域规则独立**：交易时段规则（`market_session.py`）、采集保护策略（`collection_policy.py`）可独立单测。

### 2.2 偏差

⚠️ **多数 entity 不继承 AggregateRoot**：13 个 `cap_*`/`fin_top10_*`/`mkt_*`/`base_*` 是简单 `@dataclass`，未继承 `AggregateRoot`。

- 这是务实选择：这些 entity **没有跨字段的不变式 / 行为**，只是数据载体；强行继承会引入空方法 + 字段顺序问题。
- **建议**：保持现状，仅在文件头加一行说明"该 entity 是 SymboledDatedEntity 子类，纯数据"。

⚠️ **`Entity.__eq__` 与 dataclass 冲突**：

```python
# base.py
class Entity(ABC):
    def __eq__(self, other):
        return self.id == other.id
```

但多数 entity 用 `@dataclass`，dataclass 会自动生成 `__eq__` 覆盖父类。**实际效果**：`Kline`、`StockPool` 等按 dataclass 比全字段，不按 id。这与 DDD "实体的相等性基于身份"不符。

**建议**：让所有 entity 显式重写 `__eq__` / `__hash__`（或在 `base.py` 提供 mixin），或删掉 `Entity.__eq__`（承认 dataclass 默认行为）。

⚠️ **`pool_operation_repository.py` 在 panel 出现后应回归**：从 git 看，`pool_operation_repository.py` 已迁移到 `infrastructure/persistence/repositories/`。确认 `domain/entitys/stock_pool/repository.py:1-6` 注释"已迁移至 domain panel"对吗？）— 应扫一下自己"已在 panel 与 infrastructure 层"。

---

## 3. entity 子目录膨胀问题（22 个文件）

### 3.1 现状

13 个 entity (`cap_*`/`fin_top10_*`/`mkt_*`/`base_*`) 没有任何 service 调用它们，只是**给采集任务存数据用的"表映射"**：

- `infrastructure/persistence/models/` 对应有同名 ORM 类
- `infrastructure/persistence/repositories/` 有同名 `RepoImpl`
- 路由层、AppService 都没有引用这些 entity

### 3.2 三个方案对比

| 方案 | 描述 | 优点 | 缺点 |
|---|---|---|---|
| **方案 X：保持现状** | 22 个 entity 文件一字排开 | 命名直观、对齐 ORM | 文件多 |
| **方案 X：抽到 `entitys/datalink/`** | 13 个 entity 移入子目录 | 子目录数量减少 | entity 在 domain 里"分散" |
| **方案 X：删除** | entity 直接由 ORM 层使用 entity | 文件减半 | 违反 DDD §2.1 |

**推荐：方案 X（保持现状）**。理由：
- 这些 entity 仍归 domain（数据契约与业务字段），未来真要做归属分析（capital flow / holders）时再自然变成"被业务调用的 entity"。
- `domain/entitys/{name}/{name}.py` 的 1:1 对齐是 DDD 战术模式最常见的导航结构，重组收益小。

---

## 4. `domain/entitys/panel/`（面板组合）

### 4.1 当前结构

```
panel/
├── vo.py         StockPanelRow (frozen, 16 个字段)
└── repository.py StockPanelComposeRepository (Protocol)
```

**没有 entity.py**——这是个纯"视图聚合"，4 表 JOIN 产生 `StockPanelRow`，不写回任何源表。

### 4.2 评价

✅ **抽象定位准确**：`StockPanelComposeRepository` 同时持有 `list_paginated`、`list_membership_by_symbols`、`list_concepts_by_symbols`——把"列表面板"的"3 条 SQL"封装在单一仓储，让 `PanelAppService` 不跨仓储编排。

✅ **不与任何单表 CRUD 冲突**：不污染 `StockPoolRepository` 的"列表成员"——后者已经被注释"已迁移至 panel"。

### 4.3 微小调整建议

- 给 `vo.py` 加一行说明"panel 是 scope（bounded context）而非 entity"——避免新人误以为 panel 缺 entity 是 bug。

---

## 5. `domain/service/`（跨聚合根服务）

| Service | 输入 | 输出 | 是否纯 | 依赖 |
|---|---|---|---|---|
| `IndicatorCalculator` | `pd.DataFrame(close/high/low)` | 17 列指标 DataFrame | ✅ 纯（pandas 算） | pandas |
| `SignalDetector` | `Kline[]` | `TechnicalSummary` | ✅ 纯 | 无 |
| `ConceptBriefService` | `dict[symbol, ConceptBriefVO[]]` | `dict[symbol, (main, n)]` | ✅ 纯 | 无 |

✅ 完全符合 DDD §3.2。可独立单测。

---

## 6. `domain/market/` 与 `domain/concept/`

这两个**单文件子包**是"跨聚合根的业务规则"——纯函数 + 枚举，业务知识封装在 domain 层：

- `market/market_session.py`：交易时段定义、TTL 缓存策略
- `concept/collection_policy.py`：成分股缩量保护、清单缩量保护

✅ 是 DDD §3.2 "领域服务"的教科书范例。

---

## 7. 推荐改造清单

### 7.1 必须做

| 编号 | 动作 | 工作量 |
|---|---|---|
| D1 | `domain/entitys/panel/vo.py:1-7` 加一行说明 panel 是视图 scope，不是 entity | 2 min |
| D2 | `domain/base.py` 的 `Entity.__eq__` 在头注释加一段警告（"dataclass 子类默认按字段比较；如需 id 等值请显式重写"） | 5 min |
| D3 | `domain/kline/service/_legacy_init.py` 若已 0 引用则删除（git status 仍标 `??`） | 1 min |
| D4 | `domain/entitys/stock_pool/repository.py:1-6` 注释里"已迁移至 domain panel"——若实际是 `infrastructure/persistence/repositories/panel_compose_repository.py`，改注释 | 5 min |

### 7.2 建议做（结构性）

| 编号 | 动作 | 工作量 |
|---|---|---|
| D5 | 13 个 cap_*/fin_top10_*/mkt_*/base_* entity 文件头加一行"该 entity 是 SymboledDatedEntity 子类，纯数据；业务层未引用，预留归属分析" | 30 min |
| D6 | 给 `repository.py:5` 注释加一行"BaseSymboledDatedRepository 已用于 KlineRepository/StockInfoRepository 的简化模板" | 2 min |

### 7.3 暂缓（高成本、低收益）

| 编号 | 动作 | 原因 |
|---|---|---|
| D7 | 把所有 entity 改成继承 `AggregateRoot` | 多数 entity 没有事件/行为；强行引入徒增代码 |
| D8 | 把 13 个 entity 抽到 `entitys/datalink/` | 命名收益小，路由表不变 |

---

## 8. 一句话总结

**Domain 层是整个项目最稳定、最符合规范的部分**——零外部依赖、聚合根清晰、领域服务纯函数、跨聚合根聚合单视图独占规则。**唯一明显的退化是 `Entity.__eq__` 与 dataclass 字段比较的隐性偏差——建议通过注释 + 实际影响评估后决定是否动**。**剩下的是 5-10 处过期/缺失注释的文档清扫**。