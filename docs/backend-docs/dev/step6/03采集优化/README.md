# 03 采集优化（配置化）— 表是事实来源，采集时选表

> 前置：[step5/03collect优化](../step5/03collect优化/README.md) 全部完成。
> 本文是 step6 阶段方案，**尚未修改代码**。
>
> ⚠️ **当前文档与代码差异**：本目录的 02-06 / 09 描述的是 step6 中间态方案（4 个 facet、raw_ 前缀、单库、MySQL 风格）。**最终决策以 [`10-分库与表结构.md`](10-分库与表结构.md) 为准**：
> - **5 个面**：tech / capital / fundamental / news / sentiment
> - **短前缀**：`capital_moneyflow`（无 `raw_`）
> - **双库**：`attribution_db`（业务库 11 张）+ `raw_data_db`（采集库 27 张）
> - **PostgreSQL**：已确认是 PostgreSQL
>
> 本文先按 step6 中间态思路（INFORMATION_SCHEMA / 选表 / 试运行）讲清楚；表名 / 库名 / facet 的最终落地以 `10-分库与表结构.md` 为准。

## 0. 一句话总结

**表是事实来源**。运维先建好表；采集时用户选目标表；系统反查 `INFORMATION_SCHEMA` 得出参；入库前先试运行。不需要 `output_schema` 配置，不需要 seed 字段定义。

| 阶段 | 加一个新 Port 要写什么 |
| :-- | :-- |
| step5 之前 | Port + BO + ORM 模型 + Repo + Task + `_SPECS` 注册 = 5 文件 + 1 行 |
| step5 之后 | Port + ORM 模型 + Repo + Task + `_SPECS` 注册 = 4 文件 + 1 行 |
| **本文（step6）** | **1 张表 + 1 条 `sys_data_ports` INSERT（仅入参配置）** |

`source`（adata / tushare / pytdx）适配层是**唯一**仍按数据源写死的代码；Port 声明、任务逻辑、入库全部走通用实现。

---

## 1. 现状与目标

### 1.1 现状（step5 之后）

```
sys_data_ports（只配入参）
  ├─ name: "capital_moneyflow"        ← 注意：旧名 cap_moneyflow，10-分库 改成 capital_moneyflow
  ├─ source: "tushare"
  └─ params_schema: {trade_date}

CapitalMoneyflowPort（出参 schema）    ← 写死在代码
CapitalMoneyflowDB（表结构）          ← 写死在代码
CapitalMoneyflowRepoImpl（写入逻辑）  ← 写死在代码
_SPECS["capital_moneyflow"]（映射）   ← 写死在代码
MoneyflowCollectTask（任务声明）      ← 写死在代码
```

每一行「← 写死在代码」都是新增数据源时的负担。

### 1.2 目标

```
用户操作：
  1. 选 port（哪个数据源，如 "capital_moneyflow"）
  2. 选目标表（前端从 INFORMATION_SCHEMA.TABLES 拉已有表列表）
  3. 填入参（trade_date 等）
  4. 提交采集

后端流程：
  ┌─ 前置校验
  │   查 INFORMATION_SCHEMA：表存在 / 主键 / 列名
  │   第三方返回字段 ⊆ 表列 → 通过
  │   第三方返回字段 ⊄ 表列 → 抛错返回前端
  │
  ├─ 试运行（dry_run）
  │   只入库 1 行 → 成功才继续
  │   失败 → 抛错返回前端（不污染表）
  │
  └─ 正式入库
      INSERT ... ON CONFLICT ... DO UPDATE    -- PostgreSQL 语法
```

### 1.3 关键设计原则

