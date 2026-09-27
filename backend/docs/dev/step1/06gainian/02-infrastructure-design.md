# 02 — 基础设施层设计

> 配套 UML：`docs/PlantUML/Concept/01-class.puml` 中「持久层」和「采集层」package
> 所属：`docs/dev/06gainian/README.md` 第三节「整体架构」

---

## 一、数据库设计

### 1.1 ER 图

```
┌─────────────────────┐       ┌──────────────────────────────┐
│    stock_infos      │       │      concepts               │
├─────────────────────┤       ├──────────────────────────────┤
│ symbol {PK}         │       │ id {PK}                    │
│ name                │       │ name {UQ}                   │
│ industry            │       │ source                     │
│ market              │  1:N  │ concept_type               │
│ ...                 │◄──────│ description                 │
└─────────────────────┘       │ stock_count                 │
         │                   │ is_active                   │
         │ 1:N               │ first_seen_at               │
         ▼                   │ last_synced_at              │
┌──────────────────────────────┐│                            │
│  stock_concept_members        │└────────────────────────────┘
├──────────────────────────────┤
│ symbol {PK,FK}               │
│ concept_id {PK,FK}           │
│ joined_at                    │
│ source                       │
└──────────────────────────────┘
```

### 1.2 建表 DDL

```sql
-- ============================================================
-- concepts — 概念聚合根表
-- ============================================================
CREATE TABLE concepts (
  id              SERIAL PRIMARY KEY,
  name            VARCHAR(100) NOT NULL,
  source          VARCHAR(10)  NOT NULL DEFAULT 'em',
  concept_type    VARCHAR(50)  NOT NULL DEFAULT 'other',
  description     TEXT,
  stock_count     INTEGER      NOT NULL DEFAULT 0,
  is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
  first_seen_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  last_synced_at TIMESTAMPTZ,

  CONSTRAINT uq_concept_name_source UNIQUE (name, source)
);

CREATE INDEX ix_concepts_source      ON concepts(source);
CREATE INDEX ix_concepts_active      ON concepts(is_active) WHERE is_active = TRUE;
CREATE INDEX ix_concepts_synced_at   ON concepts(last_synced_at DESC NULLS LAST);

COMMENT ON TABLE concepts IS '概念板块聚合根（东方财富 / 同花顺）';
COMMENT ON COLUMN concepts.source IS '"em"=东方财富，"ths"=同花顺';


-- ============================================================
-- stock_concept_members — 概念成员关联表
-- ============================================================
CREATE TABLE stock_concept_members (
  symbol      VARCHAR(10)  NOT NULL,
  concept_id  INTEGER     NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  joined_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source      VARCHAR(10)  NOT NULL DEFAULT 'em',

  CONSTRAINT pk_stock_concept_members PRIMARY KEY (symbol, concept_id)
);

CREATE INDEX ix_concept_member_symbol  ON stock_concept_members(symbol);
CREATE INDEX ix_concept_member_concept ON stock_concept_members(concept_id);

-- 防止孤立 symbol（可先不加 FK，待 stock_infos 稳定后再加）
-- ALTER TABLE stock_concept_members
--   ADD CONSTRAINT fk_stock_concept_member_symbol
--   FOREIGN KEY (symbol) REFERENCES stock_infos(symbol) ON DELETE CASCADE;

COMMENT ON TABLE stock_concept_members IS '概念成员关联表（全量覆盖，不做增量）';
```

### 1.3 命名说明

| 字段 | 说明 |
|------|------|
| `concept_type` | 概念类型：industry / theme / style / region / event / other |
| `is_active` | 软删除：东方财富下线概念时标记 FALSE，保留历史 |
| `first_seen_at` | 首次采集时间（不变） |
| `last_synced_at` | 最近同步时间（每次 sync 更新） |
| `stock_concept_members.symbol` | **不引用** stock_infos（AKShare 的 symbol 可能包含已退市股票） |

---

## 二、ORM 模型

### 2.1 ConceptsDB

```python
# infrastructure/database/models/concept.py
"""概念 ORM 模型"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.models.base import Base


class ConceptsDB(Base):
    """概念聚合根 ORM"""

    __tablename__ = "concepts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="em")
    concept_type: Mapped[str] = mapped_column(String(50), nullable=False, default="other")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stock_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_concepts_source", "source"),
        Index("ix_concepts_active", "is_active", postgresql_where=is_active == True),  # noqa: E501
        {"schema": None},
    )

    def __repr__(self) -> str:
        return f"<ConceptsDB(id={self.id}, name={self.name!r}, source={self.source!r})>"
```

