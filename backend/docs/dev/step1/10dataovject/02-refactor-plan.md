# 实体层重构 — 修改文档

> 配套图：`01-before-after.md`
> 本文档面向"动手改代码"的同学：列出每个改动点的 **位置 / 新增 / 删除 / 调用方同步**。
> 所有路径相对 `backend/src/`。

---

## 0. 改动一览（按依赖顺序）

| 序 | 改动 | 涉及文件数 | 影响范围 |
|---|---|---|---|
| ① | `domain/base.py` 加 `DomainError` | 1 文件 | 全栈 import 改名 |
| ② | `domain/base.py` 加 `SymboledDatedEntity` 基类 | 1 文件 | 19 个实体基类声明 |
| ③ | 加 `domain/repository.py` 仓储基类 | 1 文件 | 19 个仓储继承 |
| ④ | 3 处 `ApplicationError` 去重 | 3 文件 | 6 个调用方同步 import |
| ⑤ | `stock_pool/entity.py` 双份异常 / 事件去重 | 1 文件 | 改动 stock_pool 全栈 |
| ⑥ | 19 个采集实体改成薄子类 | 19 文件 | 无外部影响（多继承兼容） |
| ⑦ | 19 个采集仓储改成薄子类 | 19 文件 | 无外部影响 |
| ⑧ | (本期不写代码，只规划) ORM 实现基类 | 1 文件规划 | 后续 P2 |

> **建议批次**：①+④ 同批次；②+⑥+⑦ 同批次；③+ 后续仓储实现 同批次；⑤ 单独批次。

---

## 1. domain/base.py — 加 `DomainError`

### 背景

- 现状：`kline / stock_info / stock_pool` 三处各定义一个完全相同的 `ApplicationError` 类（附带 `message + code`）。
- DDD.md §2.4 明确"业务异常归 domain 层"——而 `ApplicationError` 这个命名是 application 层语义，违反 DDD 命名。

### 新增（追加在 `domain/base.py` 末尾）

```python
# ════════════════════════════════════════════════════════════════
# 领域异常基类
# 业务规则违反 → 抛 DomainError 子类（DDD.md §2.4）
# ════════════════════════════════════════════════════════════════


class DomainError(Exception):
    """领域异常基类（统一 message + code 字段）

    按 DDD.md §2.4：业务异常属于领域知识，由 domain 层定义。
    命名不再用 "ApplicationError"（那是 application 层语义）。
    """

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)
```

### 删除

- `domain/entitys/kline/entity.py` 第 223-229 行的 `class ApplicationError`
- `domain/entitys/stock_info/entity.py` 第 103-109 行的 `class ApplicationError`
- `domain/entitys/stock_pool/entity.py` 第 394-400 行的 `class ApplicationError`

### 调用方同步

把 `from domain.entitys.kline.entity import ApplicationError, KlineNotFoundError`
改成 `from domain.entitys.kline.entity import KlineNotFoundError`（`ApplicationError` 来自 `domain.base.DomainError`，**`KlineNotFoundError` 现在继承 `DomainError` 而不是 `ApplicationError`，但 `isinstance` 兼容——因为 `DomainError.__bases__ == (Exception,)`**）。

涉及 `route/api/v1/` 与 `application/service/` 下所有 `except ApplicationError` / `except KlineAppError` / `except PoolAppError` 的地方（搜索关键字 `ApplicationError` 全替换为 `DomainError`）。

---

## 2. domain/base.py — 加 `SymboledDatedEntity`

### 背景

- 19 个"采集数据"实体（`cap_* / base_* / fin_* / mkt_*`）当前全用 `@dataclass` 裸类，**没有继承 `Entity`**。
- 它们字段都长这个样：

```python
symbol: str
trade_date: date
[N 个] Mapped[Optional[float]]
data_source: str = "tushare"
```

### 新增（追加在 `domain/base.py` 末尾）

