# 04 通用任务与 Port 目录 — `DynamicPort` / `PortCatalog` / `DynamicCollectTask`

> 阶段 D3。14 个 `XxxCollectTask` 类 + 14 个 `XxxPort` 类**整体替换**为动态版本。
>
> ⚠️ **本节按 5 个面设计**：`tech` / `capital` / `fundamental` / `news` / `sentiment`。
> `DynamicPort.facet` 字段 = `sys_data_ports.facet` 字段值（不带下划线）。
> 表名短前缀（`capital_` 等）见 [`10-分库与表结构.md`](10-分库与表结构.md)。

## 1. 现状 vs 目标

### 1.1 现状（step5）

```python
# contexts/data/application/port/capital.py
class MoneyflowPort(DataPort):
    name = "cap_moneyflow"
    label = "资金流向"
    source = "tushare"
    unit = "trade_date"
    class Item(DataPort.Item):
        ts_code: str
        trade_date: date
        ...

# contexts/collect/application/collect/tasks/tushare.py
class CapMoneyflowCollectTask(_TradeDateTask):
    name = "cap_moneyflow"
    port = MoneyflowPort
    sort_order = 10
```

每个 port 写 3 处：Port 元数据类、BO Item、Task 类。

### 1.2 目标

```python
# 启动时一次性装配
ports: list[DynamicPort] = PortCatalog.load_from_db(raw_engine)   # 14 条
tasks: list[DynamicCollectTask] = [DynamicCollectTask.for_port(p) for p in ports]
```

`XxxPort` / `XxxCollectTask` 14 对类**整体删除**。

---

## 2. `PortCatalog`

```python
# contexts/data/application/port/catalog.py

@dataclass(frozen=True)
class PortSpec:
    """Port 配置（启动期装配，运行时只读）；无出参——出参由采集时选表决定"""
    name:           str
    label:          str
    source:         str           # "tushare" / "adata"
    unit:           str           # "trade_date" | "symbol" | "all"
    kind:           str           # "batch" | "realtime"
    facet:          str           # ★ 5 个面："tech" | "capital" | "fundamental" | "news" | "sentiment"
    params_schema:  dict         # 入参 JSON Schema（不变）
    upsert_mode:    str           # "by_unique" | "on_conflict_do_nothing" | "insert_only"


class PortCatalog:
    """单例；启动时 load_from_db() 一次；运行时只读"""

    _specs: ClassVar[dict[str, PortSpec]] = {}

    @classmethod
    async def load(cls, engine: AsyncEngine) -> None:
        """SELECT * FROM sys_data_ports → 装配到 _specs"""
        async with engine.begin() as conn:
            rows = await conn.execute(text("SELECT * FROM sys_data_ports"))
            for r in rows:
                spec = PortSpec(
                    name=r.name,
                    label=r.label,
                    source=r.source,
                    unit=r.unit,
                    kind=r.kind,
                    facet=r.facet,             # ★ 5 个面
                    params_schema=r.params_schema,
                    upsert_mode=r.upsert_mode,
                )
                cls._specs[spec.name] = spec

    @classmethod
    def get(cls, name: str) -> PortSpec:
        if name not in cls._specs:
            raise KeyError(f"port `{name}` not found in sys_data_ports")
        return cls._specs[name]

    @classmethod
    def all(cls) -> list[PortSpec]:
        return list(cls._specs.values())

    @classmethod
    def by_facet(cls, facet: str) -> list[PortSpec]:
        """前端按面分组用：capital 面的所有 port"""
        return [s for s in cls._specs.values() if s.facet == facet]
```

**启动时无 DDL 校验**——没有 `output_schema`，表存在性在采集时校验。

### 2.1 启动位置

```python
# main.py 或 di.py
await PortCatalog.load(engine)   # 应用启动时调用一次
```

> engine 是**业务库** engine（sys_data_ports 在 `attribution_db`）。

---

## 3. `DynamicPort`（无出参）