| 原则 | 说明 |
| :-- | :-- |
| **表是事实来源** | `INFORMATION_SCHEMA` 是唯一的出参定义，不存在 JSON 配置 |
| **灵活绑定** | port_name 只代表"取什么数据"，表由采集时选；同一表可被多 port 共用 |
| **试运行保底** | 入库前先写 1 行；失败抛错，不污染表 |
| **入库用 `text()` + bindparam** | 参数化绑定，无 SQL 注入风险 |
| **启动期无 DDL 校验** | 没有 `output_schema`，不校验；表结构以数据库为准 |
| **PostgreSQL** | ON CONFLICT / current_schema() 等语法；不用 MySQL 专属语法 |
| **双库物理隔离** | 业务对象 → `attribution_db`；采集 raw → `raw_data_db` |
| **5 个面** | tech / capital / fundamental / news / sentiment（news/sentiment 暂无 port） |

---

## 2. `sys_data_ports` 表（精简版）

> **删掉** `output_schema` / `table_config` / `output_schema_hash` 三个字段。

```sql
-- 迁移 D1：删字段
ALTER TABLE sys_data_ports
    DROP COLUMN IF EXISTS output_schema,
    DROP COLUMN IF EXISTS table_config,
    DROP COLUMN IF EXISTS output_schema_hash;

-- 最终结构
CREATE TABLE sys_data_ports (
    name           VARCHAR(64)  PRIMARY KEY,
    label          VARCHAR(128) NOT NULL,
    source         VARCHAR(32)  NOT NULL,   -- tushare / adata
    unit           VARCHAR(16)  NOT NULL,   -- trade_date / symbol
    kind           VARCHAR(16)  NOT NULL,   -- batch / realtime
    facet          VARCHAR(16)  NOT NULL,   -- tech / capital / fundamental / news / sentiment
    params_schema  JSON         NOT NULL,
    upsert_mode    VARCHAR(16)  NOT NULL DEFAULT 'by_unique'
        COMMENT 'by_unique | on_conflict_do_nothing | insert_only'
);
```

> **新增 `facet` 字段**：标识该 port 属于 5 个面中的哪一个。前端分组展示用。
> 5 个 facet 的取值为：`tech` / `capital` / `fundamental` / `news` / `sentiment`。
> 注意：**表前缀** = `capital_`（短前缀，无 `raw_`），**facet 字段值** = `capital`（不带下划线）。两者区分。

`upsert_mode`（沿用 step5 约定，PostgreSQL 语义）：

| 值 | 含义 | PostgreSQL 语法 |
| :-- | :-- | :-- |
| `by_unique`（默认） | 按主键覆盖非主键列 | `INSERT ... ON CONFLICT (pk) DO UPDATE SET ...` |
| `on_conflict_do_nothing` | 主键撞键直接跳过 | `INSERT ... ON CONFLICT (pk) DO NOTHING` |
| `insert_only` | 纯 INSERT，撞键报错 | `INSERT ...`（不写 ON CONFLICT） |

---

## 3. 采集流程（完整链路）

### 3.1 前端提交

```json
// POST /collect/run
{
    "port_name": "capital_moneyflow",
    "table_name": "capital_moneyflow",       // ★ 用户从表列表中选（注意：表名不带 raw_ 前缀）
    "params": {"trade_date": "20240101"}
}
```

### 3.2 后端处理流程

```
请求进来
  │
  ├─ 1. 查 sys_data_ports：port_name 存在？
  │     不存在 → 400 Bad Request
  │
  ├─ 2. 查 INFORMATION_SCHEMA：table_name 存在？有哪些列？主键是谁？
  │     表不存在 → 422 Unprocessable Entity（提示 CREATE TABLE）
  │
  ├─ 3. 调用 TushareAdapter / AdataAdapter.fetch(port_name, params)
  │     返回 list[dict]（字段名如 ts_code / trade_date / buy_sm_vol）
  │
  ├─ 4. 字段映射校验
  │     第三方返回列 ⊆ 表列 → 通过
  │     第三方返回列 ⊄ 表列 → 抛错返回前端（"表缺少列 X"）
  │
  ├─ 5. 试运行（dry_run）：只入库第一行
  │     成功 → 继续
  │     失败（类型不匹配等）→ 抛错返回前端（"试运行失败：..."）
  │     注意：试运行失败不回滚（因为没写成功任何行）
  │
  └─ 6. 正式入库：批量 executemany
        返回入库行数
```