```python
from datetime import date  # 已在文件顶部


@dataclass
class SymboledDatedEntity(Entity):
    """按 (symbol, trade_date) 维度采集的数据实体基类

    子类：
    - 自动获得 id-based __eq__ / __hash__（来自 Entity）
    - 自动获得 symbol / trade_date / data_source 三个公共字段

    覆盖 19 个 cap_* / base_* / fin_* / mkt_* 中的大多数。
    """

    id: int
    symbol: str
    trade_date: date
    data_source: str = "tushare"
```

> 注：`Entity` 自己不是 dataclass（`domain/base.py` 注释专门说了"不使用 dataclass 以避免字段顺序冲突"），所以 `SymboledDatedEntity` 重新启用 `@dataclass` 是 OK 的。

### 子类改造

19 个实体改为薄子类，例如：

**Before**：
```python
# domain/entitys/base_adj_factor/entity.py
@dataclass
class BaseAdjFactor:
    """复权因子"""
    symbol: str
    trade_date: date
    adj_factor: float
    data_source: str = "tushare"
```

**After**：
```python
# domain/entitys/base_adj_factor/entity.py
from domain.base import SymboledDatedEntity


@dataclass
class BaseAdjFactor(SymboledDatedEntity):
    """复权因子"""
    id: int = 0
    adj_factor: float = 0.0
```

子类的所有外部使用方（ORM `_to_entity` / fetcher BO→entity / route DTO）**构造签名变了**：

| 调用 | Before | After |
|---|---|---|
| `_to_entity` | `BaseAdjFactor(symbol=row.symbol, ...)` | `BaseAdjFactor(id=row.id, symbol=row.symbol, ...)` |
| `find_by_symbol` 返回值 | `BaseAdjFactor` 实例 | 仍是 `BaseAdjFactor` 实例（多了 `id`，不影响） |

⚠️ 调用方同步：所有构造 `BaseAdjFactor()` / `CapMargin()` / `FinDailyBasic()` 等的地方都要**加上 `id` 参数**。

### mkt_calendar 特殊性

`mkt_calendar` 主键是 `(exchange, cal_date)`，不是 `(symbol, trade_date)`，**它不能继承 `SymboledDatedEntity`**——单独列出来不参与本步骤。

### 实体清单（`SymboledDatedEntity` 适配）

| 聚合根 | 字段数 | 适配 | 备注 |
|---|---:|:---:|---|
| base_adj_factor | 4 | ✅ | |
| base_dividend | 13 | ✅ | 主键可能 (symbol, end_date) |
| base_name_change | 7 | ✅ | 主键 (symbol, ?) |
| base_suspend | 5 | ✅ | |
| cap_block_trade | 9 | ✅ | |
| cap_holder_num | 6 | ✅ | 主键 (symbol, end_date) |
| cap_margin | 10 | ⚠️ | 此表按 (exchange_id, trade_date)，主键不是 symbol |
| cap_margin_detail | 11 | ✅ | |
| cap_moneyflow | 21 | ✅ | |
| cap_top_inst | 11 | ✅ | |
| cap_top_list | 16 | ✅ | |
| fin_daily_basic | 19 | ✅ | |
| fin_report | 20 | ⚠️ | 主键 (symbol, period)，trade_date 改名 |
| fin_top10_float | 9 | ⚠️ | trade_date 可能改 ann_date |
| fin_top10_holders | 10 | ⚠️ | 同上 |
| mkt_index_member | 9 | ✅ | |
| mkt_market_daily | 12 | ⚠️ | trade_date + market |
| mkt_sector_daily | 15 | ⚠️ | trade_date + sector |
| mkt_calendar | 5 | ❌ | 不参与本步骤 |

⚠️ 标 ⚠️ 的需要确认主键——`SymboledDatedEntity` 的字段名是 `trade_date`，但 `cap_margin` 的主键是 `(exchange_id, trade_date)`，多一个 `exchange_id` 字段，不影响继承；`fin_report` 的 `trade_date` 对应 `end_date`，需要：
- **方案 A**：在子类重命名（`trade_date: end_date`）——不推荐，破坏基类字段名
- **方案 B**：`fin_report` 等少数不继承基类 `SymboledDatedEntity`，手写自己的字段
- **方案 C**：再抽一层 `SymboledEntity` 父类（只有 symbol+data_source），各表再子继承