### 2.2 ConceptMemberDB

```python
class ConceptMemberDB(Base):
    """概念成员关联表 ORM"""

    __tablename__ = "stock_concept_members"

    symbol: Mapped[str] = mapped_column(String(10), primary_key=True)
    concept_id: Mapped[int] = mapped_column(
        Integer, primary_key=True,
        # FK 暂不加（避免 stock_infos 删不掉）
        # references="stock_infos", ondelete="CASCADE"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="em")

    __table_args__ = (
        Index("ix_concept_member_symbol", "symbol"),
        Index("ix_concept_member_concept", "concept_id"),
        {"schema": None},
    )

    def __repr__(self) -> str:
        return f"<ConceptMemberDB(symbol={self.symbol!r}, concept_id={self.concept_id})>"
```

---

## 三、Repository 实现

### 3.1 ConceptRepoImpl

```python
# infrastructure/repositories/concept_repository.py
"""Concept 仓储实现"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.concept.entity import Concept, ConceptMember, ConceptSource
from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import ConceptBriefVO, ConceptGroupedVO
from domain.concept.exceptions import ConceptNotFoundError
from infrastructure.database.models.concept import ConceptsDB, ConceptMemberDB

logger = logging.getLogger(__name__)


class ConceptRepoImpl(ConceptRepository):
    """概念仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ── ORM ↔ Entity 转换 ─────────────────────────────────

    def _to_entity(self, row: ConceptsDB) -> Concept:
        return Concept.create(
            id=row.id,
            name=row.name,
            source=ConceptSource(row.source),
            concept_type=row.concept_type,  # ConceptType 已在 entity 中校验
            description=row.description,
            stock_count=row.stock_count,
            is_active=row.is_active,
            first_seen_at=row.first_seen_at,
            last_synced_at=row.last_synced_at,
        )

    def _to_vo(self, concept_id: int, name: str, source: str) -> ConceptBriefVO:
        return ConceptBriefVO(
            concept_id=concept_id,
            name=name,
            source=source,
        )

    # ── 写入 ─────────────────────────────────────────────

    async def upsert_concept(self, concept: Concept) -> Concept:
        row_dict = {
            "name": concept.name,
            "source": concept.source.value,
            "concept_type": concept.concept_type.value if hasattr(concept.concept_type, 'value') else concept.concept_type,
            "description": concept.description,
            "stock_count": concept.stock_count,
            "is_active": concept.is_active,
            "last_synced_at": concept.last_synced_at,
        }
        stmt = (
            pg_insert(ConceptsDB)
            .values(**row_dict)
            .on_conflict_do_update(
                index_elements=["name", "source"],
                set_={
                    **row_dict,
                    "is_active": True,  # 重新上线时激活
                },
            )
            .returning(ConceptsDB.id)
        )
        result = await self._session.execute(stmt)
        concept.id = result.scalar_one()
        await self._session.commit()
        return concept

    async def upsert_members(
        self,
        concept_id: int,
        members: list[ConceptMember],
    ) -> int:
        """全量覆盖语义：DELETE + INSERT"""
        # 1. DELETE 旧成员
        await self._session.execute(
            delete(ConceptMemberDB).where(
                ConceptMemberDB.concept_id == concept_id
            )
        )
        # 2. INSERT 新成员
        if not members:
            await self._session.commit()
            return 0

        rows = [
            {
                "symbol": m.symbol,
                "concept_id": concept_id,
                "joined_at": m.joined_at,
                "source": m.source.value if hasattr(m.source, 'value') else m.source,
            }
            for m in members
        ]
        self._session.add_all([ConceptMemberDB(**r) for r in rows])
        await self._session.commit()
        return len(rows)

    # ── 单条读取 ────────────────────────────────────────

    async def get_concept_by_id(self, concept_id: int) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(ConceptsDB.id == concept_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_concept_by_name(
        self, name: str, source: str = "em"
    ) -> Optional[Concept]:
        stmt = select(ConceptsDB).where(
            and_(
                ConceptsDB.name == name,
                ConceptsDB.source == source,
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return self._to_entity(row) if row else None

    # ── 反向查询 ────────────────────────────────────────

    async def list_concepts_by_symbol(
        self, symbol: str
    ) -> list[ConceptBriefVO]:
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [self._to_vo(r.id, r.name, r.source) for r in rows]

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        if not symbols:
            return {}

        stmt = (
            select(
                ConceptMemberDB.symbol,
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
            )
            .join(ConceptsDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol.in_(symbols),
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()

        out: dict[str, list[ConceptBriefVO]] = {s: [] for s in symbols}
        for r in rows:
            out[r.symbol].append(self._to_vo(r.id, r.name, r.source))
        return out

    async def list_concepts_by_symbol_grouped(
        self, symbol: str
    ) -> list[ConceptGroupedVO]:
        """单股票所属概念（含 concept_type / description，用于详情抽屉「概念」Tab）

        与 list_concepts_by_symbol 的区别：
        - list_concepts_by_symbol：返回 ConceptBriefVO[]（3 字段），用于列表预热
        - list_concepts_by_symbol_grouped：返回 ConceptGroupedVO[]（5 字段），用于抽屉 Tab 渲染
        """
        stmt = (
            select(
                ConceptsDB.id,
                ConceptsDB.name,
                ConceptsDB.source,
                ConceptsDB.concept_type,
                ConceptsDB.description,
            )
            .join(ConceptMemberDB, ConceptMemberDB.concept_id == ConceptsDB.id)
            .where(
                and_(
                    ConceptMemberDB.symbol == symbol,
                    ConceptsDB.is_active == True,
                )
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            ConceptGroupedVO(
                concept_id=r.id,
                name=r.name,
                source=r.source,
                concept_type=r.concept_type,
                description=r.description,
            )
            for r in rows
        ]

    # ── 列表 / 统计 ───────────────────────────────────

    async def list_concepts(
        self,
        q: Optional[str] = None,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Concept], int]:
        stmt = select(ConceptsDB)
        count_stmt = select(func.count()).select_from(ConceptsDB)

        conditions = []
        if q:
            stmt = stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
            count_stmt = count_stmt.where(ConceptsDB.name.ilike(f"%{q}%"))
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
            count_stmt = count_stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
            count_stmt = count_stmt.where(ConceptsDB.is_active == is_active)

        total = (await self._session.execute(count_stmt)).scalar_one()
        stmt = (
            stmt.order_by(ConceptsDB.name)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_entity(r) for r in rows], int(total)

    async def count_concepts(
        self,
        source: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        stmt = select(func.count()).select_from(ConceptsDB)
        if source:
            stmt = stmt.where(ConceptsDB.source == source)
        if is_active is not None:
            stmt = stmt.where(ConceptsDB.is_active == is_active)
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_last_synced_at(self, source: str = "em") -> Optional[datetime]:
        stmt = (
            select(func.max(ConceptsDB.last_synced_at))
            .where(ConceptsDB.source == source)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


# ── Protocol 实现标注 ─────────────────────────────────
ConceptRepoImpl.__implements_protocol__ = ConceptRepository
```