### 3.3 链路图（step6 之后）

```
用户提交（选 port + 选表）
  │
  ▼
采集任务（DynamicCollectTask）
  │
  ▼
Adapter.fetch(port_name, params)          ← 第三方返回 dict
  │
  ▼
resolve_table_schema(table_name)          ← 查 INFORMATION_SCHEMA
  │  （注：PostgreSQL 用 current_schema() 代替 MySQL DATABASE()）
  │
  ▼
字段校验：第三方列 ⊆ 表列？              ← 不符合抛错
  │
  ├─ dry_run：入库 1 行
  │
  └─ 正式入库：INSERT ... ON CONFLICT (pk) DO UPDATE
              （text() SQL + bindparam）
```

---

## 4. 关键组件

### 4.1 `TableSchema`：采集时从数据库反查

```python
class TableSchema(NamedTuple):
    columns:     list[ColumnDef]   # 列名 / 类型 / 是否可空
    primary_key: list[str]          # 主键列（用于 upsert_mode=by_unique）

async def resolve_table_schema(
    engine: AsyncEngine, table_name: str
) -> TableSchema:
    """采集时从 INFORMATION_SCHEMA 反查表结构（PostgreSQL）"""
    async with engine.begin() as conn:
        cols = await conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = current_schema()
              AND TABLE_NAME = :t
            ORDER BY ORDINAL_POSITION
        """), {"t": table_name})
        pks = await conn.execute(text("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = current_schema()
              AND TABLE_NAME = :t
              AND CONSTRAINT_NAME = 'PRIMARY'
            ORDER BY ORDINAL_POSITION
        """), {"t": table_name})
    col_list = [dict(r._mapping) for r in cols]
    pk_list  = [r[0] for r in pks]
    if not col_list:
        raise PortSchemaMismatchError(...)
    return TableSchema(columns=col_list, primary_key=pk_list)
```

### 4.2 `DynamicRawDataStore.save`（入库核心）

```python
class DynamicRawDataStore(RawDataStorePort):
    async def save(
        self,
        port_name: str,
        table_name: str,
        params: dict,
    ) -> SaveResult:
        spec     = self._catalog[port_name]         # sys_data_ports 元数据
        schema   = await resolve_table_schema(self._engine, table_name)

        rows = await self._adapter.fetch(port_name, params)
        if not rows:
            return SaveResult(written=0, skipped=0)

        # 字段校验：第三方列 ⊆ 表列
        table_cols = {c["COLUMN_NAME"] for c in schema.columns}
        for row in rows:
            extra = set(row.keys()) - table_cols
            if extra:
                raise PortSchemaMismatchError(
                    port=port_name, table=table_name,
                    reason=f"表缺少以下列: {sorted(extra)}",
                )

        # 试运行：只写 1 行
        await self._upsert_one(self._engine, table_name, schema, spec.upsert_mode, [rows[0]])

        # 正式入库
        written = await self._upsert_batch(
            self._engine, table_name, schema, spec.upsert_mode, rows
        )
        return SaveResult(written=written, skipped=0)
```

### 4.3 通用 Port：`DynamicPort`（无出参定义）

```python
class DynamicPort:
    """运行时从 sys_data_ports 装配，只定义入参，不定义出参"""
    def __init__(self, row: dict):
        self.name  = row["name"]
        self.label = row["label"]
        self.source = row["source"]
        self.unit   = row["unit"]
        self.kind   = row["kind"]
        self.facet  = row["facet"]                # ★ 5 个面之一
        self.params_schema = row["params_schema"] # 入参 JSON Schema
        self.upsert_mode  = row["upsert_mode"]

    @property
    def item_schema(self) -> TableSchema:
        # 采集时由用户所选表决定，不在 port 定义里
        raise AttributeError("出参由采集时选表决定，port 不定义")
```

### 4.4 `PortCatalog`：启动时装配（无 DDL 校验）