**推荐选 C**：

```python
# base.py
@dataclass
class SymboledEntity(Entity):
    id: int
    symbol: str
    data_source: str = "tushare"


@dataclass
class SymboledDatedEntity(SymboledEntity):
    trade_date: date
```

然后 `cap_margin` 直接继承 `SymboledEntity` 自己再加 `trade_date + exchange_id`；`fin_report` 继承 `SymboledEntity` 自己再加 `end_date` 等。

---

## 3. domain/repository.py — 加 `BaseSymboledDatedRepository`

新建文件 `domain/repository.py`（**新文件，不是新增到 `base.py`** —— 仓储基类是协议/接口专属，DDD.md §3.1 暗示 repository 是平级于 entitys 的目录；放 `domain/repository.py` 是合规且清晰的）：

```python
"""领域层 - 仓储接口基类

按 DDD.md §3.1：repository 接口定义在 domain 层，由 infrastructure 实现。
"按 (symbol, trade_date) 维度采集"是一类高频查询，
对 19 个 cap_* / base_* / fin_* / mkt_* 的仓储抽象出统一接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Generic, Optional, TypeVar


T = TypeVar("T")  # entity 类型


class BaseSymboledDatedRepository(ABC, Generic[T]):
    """按 (symbol, trade_date) 维度采集的仓储接口基类

    Generic[T]：子类声明时指定实体类，避免每个都重写类型签名。
    """

    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def save_batch(self, entities: list[T]) -> int: ...

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[T]: ...
```

### 子类改造（示例）

**Before**：
```python
# domain/entitys/base_adj_factor/repository.py
class BaseAdjFactorRepository(ABC):
    @abstractmethod
    async def save(self, entity: BaseAdjFactor) -> BaseAdjFactor: ...
    @abstractmethod
    async def save_batch(self, entities: list[BaseAdjFactor]) -> int: ...
    @abstractmethod
    async def find_by_symbol(self, symbol, start_date=None, end_date=None) -> list[BaseAdjFactor]: ...
```

**After**：
```python
# domain/entitys/base_adj_factor/repository.py
from domain.entitys.base_adj_factor.entity import BaseAdjFactor
from domain.repository import BaseSymboledDatedRepository


class BaseAdjFactorRepository(BaseSymboledDatedRepository[BaseAdjFactor]):
    """复权因子仓储（继承通用维度仓储）"""
    pass
```

### 不参与本步骤的特殊仓储

| 仓储 | 原因 |
|---|---|
| `BaseNameChangeRepository` | 主键是 `(symbol, start_date, name)`，时间维度不是单 trade_date |
| `CapMarginRepository` | 主键 `(exchange_id, trade_date)`，不是 symbol 维度 |
| `CapTopListRepository` | 仅按 trade_date，无 symbol |
| `MktCalendarRepository` | 按 (exchange, cal_date) |
| `MktIndexMemberRepository` | 按 sector + trade_date |
| `MktMarketDailyRepository` | 按 (market, trade_date) |
| `MktSectorDailyRepository` | 按 (sector, trade_date) |

这 7 个**不继承** `BaseSymboledDatedRepository`，保留自己的 ABC 声明（也是 4 行 ABC，没重复）。

---

## 4. entitys/{kline,stock_info} — `ApplicationError` 去重

按照 §1 节统一改，三个文件：

```diff
- class ApplicationError(Exception):
-     """应用层异常基类"""
-     def __init__(self, message, code="APP_ERROR"):
-         self.message = message
-         self.code = code
-         super().__init__(message)

+ # ApplicationError 已迁到 domain.base.DomainError（DDD.md §2.4 命名规范）
+ # KlineNotFoundError / KlineDataError / CollectionError 改为继承 DomainError
```

```diff
- class KlineNotFoundError(ApplicationError):
+ class KlineNotFoundError(DomainError):
```

调用方同步：
- `from domain.entitys.kline.entity import ApplicationError` → 删
- `except ApplicationError` → `except DomainError`
- 全栈搜索关键字 `ApplicationError` 替换为 `DomainError`

---

## 5. entitys/stock_pool/entity.py — 双份事件/异常去重