```python
# contexts/data/application/port/dynamic.py

class DynamicPort:
    """运行时从 PortSpec 装配的 Port；只定义入参，出参由采集时选表决定"""

    def __init__(self, spec: PortSpec):
        self._spec = spec

    @property
    def name(self) -> str:          return self._spec.name
    @property
    def label(self) -> str:         return self._spec.label
    @property
    def source(self) -> str:        return self._spec.source
    @property
    def unit(self) -> str:          return self._spec.unit
    @property
    def kind(self) -> str:          return self._spec.kind
    @property
    def facet(self) -> str:         return self._spec.facet     # ★ 5 个面
    @property
    def upsert_mode(self) -> str:   return self._spec.upsert_mode

    @property
    def params_schema(self) -> dict:
        return self._spec.params_schema   # 入参校验用

    def validate_params(self, raw_params: dict) -> dict:
        """jsonschema.Draft7Validator 校验入参"""
        validator = Draft7Validator(self._spec.params_schema)
        errors = list(validator.iter_errors(raw_params))
        if errors:
            raise ValidationError(errors)
        return raw_params

    def build_adapter_params(self, unit: str, raw_params: dict) -> dict:
        """把入参整理成 adapter.fetch() 调用参数"""
        params = dict(raw_params)
        if self._spec.unit in ("trade_date", "symbol"):
            params[self._spec.unit] = unit
        return params
```

**注意**：`DynamicPort` **没有** `Item` / `output_schema` 属性。出参在采集时由用户所选表决定，不在 port 定义里。

---

## 4. `DynamicCollectTask`

```python
# contexts/collect/application/collect/dynamic_task.py

class DynamicCollectTask(DeclarativeCollectTask):
    """通用任务：元数据来自 DynamicPort；不再每个数据源写一个类"""

    def __init__(self, port: DynamicPort, adapter: DataSourceAdapter,
                 raw_store: DynamicRawDataStore):
        self._port      = port
        self._adapter   = adapter
        self._raw_store = raw_store

        # DeclarativeCollectTask 需要的属性
        self.name = port.name
        self.label = port.label
        self.unit_word = (
            "交易日" if port.unit == "trade_date"
            else "股票" if port.unit == "symbol"
            else "单元"
        )
        self.empty_word = "无数据"
        self.sort_order = 0

    @classmethod
    def for_port(cls, port: DynamicPort, adapter: DataSourceAdapter,
                 raw_store: DynamicRawDataStore) -> "DynamicCollectTask":
        return cls(port, adapter, raw_store)

    async def _do_collect(self, unit: str, params: dict) -> list[dict]:
        """
        采集入口（替代原来的 DeclarativeCollectTask.collect_one）：
        1. 校验入参
        2. 调用 adapter.fetch()
        3. 字段映射（adapter 输出列名 → 目标表列名）
        4. 入库（raw_store.save()）
        """
        validated = self._port.validate_params(params)
        adapter_params = self._port.build_adapter_params(unit, validated)

        rows = await self._adapter.fetch(self._port.name, adapter_params)
        if not rows:
            return []

        # 字段映射：adapter 返回的 dict 键名就是目标表列名
        # （adapter 已在 fetch() 里做了列名对齐）
        return rows
```

`DeclarativeCollectTask` 的 `collect_one` / `existing_units` / `summary_message` **不改**；`DynamicCollectTask` 只覆写 `_do_collect`。

### 4.1 `all_collect_tasks` 装配

```python
# contexts/collect/application/collect/tasks/__init__.py（修改）
def all_collect_tasks() -> list[BaseCollectTask]:
    if not PortCatalog._specs:
        raise RuntimeError("PortCatalog not loaded; call await PortCatalog.load(engine) first")

    # Tushare / Adata adapter（单例）
    tushare_adapter = TushareAdapter()
    adata_adapter   = AdataAdapter()

    # DynamicRawDataStore（单例，注入 raw_engine）
    raw_store = DynamicRawDataStore(raw_engine, tushare_adapter)

    dynamic = [
        DynamicCollectTask.for_port(
            DynamicPort(PortCatalog.get(p.name)),
            tushare_adapter if p.source == "tushare" else adata_adapter,
            raw_store,
        )
        for p in PortCatalog.all()
        if p.kind == "batch"
    ]

    return [
        *dynamic,
        DailyKlineCollectTask(),   # 日 K：业务仓储，不走 raw（走 tech_kline_daily）
        StockBasicCollectTask(),    # 股票清单：业务仓储（走 fundamental_stock_info）
        *all_concept_tasks(),       # 概念 5 个：走 ConceptStorePort（走 fundamental_concept*）
        *all_planned_tasks(),
    ]
```