---

## 四、AKShare 采集器实现

### 4.1 ConceptFetcher Protocol（已存在于 protocols.py）

```python
# infrastructure/collectors/protocols.py 中已定义
@runtime_checkable
class ConceptFetcher(Protocol):
    """概念板块采集协议"""

    def fetch_concept_list(self) -> list[Any]:
        """获取概念板块列表"""
        ...

    def fetch_concept_stocks(self, concept_name: str) -> list[Any]:
        """获取概念板块成分股"""
        ...

    @property
    def source_name(self) -> str:
        """数据源名称"""
        ...
```

### 4.2 AkShareConceptFetcher

```python
# infrastructure/collectors/akshare/concept_fetcher.py
"""AKShare 概念板块采集器"""

from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd

from domain.concept.schemas import ConceptListBO, ConceptStockBO
from infrastructure.collectors.protocols import ConceptFetcher

logger = logging.getLogger(__name__)


class AkShareConceptFetcher:
    """东方财富概念板块采集器

    数据源：
    - 概念清单：ak.stock_board_concept_name_em()
    - 概念成分股：ak.stock_board_concept_cons_em(symbol=概念名称)

    同步策略：
    - 全量同步：首次运行时一次性拉取全部概念 + 成分股
    - 增量同步：每周重新拉取概念清单，对比新增/退出
    """

    RETRY_TIMES = 2
    RETRY_DELAY = 1.0   # 秒
    REQUEST_DELAY = 0.3  # 东方财富接口建议间隔
    CONCEPT_TIMEOUT = 10  # 秒

    def __init__(self):
        self._ak = self._ensure_ak()

    def _ensure_ak(self):
        """延迟导入 akshare"""
        try:
            import akshare as ak  # noqa: WPS433
            return ak
        except ImportError:
            raise RuntimeError(
                "AKShare 未安装：pip install akshare"
            )

    @property
    def source_name(self) -> str:
        return "AkShare"

    # ── 采集 ─────────────────────────────────────────

    def fetch_concept_list(self) -> list[ConceptListBO]:
        """获取全量概念清单"""
        logger.info("AKShare: 开始拉取概念清单")

        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_name_em()
            )
        except Exception as e:
            logger.error("拉取概念清单失败: %s", e)
            return []

        if df is None or df.empty:
            logger.warning("概念清单为空")
            return []

        return self._parse_list(df)

    def fetch_concept_stocks(self, concept_name: str) -> list[ConceptStockBO]:
        """获取指定概念的成分股"""
        logger.debug("AKShare: 拉取概念成分股: %s", concept_name)

        try:
            df = self._fetch_with_retry(
                lambda: self._ak.stock_board_concept_cons_em(symbol=concept_name)
            )
        except Exception as e:
            logger.warning("拉取概念 %s 成分股失败: %s", concept_name, e)
            return []

        if df is None or df.empty:
            return []

        return self._parse_stocks(df, concept_name)

    # ── 解析 ─────────────────────────────────────────

    @staticmethod
    def _parse_list(df: pd.DataFrame) -> list[ConceptListBO]:
        """解析概念清单 DataFrame"""
        # 东方财富字段：板块名称 / 板块代码 / 最新价 / 涨跌额 / 涨跌幅 /
        #               总市值 / 换手率 / 上涨家数 / 下跌家数 / 领涨股票
        items = []
        for _, row in df.iterrows():
            try:
                name = str(row.get("板块名称", "")).strip()
                if not name:
                    continue
                code = str(row.get("板块代码", "")).strip()
                # 上涨家数作为 stock_count 近似
                stock_count = int(row.get("上涨家数", 0) or 0) + int(row.get("下跌家数", 0) or 0)

                items.append(ConceptListBO(
                    name=name,
                    code=code,
                    stock_count=stock_count,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    @staticmethod
    def _parse_stocks(df: pd.DataFrame, concept_name: str) -> list[ConceptStockBO]:
        """解析成分股 DataFrame"""
        # 东方财富字段：序号 / 代码 / 名称 / 最新价 / 涨跌幅 / ...
        items = []
        for _, row in df.iterrows():
            try:
                symbol = str(row.get("代码", "")).zfill(6)
                name = str(row.get("名称", "")).strip()
                if not symbol or len(symbol) != 6:
                    continue

                items.append(ConceptStockBO(
                    symbol=symbol,
                    name=name,
                    rank=int(row.get("序号", 0)) if pd.notna(row.get("序号")) else None,
                ))
            except Exception as e:
                logger.debug("跳过无效行: %s", e)
                continue
        return items

    # ── 辅助 ─────────────────────────────────────────

    def _fetch_with_retry(self, fn, retries: int = RETRY_TIMES) -> pd.DataFrame:
        """带重试的采集"""
        for i in range(retries + 1):
            try:
                time.sleep(self.REQUEST_DELAY)
                return fn()
            except Exception as e:
                if i < retries:
                    logger.debug("请求失败，重试 %d/%d: %s", i + 1, retries, e)
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise
```