### 5.1 双份事件（1-46 行 + 330-386 行）

当前两个副本：

| 上半段 (1-46) | 下半段 (330-386) | 处置 |
|---|---|---|
| `PoolCreated` | `PoolCreated` | 同名重复，**保留上半段** |
| `PoolRenamed` | `PoolRenamed` | 同名重复，**保留上半段** |
| `PoolArchived` | `PoolArchived` | 同名重复，**保留上半段** |
| `MemberAdded` | `MemberAdded` | 同名重复，**保留上半段** |
| `MemberRemoved` | `MemberRemoved` | 同名重复，**保留上半段** |
| 无 | `PoolDeleted` | **保留** |
| 无 | `PoolOperationStarted` | **保留** |
| 无 | `PoolOperationProgress` | **保留** |
| 无 | `PoolOperationFinished` | **保留** |

### 5.2 双份异常（53-77 行 + 392-437 行）

| 上半段 (53-77) | 下半段 (392-437) | 处置 |
|---|---|---|
| `PoolDomainError` (基类) | `ApplicationError` (基类) | `PoolDomainError` 改为继承 `DomainError`；`ApplicationError` 整体删除 |
| `DuplicateMemberError(symbol, pool_id)` | `DuplicatePoolMemberError(symbol)` | **重复语义**，合并为 `DuplicateMemberError(symbol, pool_id)`，删 `DuplicatePoolMemberError` |
| `MemberNotFoundError(symbol, pool_id)` | `PoolMemberNotFoundError(symbol)` | **重复语义**，合并为 `MemberNotFoundError(symbol, pool_id)`，删 `PoolMemberNotFoundError` |
| `CannotDeleteDefaultPoolError(pool_id)` | `CannotDeleteDefaultPoolError()` (不接 pool_id) | **签名不一致**，**保留上半版本**，删下半版本 |
| 无 | `PoolNotFoundError(pool_id)` | **保留** |
| 无 | `PoolOperationNotFoundError(op_id)` | **保留** |
| 无 | `PoolOperationConflictError(pool_id)` | **保留** |

### 5.3 改完后大致骨架

```python
"""stock_pool - 聚合根"""

from domain.base import AggregateRoot, DomainError, DomainEvent
from domain.entitys.stock_pool.vo import PoolMember, PoolType


# ── 领域事件 ────────────────────────────────────────────────────

@dataclass(kw_only=True)
class PoolCreated(DomainEvent):
    pool_id: int
    pool_name: str


@dataclass(kw_only=True)
class PoolRenamed(DomainEvent):
    pool_id: int
    new_name: str


@dataclass(kw_only=True)
class PoolDeleted(DomainEvent):
    pool_id: int


@dataclass(kw_only=True)
class PoolArchived(DomainEvent):
    pool_id: int


@dataclass(kw_only=True)
class MemberAdded(DomainEvent):
    pool_id: int
    symbol: str


@dataclass(kw_only=True)
class MemberRemoved(DomainEvent):
    pool_id: int
    symbol: str


@dataclass(kw_only=True)
class PoolOperationStarted(DomainEvent):
    op_id: int
    pool_id: int
    operation_type: str
    total: int


@dataclass(kw_only=True)
class PoolOperationProgress(DomainEvent):
    op_id: int
    done: int
    total: int
    failed: int


@dataclass(kw_only=True)
class PoolOperationFinished(DomainEvent):
    op_id: int
    pool_id: int
    status: str
    success_count: int
    failed_count: int


# ── 领域异常 ────────────────────────────────────────────────────

class PoolDomainError(DomainError):
    """stock_pool 家族异常基类"""
    def __init__(self, message: str, code: str):
        super().__init__(message, code)


class DuplicateMemberError(PoolDomainError):
    def __init__(self, symbol: str, pool_id: int):
        self.symbol = symbol
        self.pool_id = pool_id
        super().__init__(f"股票 {symbol} 已在池 {pool_id} 中", "DUPLICATE_MEMBER")


class MemberNotFoundError(PoolDomainError):
    def __init__(self, symbol: str, pool_id: int):
        self.symbol = symbol
        self.pool_id = pool_id
        super().__init__(f"股票 {symbol} 不在池 {pool_id} 中", "MEMBER_NOT_FOUND")


class CannotDeleteDefaultPoolError(PoolDomainError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(f"无法删除默认池 {pool_id}", "CANNOT_DELETE_DEFAULT_POOL")


class PoolNotFoundError(DomainError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(f"操作池不存在: {pool_id}", "POOL_NOT_FOUND")


class PoolOperationNotFoundError(DomainError):
    def __init__(self, op_id: int):
        self.op_id = op_id
        super().__init__(f"操作记录不存在: {op_id}", "POOL_OP_NOT_FOUND")


class PoolOperationConflictError(DomainError):
    def __init__(self, pool_id: int):
        self.pool_id = pool_id
        super().__init__(
            f"池 {pool_id} 已有进行中的操作，请等待完成后重试",
            "OPERATION_CONFLICT",
        )


# ── StockPool 聚合根 ───────────────────────────────────────────

@dataclass
class StockPool(AggregateRoot):
    # ... (保持现状)
```

