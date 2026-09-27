# 01 — 领域层设计

> 配套 UML：`docs/PlantUML/Concept/01-class.puml` 中「领域层 (Domain)」package
> 所属：`docs/dev/06gainian/README.md` 第二节「核心决策」

---

## 一、聚合根边界

### 1.1 新聚合根：`concept`

```
concept（聚合根）
├── Concept              ← 实体（Entity），持有状态与不变式
├── ConceptMember        ← 子实体，由 Concept 通过 concept_id 关联
└── ConceptBriefVO       ← 值对象（frozen），只读投影
```

**聚合边界**：以 `Concept` 为聚合根，`ConceptMember` 作为子实体仅在 `Concept` 内部维护，
不直接对外暴露修改入口。

### 1.2 不放在 stock_info 下的理由

`stock_info` 聚合根关注「单只股票的元数据」，概念是「外部数据源对股票的标签」，
**生命周期不同步**：

| 聚合根 | 数据源 | 同步周期 | 数据量 |
|------|------|--------|------|
| stock_info | Tushare | 一次性 + 退市时更新 | 5569 条 |
| concept | AKShare | 每周/每日 | 500+ 概念 + 15000+ 关联 |

强行合并会让 stock_info 仓储的耦合度爆炸。

---

## 二、实体（Entity）

### 2.1 Concept

```python
# domain/concept/entity.py
"""概念实体 — 概念聚合根"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ConceptSource(str, Enum):
    """概念数据来源"""
    EM = "em"      # 东方财富（默认）
    THS = "ths"    # 同花顺


class ConceptType(str, Enum):
    """概念类型（粗粒度分类）"""
    INDUSTRY = "industry"   # 行业概念（接近 SW 行业）
    THEME = "theme"         # 主题概念（如"碳中和"）
    STYLE = "style"         # 风格概念（如"高股息"）
    REGION = "region"       # 地域概念（如"雄安"）
    EVENT = "event"         # 事件概念（如"中字头"）
    OTHER = "other"


@dataclass(frozen=False)
class Concept:
    """概念实体（聚合根）

    不变式：
    - name 与 source 联合唯一
    - is_active = False 时仍保留历史（软删除）
    - last_synced_at 必填（标记采集状态）
    """

    id: Optional[int] = field(default=None)
    name: str = field(...)
    source: ConceptSource = field(default=ConceptSource.EM)
    concept_type: ConceptType = field(default=ConceptType.OTHER)
    description: Optional[str] = field(default=None)
    stock_count: int = field(default=0)
    is_active: bool = field(default=True)
    first_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_synced_at: Optional[datetime] = field(default=None)

    @classmethod
    def create(
        cls,
        name: str,
        source: ConceptSource = ConceptSource.EM,
        concept_type: ConceptType = ConceptType.OTHER,
        description: Optional[str] = None,
    ) -> "Concept":
        """工厂方法：从 BO 创建"""
        if not name or not name.strip():
            raise ValueError(f"Concept name 不能为空: {name!r}")
        return cls(
            name=name.strip(),
            source=source,
            concept_type=concept_type,
            description=description,
        )

    def mark_synced(self, member_count: int, at: Optional[datetime] = None) -> None:
        """同步完成后调用：更新 last_synced_at 和 stock_count"""
        self.last_synced_at = at or datetime.now(timezone.utc)
        self.stock_count = member_count
        if not self.is_active:
            # 重新激活（曾下线又出现）
            self.is_active = True

    def deactivate(self) -> None:
        """软删除：标记为不活跃，保留历史"""
        self.is_active = False
```

### 2.2 ConceptMember

```python
@dataclass(frozen=True)
class ConceptMember:
    """概念成员（子实体）

    不变式：
    - (symbol, concept_id) 联合唯一
    - source 必须与所属 Concept.source 一致
    """

    symbol: str
    concept_id: int
    source: ConceptSource
    joined_at: datetime

    @classmethod
    def create(
        cls,
        symbol: str,
        concept_id: int,
        source: ConceptSource,
        joined_at: Optional[datetime] = None,
    ) -> "ConceptMember":
        if not symbol or len(symbol) != 6 or not symbol.isdigit():
            raise ValueError(f"无效的 symbol: {symbol!r}")
        return cls(
            symbol=symbol,
            concept_id=concept_id,
            source=source,
            joined_at=joined_at or datetime.now(timezone.utc),
        )
```

---

## 三、BO（业务对象，采集层产出）

### 3.1 ConceptListBO