---

## 五、采集任务编排

### 5.1 ConceptSyncOperation（参考既有 operation_dispatcher.py）

```python
# infrastructure/tasks/concept_sync_operation.py
"""概念同步任务操作"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from domain.concept.entity import Concept, ConceptMember, ConceptSource
from domain.concept.schemas import ConceptListBO, ConceptStockBO
from domain.concept.repository import ConceptRepository
from infrastructure.collectors.akshare.concept_fetcher import AkShareConceptFetcher

logger = logging.getLogger(__name__)


@dataclass
class ConceptSyncResult:
    """同步结果"""
    total_concepts: int = 0
    total_members: int = 0
    failed_concepts: list[str] = field(default_factory=list)
    elapsed_ms: int = 0
    synced_at: datetime = field(default_factory=datetime.now)


class ConceptSyncOperation:
    """概念同步任务

    步骤：
    1. fetch_concept_list → 全量概念清单
    2. 对每个概念 upsert_concept + upsert_members
    3. 统计失败项，记录结果
    """

    def __init__(
        self,
        repo: ConceptRepository,
        fetcher: Optional[AkShareConceptFetcher] = None,
    ):
        self._repo = repo
        self._fetcher = fetcher or AkShareConceptFetcher()

    async def sync_all(self) -> ConceptSyncResult:
        """全量同步所有概念"""
        start = time.time()
        result = ConceptSyncResult()

        # 1. 拉概念清单
        concept_bos = self._fetcher.fetch_concept_list()
        result.total_concepts = len(concept_bos)
        logger.info("全量同步：获取 %d 个概念", result.total_concepts)

        # 2. 逐个同步
        for i, bo in enumerate(concept_bos):
            try:
                await self._sync_one(bo)
            except Exception as e:
                logger.warning("同步概念 %s 失败: %s", bo.name, e)
                result.failed_concepts.append(bo.name)

            if (i + 1) % 50 == 0:
                logger.info("进度: %d/%d", i + 1, result.total_concepts)

        result.elapsed_ms = int((time.time() - start) * 1000)
        result.synced_at = datetime.now(timezone.utc)
        return result

    async def _sync_one(self, bo: ConceptListBO) -> int:
        """同步单个概念及其成分股"""
        # 1. upsert 概念
        concept = bo.to_entity()
        concept.mark_synced(member_count=0)
        concept = await self._repo.upsert_concept(concept)

        # 2. 拉成分股
        stock_bos = self._fetcher.fetch_concept_stocks(bo.name)
        concept.stock_count = len(stock_bos)
        concept.mark_synced(member_count=len(stock_bos))
        await self._repo.upsert_concept(concept)  # 更新 stock_count

        # 3. upsert 成员
        members = [bo.to_entity(concept.id) for bo in stock_bos]
        return await self._repo.upsert_members(concept.id, members)
```