预计减约 **80 行死代码**。

---

## 6. 19 个采集数据实体 — 改薄子类

按 §2 表 **✅ 部分**（12 个）改为继承 `SymboledDatedEntity`：

```python
# 示例：base_adj_factor/entity.py
from domain.base import SymboledDatedEntity


@dataclass
class BaseAdjFactor(SymboledDatedEntity):
    """复权因子"""
    adj_factor: float = 0.0
```

⚠️ 部分（4 个：`cap_margin` / `fin_report` / `fin_top10_*` / `mkt_market_daily` / `mkt_sector_daily`）继承 `SymboledEntity` 而非 `SymboledDatedEntity`，自己加剩余维度字段。

⚠️ 修改涉及的 `_to_entity` 函数（共 19 个 future ORM impl + 1 个当前 `fin_daily_basic` impl）：构造实体时多传 `id`。
当前 `fin_daily_basic` 是 ORM 实现里唯一的，`_to_entity` 已经返回 `FinDailyBasic(...)` 字面调用，**批量改**这些位置。

---

## 7. 19 个采集数据仓储 — 改薄子类

按 §3 表 **能直接继承** 的 12 个改为 3 行 `pass`：

```python
# 示例：base_adj_factor/repository.py
from domain.entitys.base_adj_factor.entity import BaseAdjFactor
from domain.repository import BaseSymboledDatedRepository


class BaseAdjFactorRepository(BaseSymboledDatedRepository[BaseAdjFactor]):
    """复权因子仓储接口"""
    pass
```

剩余 7 个特殊仓储（`BaseNameChange / CapMargin / CapTopList / MktCalendar / MktIndexMember / MktMarketDaily / MktSectorDaily`）保留各自 ABC 声明。

预计减约 **380 行模板代码**。

---

## 8. ORM 实现基类规划（本期不写代码）

`infrastructure/persistence/repositories/base_repository.py`（建议新建文件）应实现：

```python
"""ORM 仓储实现基类

按"按 (symbol, trade_date) 采集"模式抽象，配套 domain.repository.BaseSymboledDatedRepository。
子类只需提供：
- _db_cls: ORM 类
- _value_columns: 可空业务字段名
- _to_entity(row): ORM 行 → 领域实体
"""
from __future__ import annotations

from datetime import date
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

DB = TypeVar("DB")       # ORM 行类
ENT = TypeVar("ENT")     # 实体类


class BaseSymboledDatedRepoImpl(Generic[DB, ENT]):
    def __init__(self, session: AsyncSession, db_cls: Type[DB], ent_cls: Type[ENT]):
        self._session = session
        self._db = db_cls
        self._ent = ent_cls

    async def save(self, entity: ENT) -> ENT: ...
    async def save_batch(self, entities: list[ENT]) -> int: ...
    async def find_by_symbol(self, symbol, start_date=None, end_date=None) -> list[ENT]: ...
    def _to_entity(self, row: DB) -> ENT:
        raise NotImplementedError
```

子类的标准形态：