```python
class PortCatalog:
    """启动时一次扫 sys_data_ports；采集时不校验 DDL"""
    def __init__(self, engine: AsyncEngine):
        self._engine = engine
        self._ports: dict[str, DynamicPort] = {}

    async def load(self) -> None:
        async with self._engine.begin() as conn:
            rows = await conn.execute(text("SELECT * FROM sys_data_ports"))
            for r in rows:
                self._ports[r.name] = DynamicPort(dict(r._mapping))

    def get(self, name: str) -> DynamicPort:
        return self._ports[name]   # KeyError → 400

    def list_ports(self) -> list[DynamicPort]:
        return list(self._ports.values())
```

### 4.5 数据源适配层

```python
class DataSourceAdapter(Protocol):
    name: str
    async def fetch(self, port_name: str, params: dict) -> list[dict]: ...

class TushareAdapter:
    name = "tushare"
    async def fetch(self, port_name: str, params: dict) -> list[dict]:
        # 按 port_name 走 tushare_tasks 里的 fetch 逻辑
        # 返回 dict 列表，字段名对齐到表的 snake_case 列名
        ...

class AdataAdapter:
    name = "adata"
    async def fetch(self, port_name: str, params: dict) -> list[dict]:
        # 做 adata → tushare 字段名映射（用 _ALIAS 常量）
        ...
```

---

## 5. 一次性迁移，**不双轨**

| 旧对象 | 去留 |
| :-- | :-- |
| `MoneyflowPort` 等 14 个 Port 类 | 删除 |
| `MoneyflowItem` 等 14 个 BO | 删除 |
| `XxxDB` 14 张表模型 | 删除 |
| `XxxRepoImpl` 14 个仓储 | 删除 |
| `SqlRawDataStore._SPECS` | 删除 |
| `DailyBasicCollectTask` 等 14 个 Task | 删除 |
| `output_schema` / `table_config` 字段 | 删除 |
| 旧 `capital_moneyflow` 等 14 张表数据 | **迁移到新表**（按 `10-分库与表结构.md` 的 27 张表 RENAME） |

详细迁移见 [05-迁移与数据回填](05-迁移与数据回填.md)。

---

## 6. 兼容性约束（对外不变）

| 项 | 约束 |
| :-- | :-- |
| `task_type` 名称 | 14 个原 `task_type` 全部保留 |
| `/collect/catalog` 输出 | 只输出 port 元数据（无出参字段），**新增 `facet` 字段**用于前端分组 |
| `/collect/tables` 输出 | 新增端点：从 `INFORMATION_SCHEMA.TABLES` 拉表名列表供前端展示 |
| `sys_collect_jobs` 表 / Redis `collect:progress:{task_id}` | 不变 |
| `UnitResult.data` / 汇总文案 | 不变 |
| 路由接口 | `/collect/run` 多一个 `table_name` 参数 |
| 前端 | 采集表单加"选择目标表"下拉框（从 `/collect/tables` 取） |

> **表名变更说明**：原 `task_type`（如 `cap_moneyflow`）保留，但**实际写入的表**改成新名（`capital_moneyflow`）。这是通过 `sys_data_ports` 里的 `name` 字段保持原值、表名通过 `/collect/run` 的 `table_name` 参数显式传入实现的——`task_type` 与表名**不再绑定**。

---

## 7. 关于读侧（`data_board.py`）

读侧与写侧完全解耦。读侧不需要知道 port_name，只知道表名：

```python
# 改前：select(CapMoneyflowDB).where(...)
# 改后：text("SELECT * FROM capital_moneyflow WHERE trade_date = :d").bindparams(d=...)
```

表名从运维的 `tech_` / `capital_` / `fundamental_` / `news_` / `sentiment_` 规范中取。具体迁移见 [03-动态表与入库 §5](03-动态表与入库.md)。

---

## 8. 文档目录