```python
# domain/concept/schemas.py
"""概念 BO（采集层 → 应用层）"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator

from domain.concept.entity import Concept, ConceptSource, ConceptType


class ConceptListBO(BaseModel):
    """概念清单 BO（来自 ak.stock_board_concept_name_em）

    字段说明：
    - 东方财富接口实际字段：排名 / 板块名称 / 板块代码 / 最新价 / 涨跌额 / 涨跌幅 /
      总市值 / 换手率 / 上涨家数 / 下跌家数 / 领涨股票 / 板块代码
    - 我们只关心：name / code / stock_count（成分股数量）
    """

    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20, description="板块代码")
    source: ConceptSource = Field(default=ConceptSource.EM)
    concept_type: ConceptType = Field(default=ConceptType.OTHER)
    stock_count: int = Field(default=0, ge=0)
    description: Optional[str] = Field(default=None, max_length=500)
    raw_payload: Optional[dict] = Field(default=None, description="原始 dict（调试用）")

    @validator("name")
    def normalize_name(cls, v: str) -> str:
        """概念名称标准化：去前后空格、去除常见噪声字符"""
        v = v.strip()
        # 东方财富偶尔返回 "人形机器人\n" 这种，剔除
        for noise in ("\n", "\r", "\t"):
            v = v.replace(noise, "")
        return v

    def to_entity(self) -> Concept:
        """BO → Entity"""
        return Concept.create(
            name=self.name,
            source=self.source,
            concept_type=self.concept_type,
            description=self.description,
        )


class ConceptStockBO(BaseModel):
    """概念成分股 BO（来自 ak.stock_board_concept_cons_em(symbol=name)）

    字段说明：
    - 东方财富接口实际字段：序号 / 代码 / 名称 / 最新价 / 涨跌幅 / 涨跌额 / 成交量 /
      成交额 / 振幅 / 最高 / 最低 / 今开 / 昨收 / 市盈率 / 市净率
    - 我们只关心：symbol / name / rank（序号）
    """

    symbol: str = Field(..., min_length=6, max_length=6)
    name: str = Field(..., min_length=1, max_length=100)
    source: ConceptSource = Field(default=ConceptSource.EM)
    rank: Optional[int] = Field(default=None, description="在该概念中的排名")
    latest_price: Optional[float] = Field(default=None)

    @validator("symbol")
    def normalize_symbol(cls, v: str) -> str:
        return v.zfill(6)

    def to_entity(self, concept_id: int) -> "ConceptMember":
        from domain.concept.entity import ConceptMember
        return ConceptMember.create(
            symbol=self.symbol,
            concept_id=concept_id,
            source=self.source,
        )
```

---

## 四、值对象（VO，frozen）

### 4.1 ConceptBriefVO

```python
# domain/concept/value_objects.py
"""概念只读投影 VO"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from domain.concept.entity import ConceptSource


@dataclass(frozen=True)
class ConceptBriefVO:
    """概念简略 VO（用于嵌入到 StockPanelItemVO.concepts）

    设计为 frozen dataclass：
    - 不可变，避免下游误改
    - hashable，可放进 set / 作为 dict key
    - 字段最小化（仅前端展示需要的 3 个字段）
    """

    concept_id: int
    name: str
    source: str  # ConceptSource 的 value（"em" / "ths"），方便序列化


@dataclass(frozen=True)
class ConceptGroupedVO:
    """概念分组 VO（用于详情抽屉「概念」Tab）

    与 ConceptBriefVO 的区别：
    - ConceptBriefVO：3 字段，用于列表预热
    - ConceptGroupedVO：5 字段（多了 concept_type、description），用于抽屉 Tab 分组展示
    """

    concept_id: int
    name: str
    source: str
    concept_type: str      # industry / theme / style / region / event / other
    description: Optional[str] = None
```

---

## 五、Repository Protocol

### 5.1 ConceptRepository