---

## 六、与其他模块的接口

### 6.1 与 StockPanelComposeRepository 的委托关系

```python
# infrastructure/repositories/panel_compose_repository.py
# 在 StockPanelComposeRepoImpl 中新增：

from domain.concept.repository import ConceptRepository
from domain.concept.value_objects import ConceptBriefVO

class StockPanelComposeRepoImpl:
    def __init__(self, session: AsyncSession, concept_repo: ConceptRepository):
        self._session = session
        self._concept_repo = concept_repo  # 🆕 注入

    async def list_concepts_by_symbols(
        self, symbols: list[str]
    ) -> dict[str, list[ConceptBriefVO]]:
        """批量反向查询概念（委托给 ConceptRepository）"""
        return await self._concept_repo.list_concepts_by_symbols(symbols)
```

### 6.2 与 FetcherRegistry 的注册关系

```python
# infrastructure/collectors/registry.py
from infrastructure.collectors.protocols import ConceptFetcher
from infrastructure.collectors.akshare.concept_fetcher import AkShareConceptFetcher

registry.register_factory(ConceptFetcher, AkShareConceptFetcher)
```

---

## 七、单元测试覆盖要点

| 测试 | 说明 |
|------|------|
| `test_concept_repository.py` | ORM ↔ Entity 转换、upsert 命中/未命中路径、批量反向查询 |
| `test_akshare_concept_fetcher.py` | 解析正常数据/空数据/异常格式 |
| `test_concept_sync_operation.py` | 模拟采集失败时的重试与回退 |
| `test_concept_orm.py` | 索引、约束验证 |

---

## 八、相关文档

- [README.md](../README.md) — 统一设计文档
- [01-domain-design.md](../01-domain-design.md) — 领域层 BO / VO / Entity / Protocol
- [03-application-and-route-design.md](../03-application-and-route-design.md) — DTO / Service / Route
- `docs/PlantUML/Concept/01-class.puml` — 类图
- `docs/PlantUML/Concept/02-data-flow.puml` — 数据流