---

## 5. 采集请求的 `table_name` 怎么来

`DynamicCollectTask._do_collect` 的 `params` 里由上层（`CollectRunner`）注入 `table_name`：

```python
# CollectRunner 改造：run() 收 table_name 参数
async def run(self, task_name: str, params: dict, table_name: str, ...) -> TaskResult:
    task = self._get_task(task_name)
    result = await task.execute(
        units=[...],
        params=params,
        extra={"table_name": table_name},   # ★ 注入
    )
    return result
```

`DynamicCollectTask._do_collect` 从 `extra["table_name"]` 取表名，调用 `raw_store.save(port_name, table_name, rows)`。

> **双库下的 table_name 解析**：表名不带 schema 前缀（`capital_moneyflow`，不是 `raw_data_db.capital_moneyflow`）。`DynamicRawDataStore` 注入的是 `raw_engine`，所以表名自动解析到 `raw_data_db`。

---

## 6. 兼容性：旧 `XxxCollectTask` 路径保留到 D5

D3 阶段 `all_collect_tasks()` 返回动态版本，但旧 task 类文件仍然存在（用于回滚）。D5 才真正删除。

---

## 7. 验收（D3）

- [ ] `all_collect_tasks()` 列表顺序与 step5 §8 验收清单一致
- [ ] `/collect/catalog` 输出只含 port 入参元数据（无出参字段），**每个 port 包含 `facet` 字段**
- [ ] 前端按 `facet` 分组展示 port（5 个组：tech / capital / fundamental / news / sentiment）
- [ ] 前端提交 `moneyflow` 采集（选表 `capital_moneyflow`）：进度、取消、重跑、方案执行正常
- [ ] `PortCatalog.get("non_existed")` 抛 `KeyError`
- [ ] 故意传不存在的表名 → `resolve_table_schema` 抛错，任务 fail
- [ ] 故意选缺位列的表 → 字段校验失败，任务 fail

---

## 8. 不影响

- `ConceptStorePort` 概念 5 个任务：不动（仍写 `fundamental_concept*`）
- `StockUniversePort` / 日 K / 股票清单：不动
- `CollectRunner` / `CollectManageService`：不动（接口稳定）
- `DataGateway.fetch(port, params)`：不动（`DynamicPort` 兼容 `DataPort` 协议）

---

## 9. 5 个面的 port 清单

D3 阶段已经装入 `sys_data_ports` 的 14 个 port 在 5 个面下的分布：

| facet | port name | 写表 |
|:--|:--|:--|
| `tech`        | `adj_factor`    | `tech_adj_factor` |
| `tech`        | `name_change`   | `tech_name_change` |
| `tech`        | `suspend`       | `tech_suspend` |
| `capital`     | `moneyflow`     | `capital_moneyflow` |
| `capital`     | `margin_detail` | `capital_margin_detail` |
| `capital`     | `margin`        | `capital_margin` |
| `capital`     | `top_list`      | `capital_top_list` |
| `capital`     | `top_inst`      | `capital_top_inst` |
| `capital`     | `block_trade`   | `capital_block_trade` |
| `capital`     | `holder_number` | `capital_holder_num` |
| `fundamental` | `daily_basic`   | `fundamental_daily_basic` |
| `fundamental` | `fin_income`    | `fundamental_report` |
| `fundamental` | `top10_holders` | `fundamental_top10` |
| `fundamental` | `top10_floatholders` | `fundamental_top10_float` |
| `fundamental` | `dividend`      | `fundamental_dividend` |

> **`news_` / `sentiment_` 暂无 port**——D3 阶段没有 news / sentiment 面的 port。
> `PortCatalog.by_facet("news")` 和 `by_facet("sentiment")` 返回空列表，**前端两个分组为空属正常**。