```python
# domain/concept/repository.py
"""Concept 仓储协议"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from domain.concept.entity import Concept, ConceptMember
from domain.concept.value_objects import ConceptBriefVO


@runtime_checkable
class ConceptRepository(Protocol):
    """概念聚合根仓储协议

    职责：
    - 写入：采集器写入
    - 读取：列表 / 详情 / 反查
    - 软删除：标记 is_active = False
    """

    # ── 写入 ─────────────────────────────────────
    async def upsert_concept(self, concept: Concept) -> Concept:
        """新增或更新概念，返回带 id 的 Concept

        - 命中 (name, source) 唯一约束 → 更新 description / concept_type / is_active
        - 未命中 → INSERT
        """
        ...

    async def upsert_members(
        self,
        concept_id: int,
        members: list[ConceptMember],
    ) -> int:
        """批量写入概念成员，先 DELETE 旧再 INSERT 新，返回写入条数

        全量覆盖语义：保证 stock_concept_members 与采集数据一致。
        """
        ...

    # ── 单条读取 ──────────────────────────────────
    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        ...

    async def get_concept_by_name(
        self, name: str, source: str = "em"
    ) -> Optional[Concept]:
        ...

    # ── 反向查询（核心：被 panel 复用）─────────────
    async def list_concepts_by_symbol(self, symbol: str) -> list[ConceptBriefVO]:
        """单只股票所属的所有活跃概念"""
        ...

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询，避免 N+1

        单次 SQL：symbol IN (:symbols) + JOIN concepts
        返回 dict[symbol, list[ConceptBriefVO]]，
        未在结果中的 symbol 表示无活跃概念（不会自动补 key）。
        """
        ...

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单只股票所属的所有活跃概念（含 concept_type / description，用于详情抽屉「概念」Tab）

        与 list_concepts_by_symbol 的区别：
        - list_concepts_by_symbol：返回 ConceptBriefVO[]（3 字段），用于列表预热
        - list_concepts_by_symbol_grouped：返回 ConceptGroupedVO[]（5 字段），用于抽屉 Tab 渲染
        """
        ...

    # ── 列表 / 统计 ──────────────────────────────
    async def list_concepts(
        self,
        q: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        """分页列出概念"""
        ...

    async def count_concepts(
        self, source: Optional[str] = None, is_active: Optional[bool] = None,
    ) -> int:
        ...

    # ── 同步状态 ──────────────────────────────────
    async def get_last_synced_at(self, source: str = "em") -> Optional[datetime]:
        """最近一次同步时间（取 is_active 概念中最大的 last_synced_at）"""
        ...
```

### 5.2 复用：StockPanelComposeRepository 扩展

```python
# domain/panel/repository.py（既有文件修改）
from domain.concept.value_objects import ConceptBriefVO

@runtime_checkable
class StockPanelComposeRepository(Protocol):
    # ... 既有方法不变 ...

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询概念（与 list_membership_by_symbols 对称）

        实现层内部委托给 ConceptRepository：
            return await self._concept_repo.list_concepts_by_symbols(symbols)
        """
        ...
```

---

## 六、领域异常

### 6.1 ConceptNotFoundError

```python
# domain/concept/exceptions.py
"""概念领域异常"""

from __future__ import annotations

from domain.exceptions import DomainError


class ConceptNotFoundError(DomainError):
    """指定概念不存在（按 id / name 查不到）"""
    message: str

    def __init__(self, *, id: int | None = None, name: str | None = None):
        if id is not None:
            self.message = f"概念 id={id} 不存在"
        elif name is not None:
            self.message = f"概念 name={name!r} 不存在"
        else:
            self.message = "概念不存在"
        super().__init__(self.message)
```

---

## 七、与现有 domain 层的关系

| 现有聚合根 | 与 concept 的关系 | 是否需要修改 |
|----------|------|------|
| `stock_info` | 通过 `stock_concept_members.symbol` 间接关联 | ❌ 不修改 |
| `panel`（跨域视图） | StockPanelItemVO.concepts 嵌入 ConceptBriefVO | ✏️ 加 1 个字段 |
| `pool`（运营层） | 同为 N:M 关联模式，可参考但无代码复用 | ❌ 不修改 |
| `kline / fin_daily_basic / fin_report` | 与概念无关联 | ❌ 不修改 |

---

## 八、单元测试覆盖要点（设计阶段先列）

| 测试 | 覆盖 |
|------|------|
| `test_concept_entity.py` | `Concept.create` 校验、`mark_synced` 状态转移、`deactivate` |
| `test_concept_member.py` | symbol 校验、联合主键 |
| `test_concept_vo.py` | frozen 不可变、hashable |
| `test_concept_repository.py`（mock） | upsert_concept 唯一键冲突路径、upsert_members 全量覆盖语义 |
| `test_protocol_conformance.py` | `ConceptRepoImpl.__implements_protocol__ = ConceptRepository` 标注 |

---

## 九、相关文档

- [README.md](../README.md) — 统一设计文档
- [02-infrastructure-design.md](../02-infrastructure-design.md) — 数据库 / ORM / Repository 实现
- [03-application-and-route-design.md](../03-application-and-route-design.md) — DTO / Service / Route
- `docs/PlantUML/Concept/01-class.puml` — 类图（含领域层 package）
- `docs/PlantUML/Concept/02-data-flow.puml` — 数据流