| 文档 | 内容 | 状态 |
| :-- | :-- | :-- |
| [02-配置表升级](02-配置表升级.md) | `sys_data_ports` 字段精简：删 output_schema/table_config，**新增 facet** | 待对齐 10-分库 |
| [03-动态表与入库](03-动态表与入库.md) | 采集时反查表结构 + 试运行 + 动态 SQL upsert | 待对齐 PostgreSQL + 短前缀 |
| [04-通用任务与Port目录](04-通用任务与Port目录.md) | `DynamicPort`（无出参）/ `PortCatalog` / `DynamicCollectTask` | 待对齐 5 面 |
| [05-迁移与数据回填](05-迁移与数据回填.md) | 删 14 套 Port/ORM/Repo/Task，**表 RENAME 改 27 张** | 待对齐 10-分库 |
| [06-数据源适配器](06-数据源适配器.md) | `TushareAdapter` / `AdataAdapter`（不变） | 部分对齐 |
| [**10-分库与表结构**](10-分库与表结构.md) | **权威定义**：5 面、双库、27 张表、短前缀 | ✅ |

---

## 9. 实施阶段

| 阶段 | 内容 | 文档 | 验收 |
| :-- | :-- | :-- | :-- |
| D0 | 命名重整（DDD 化） | 09 §0 | `collect_fetchers` → `sys_data_ports`；`sys_collect_tasks` → `sys_collect_jobs` |
| D1 | `sys_data_ports` 删 `output_schema/table_config/output_schema_hash`；**新增 `facet` 字段**；`PortCatalog` 启动装配 | 02 | 启动期 catalog 加载正常；`/collect/catalog` 输出含 facet 字段 |
| D2 | `DynamicRawDataStore` 上线；采集时选表 + 反查 + 试运行 + 入库（**PostgreSQL 语法**） | 03 | 选 `capital_moneyflow` 表，同交易日入库行数 = 旧表行数 |
| D3 | 前端加"选择目标表"下拉框；`/collect/tables` 端点上线 | 03/前端 | 前端能选表；选错表（如缺列）返回友好错误 |
| D4 | 读侧改用新表名；旧表可改名或保留；**双库物理迁移** | 05 / 10 | `data_board` 查 `capital_moneyflow` 与改前结果一致；`raw_data_db` 与 `attribution_db` 物理隔离 |
| D5 | 删旧 14 套 Port/BO/ORM/Repo/Task；`TushareAdapter` 集中 fetch | 05 / 06 | `application/` grep `MoneyflowPort` / `CapMoneyflowDB` / `XxxDB` 应为 0 |
| D6 | `AdataAdapter` 试 1 个 port | 06 | 选 adata 的表 + 选对应 port，入库成功 |

---

## 10. 风险与回滚

| 风险 | 缓解 |
| :-- | :-- |
| 用户选了错误的表（如列名对不上） | 采集时字段校验：第三方返回列 ⊄ 表列 → 抛错返回，**不写任何行** |
| 试运行成功但正式入库失败 | PostgreSQL executemany 失败直接抛错；任务计 fail；前一行试运行行仍在表中（接受，因为是同数据） |
| 运维建表列名与第三方返回不一致 | `TushareAdapter` / `AdataAdapter` 里做字段名映射（统一到 snake_case）；建表规范要求列名 = 适配器输出名 |
| 读侧查旧表名不存在 | D4 统一改到新表，一次迁移完成 |
| 删了 output_schema 配置后，想知道某表有哪些列 | 随时 `SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'xxx'` |
| 一个表被多个 port 写入，字段冲突 | 约束：每个表只服务一类字段来源；不同 port 选不同表 |
| 删了旧的 `_SPECS` 后想回滚 | D5 之前 git revert；D5 之后旧表数据已迁到新表里，新代码删了可以重建旧类 |
| **PostgreSQL vs MySQL 语法** | 严格用 `ON CONFLICT (pk) DO UPDATE` / `current_schema()`；写代码前 grep 一次避免 MySQL 痕迹 |
| **双库跨库事务** | 不支持跨库事务，采集时两次 session（业务库写 job + raw 库写数据）独立 commit |

回滚策略：D3 之前任意阶段回退 = 删除动态代码 + 恢复旧路径；D4 之后新表保留，双轨并存（读侧可切回旧表名）。