```python
# infrastructure/persistence/repositories/base_adj_factor_repository.py
from infrastructure.persistence.models.base_adj_factor import BaseAdjFactorDB
from infrastructure.persistence.base_repository import BaseSymboledDatedRepoImpl
from domain.entitys.base_adj_factor.entity import BaseAdjFactor


class BaseAdjFactorRepoImpl(BaseSymboledDatedRepoImpl[BaseAdjFactorDB, BaseAdjFactor]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, BaseAdjFactorDB, BaseAdjFactor)

    def _to_entity(self, row: BaseAdjFactorDB) -> BaseAdjFactor:
        return BaseAdjFactor(
            id=row.id,
            symbol=row.symbol,
            trade_date=row.trade_date,
            adj_factor=row.adj_factor,
            data_source=row.data_source,
        )
```

> ⚠️ ORM 实现目前只有 `fin_daily_basic` 一个（被 `daily_basic` 采集任务 + `stock.py` route 引用）。
> 其它 18 个仓储当前**没有 ORM 实现**——这个缺口是 phase2 留下的。
> 建议下一步用这个基类**顺势把缺的 18 个 ORM 实现批量补完**，比纯抽象基类收益更大。

---

## 9. 风险点

| 风险 | 等级 | 缓解 |
|---|---|---|
| 实体构造签名变化（多了 `id`），调用方同步量大 | 中 | 全栈 `grep "BaseAdjFactor\(" "CapMargin\("` 一次性更新 |
| `isinstance(x, ApplicationError)` 不再成立 | 中 | 同步改 `except ApplicationError` → `except DomainError` |
| `CannotDeleteDefaultPoolError` 改签名后，调用方漏传 `pool_id` | 低 | 静态检查 + grep `CannotDeleteDefaultPoolError(` |
| `SymboledDatedEntity` 加 `id`，但部分实体原本没有 id 字段（如 `base_adj_factor`） | 低 | 检查 entity 的 ORM 表都有 `id` 主键（已确认） |
| `mkt_calendar` / `CapMargin` / `MktMarketDaily` 等不参与本步骤 | — | 不改，保持现状 |
| 19 个 ORM 模型暂时没有 ORM impl，基类现在加 = 没人用 | 低 | ORM 基类（§8）暂不写代码，只规划 |

---

## 10. 测试建议

- **静态检查**：`mypy`/`pyright` 确保 19 个 dataclass 继承后字段顺序合法
- **构造一致性**：构造 `BaseAdjFactor(id=1, symbol="000001", trade_date=date(2026,1,1), adj_factor=1.0)` 看 repr
- **`isinstance` 兼容**：`assert isinstance(KlineNotFoundError("x"), DomainError)` 必须 True
- **接口签名兼容**：`BaseAdjFactorRepository.find_by_symbol("000001")` 必须返回 `list[BaseAdjFactor]`（下游 AppService 不变）
- **集成验证**：跑采集任务 `daily_basic`，数据流向 `FinDailyBasicRepoImpl → FinDailyBasic → 领域 → 返回`

---

## 11. 实施清单（TODO 列表）

```
[ ] §1: domain/base.py 加 DomainError
[ ] §4: 删 3 处 ApplicationError；KlineNotFoundError/StockNotFoundError 等改继承 DomainError
[ ] §5: stock_pool/entity.py 双份异常/事件去重
[ ] §2: domain/base.py 加 SymboledEntity + SymboledDatedEntity
[ ] §6: 12 个完全适配的实体（cap_* / base_* / fin_* / mkt_* 不含 ⚠️）改继承 SymboledDatedEntity
[ ] §6: 4 个部分适配的实体（cap_margin / fin_report / fin_top10_* / mkt_market_daily 等）改继承 SymboledEntity
[ ] §3: 新建 domain/repository.py 加 BaseSymboledDatedRepository[T]
[ ] §7: 12 个仓储改继承 BaseSymboledDatedRepository[Entity]
[ ] 全栈 grep 'ApplicationError' 替换 'DomainError'
[ ] 跑采集任务验证数据流
[ ] (本期不写代码) §8 ORM 基类规划
```
