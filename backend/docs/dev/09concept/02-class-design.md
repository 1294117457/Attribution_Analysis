# 02 — 概念三期：跨层类图

> 本文档只讲类与字段，不讲调用时序（见 [03-data-flow.md](./03-data-flow.md)）。
>
> 同目录其他文档：
> - [README.md](./README.md) — 总览
> - [01-data-source-decision.md](./01-data-source-decision.md) — 数据源选型
> - [03-data-flow.md](./03-data-flow.md) — 时序图
> - [04-frontend-stockinfo.md](./04-frontend-stockinfo.md) — 前端 StockInfo
> - [05-collect-manage.md](./05-collect-manage.md) — 前端 CollectManage

---

## 一、类图全貌（新增 + 复用）

```mermaid
classDiagram
    direction LR

    namespace 采集层 {
        class AkShareConceptFetcher {
            +fetch_concept_list() list~ConceptListBO~
            +fetch_concept_stocks(name) list~ConceptStockBO~
            +fetch_concept_info_ths(name) ConceptSnapshotBO
            +fetch_concept_index_ths(name) list~ConceptIndexTHBO~
            +fetch_concepts_by_stock(symbol) list~ConceptListBO~
        }

        class AdataConceptFetcher {
            +fetch_concept_list() list~ConceptListBO~  [deprecated]
            +fetch_concept_stocks(name) list~ConceptStockBO~  [deprecated]
            +fetch_concepts_by_stock(symbol) list~ConceptListBO~
        }
    }

    namespace 领域层 {
        class Concept {
            +int id
            +str name
            +ConceptSource source
            +ConceptType concept_type
            +str description
            +int stock_count
            +bool is_active
            +datetime first_seen_at
            +datetime last_synced_at
        }

        class ConceptMember {
            +str symbol
            +int concept_id
            +ConceptSource source
            +datetime joined_at
        }

        class ConceptSnapshot {
            +int id
            +str concept_name
            +float open_price
            +float prev_close
            +float low
            +float high
            +float volume_wan
            +float pct_change
            +int rank_current
            +int rank_total
            +int up_count
            +int down_count
            +float net_inflow_yi
            +float turnover_yi
            +datetime captured_at
            +ConceptSource source
        }

        class ConceptIndexTH {
            +int id
            +str concept_name
            +date trade_date
            +float open
            +float high
            +float low
            +float close
            +int64 volume
            +float amount
            +datetime captured_at
        }

        class ConceptSnapshotVO {
            +str concept_name
            +float pct_change
            +int rank_current
            +int rank_total
            +str rank_label  "191/390"
            +str up_down_label  "90/372"
            +str color  "up"/"down"/"flat"
            +datetime captured_at
        }

        class ConceptIndexTHVO {
            +str concept_name
            +date trade_date
            +float open
            +float high
            +float low
            +float close
            +int64 volume
            +float amount
        }
    }

    namespace 仓储层 {
        class ConceptRepository {
            <<Protocol>>
            +upsert_concept(c) Concept
            +upsert_members(cid, members) int
            +get_concept_by_id(id) Concept
            +list_concepts_by_symbol(sym) list~ConceptBriefVO~
            +list_concepts_by_symbols(syms) dict
            +list_concepts_by_symbol_grouped(sym) list~ConceptGroupedVO~
            +list_concepts(q, source, is_active, page, page_size) tuple
            +count_concepts(source, is_active) int
            +get_last_synced_at(source) datetime
        }

        class ConceptRepositoryExt {
            <<Protocol - 本期新增>>
            +upsert_single_member(symbol, concept_id, source) bool
            +get_concept_id_by_name(name, source) int
            +upsert_snapshot(snap) bool
            +upsert_index_th(rows) int
            +list_snapshot(name) ConceptSnapshotVO
        }
    }

    namespace 应用层 {
        class ConceptAppService {
            +sync_concepts(req) ConceptSyncResultVO
            +fetch_concepts_by_stock(sym) list~ConceptLiveVO~
            +get_tab_content_for_symbol(sym, merge_live) list~dict~
        }

        class ConceptSyncOperation {
            +sync_all() ConceptSyncResult
            -_sync_one(bo) int
        }

        class ConceptMembershipSyncOperation {
            <<本期新增>>
            +sync_membership() MembershipSyncResult
            -_sync_one_stock(symbol) int
            -_resolve_concept_id(name, source) int
        }

        class ConceptSnapshotSyncOperation {
            <<本期新增>>
            +sync_snapshots() SnapshotSyncResult
            -_sync_one(name) bool
            -_parse_pct_change(s) float
        }

        class ConceptIndexTHSyncOperation {
            <<本期 P1>>
            +sync_index_th(start, end) IndexSyncResult
            -_sync_one(name, start, end) int
        }
    }

    namespace 路由层 {
        class ConceptRoute {
            +GET /concepts/
            +GET /concepts/{name}
            +GET /concepts/by-symbol/{symbol}
            +GET /concepts/tab-by-symbol/{symbol}
            +GET /concepts/live-by-symbol/{symbol}
            +GET /concepts/{name}/snapshot
            +GET /concepts/{name}/index-th
            +POST /concepts/sync/membership
        }
    }

    namespace 前端 {
        class ConceptTag {
            +ConceptBrief concept
            +ConceptSnapshotVO snapshot
            +render() void
        }

        class ConceptTab {
            +string symbol
            +ConceptGroupedVO[] groups
            +ConceptSnapshotVO[] snapshots
            +onSnapshotTick() void
        }

        class CollectManage_ConceptTab {
            +enum subTask  "list"/"membership"/"snapshot"
            +startMembership() void
            +startSnapshot() void
        }
    }

    AkShareConceptFetcher --> ConceptListBO
    AkShareConceptFetcher --> ConceptSnapshotBO
    AkShareConceptFetcher --> ConceptIndexTHBO
    AdataConceptFetcher --> ConceptListBO

    ConceptRepository <|.. ConceptRepositoryExt
    ConceptRepositoryExt --> Concept : upsert
    ConceptRepositoryExt --> ConceptMember : upsert_single
    ConceptRepositoryExt --> ConceptSnapshot : upsert
    ConceptRepositoryExt --> ConceptIndexTH : upsert

    ConceptAppService --> ConceptRepositoryExt
    ConceptMembershipSyncOperation --> AdataConceptFetcher
    ConceptMembershipSyncOperation --> ConceptRepositoryExt
    ConceptSnapshotSyncOperation --> AkShareConceptFetcher
    ConceptSnapshotSyncOperation --> ConceptRepositoryExt
    ConceptIndexTHSyncOperation --> AkShareConceptFetcher
    ConceptIndexTHSyncOperation --> ConceptRepositoryExt

    ConceptRoute --> ConceptAppService
    ConceptRoute --> ConceptMembershipSyncOperation
    ConceptRoute --> ConceptSnapshotSyncOperation

    ConceptTag --> ConceptSnapshotVO
    ConceptTab --> ConceptSnapshotVO
    CollectManage_ConceptTab --> ConceptMembershipSyncOperation
```

---

## 二、新增 BO（采集层 → 应用层）

### 2.1 `ConceptSnapshotBO`（akshare THS info）

来自 `ak.stock_board_concept_info_ths(symbol=...)` 的 10 行 DataFrame。

```python
class ConceptSnapshotBO(BaseModel):
    concept_name: str
    open_price: float            # 今开
    prev_close: float            # 昨收
    low: float                   # 最低
    high: float                  # 最高
    volume_wan: float            # 成交量(万手)
    pct_change_raw: str          # 板块涨幅, 例 "-1.32%"（保留原始字符串，应用层再解析）
    rank_label: str              # 涨幅排名, 例 "191/390"
    up_down_label: str           # 涨跌家数, 例 "90/372"
    net_inflow_yi: float         # 资金净流入(亿)
    turnover_yi: float           # 成交额(亿)
    source: ConceptSource = THS
    captured_at: datetime        # 调用时刻

    def to_pct_change(self) -> float:
        """解析 '-1.32%' → -1.32"""
        return float(self.pct_change_raw.rstrip('%'))
```

### 2.2 `ConceptIndexTHBO`（akshare THS index）

来自 `ak.stock_board_concept_index_ths(symbol=..., start_date=..., end_date=...)`。

```python
class ConceptIndexTHBO(BaseModel):
    concept_name: str
    trade_date: date
    open: float                  # 开盘价
    high: float                  # 最高价
    low: float                   # 最低价
    close: float                 # 收盘价
    volume: int64                # 成交量
    amount: float                # 成交额
    source: ConceptSource = THS
    captured_at: datetime
```

---

## 三、新增 VO（应用层 → 前端）

### 3.1 `ConceptSnapshotVO`

```python
class ConceptSnapshotVO(BaseModel):
    concept_name: str
    pct_change: float            # 1.32 / -1.32 / 0.0（已解析）
    rank_current: int            # 191
    rank_total: int              # 390
    rank_label: str              # "191/390"（前端直接展示）
    up_count: int                # 90
    down_count: int              # 372
    up_down_label: str           # "90/372"
    net_inflow_yi: float         # -199.38
    turnover_yi: float           # 1960.19
    color: Literal["up","down","flat"]  # 前端 Tag 染色（红/绿/灰）
    captured_at: datetime

    @classmethod
    def from_db(cls, db) -> "ConceptSnapshotVO":
        """DB → VO；自动判定 color"""
        color = "flat"
        if db.pct_change > 0:
            color = "up"
        elif db.pct_change < 0:
            color = "down"
        return cls(...)
```

### 3.2 `ConceptIndexTHVO`

```python
class ConceptIndexTHVO(BaseModel):
    concept_name: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int64
    amount: float
```

---

## 四、新增 ORM

### 4.1 `ConceptSnapshotDB`

```python
class ConceptSnapshotDB(Base):
    __tablename__ = "concept_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_name: Mapped[str] = mapped_column(String(100), index=True)
    open_price: Mapped[float]
    prev_close: Mapped[float]
    low: Mapped[float]
    high: Mapped[float]
    volume_wan: Mapped[float]
    pct_change: Mapped[float]                # 已解析为 float
    rank_current: Mapped[int]
    rank_total: Mapped[int]
    up_count: Mapped[int]
    down_count: Mapped[int]
    net_inflow_yi: Mapped[float]
    turnover_yi: Mapped[float]
    source: Mapped[str] = "ths"
    captured_at: Mapped[datetime]

    __table_args__ = (
        # 每概念每 source 仅保留最新一条
        Index("ix_concept_snapshots_name_captured", "concept_name", "captured_at"),
    )
```

> **注意**：不像 `concepts` 表那样做"唯一键 + 覆盖"，`concept_snapshots` 是**时序数据**，保留历史快照便于追溯。表里会有 N 条/概念。

### 4.2 `ConceptIndexTHDB`

```python
class ConceptIndexTHDB(Base):
    __tablename__ = "concept_index_ths"

    id: Mapped[int] = mapped_column(primary_key=True)
    concept_name: Mapped[str] = mapped_column(String(100), index=True)
    trade_date: Mapped[date]
    open: Mapped[float]
    high: Mapped[float]
    low: Mapped[float]
    close: Mapped[float]
    volume: Mapped[int64]
    amount: Mapped[float]
    captured_at: Mapped[datetime]

    __table_args__ = (
        UniqueConstraint("concept_name", "trade_date",
                         name="uq_concept_index_th_name_date"),
    )
```

---

## 五、仓储新增方法

### 5.1 `upsert_single_member`（M:N 累加）

```python
async def upsert_single_member(
    self,
    symbol: str,
    concept_id: int,
    source: ConceptSource,
) -> bool:
    """单条插入（冲突 NOOP）

    用于 adata 反查模式：一只只股票写入多个 concept。
    与 upsert_members（全量覆盖）语义不同：
    - upsert_members：DELETE + INSERT（先清空再批量写）
    - upsert_single_member：ON CONFLICT DO NOTHING（累加）

    Returns: True 新插入；False 已存在
    """
    stmt = pg_insert(ConceptMemberDB).values(
        symbol=symbol,
        concept_id=concept_id,
        source=source.value,
        joined_at=datetime.now(timezone.utc),
    ).on_conflict_do_nothing(
        index_elements=["symbol", "concept_id"],
    )
    result = await self._session.execute(stmt)
    await self._session.commit()
    return result.rowcount > 0
```

### 5.2 `get_concept_id_by_name`

```python
async def get_concept_id_by_name(
    self,
    name: str,
    source: ConceptSource = ConceptSource.THS,
) -> Optional[int]:
    """根据 (name, source) 查询概念 id（不存在返回 None）

    用于 adata 反查后回填 concept_id：
    - 若概念已入库（清单同步过）→ 返回已有 id
    - 若未入库 → 返回 None，应用层应先 upsert_concept 再获取
    """
    stmt = select(ConceptsDB.id).where(
        and_(
            ConceptsDB.name == name,
            ConceptsDB.source == source.value,
        )
    )
    row = (await self._session.execute(stmt)).scalar_one_or_none()
    return row
```

### 5.3 `upsert_snapshot`

```python
async def upsert_snapshot(self, snap: ConceptSnapshot) -> bool:
    """插入新快照（不覆盖历史）

    Returns: True
    """
    db = ConceptSnapshotDB(
        concept_name=snap.concept_name,
        open_price=snap.open_price,
        prev_close=snap.prev_close,
        low=snap.low,
        high=snap.high,
        volume_wan=snap.volume_wan,
        pct_change=snap.pct_change,
        rank_current=snap.rank_current,
        rank_total=snap.rank_total,
        up_count=snap.up_count,
        down_count=snap.down_count,
        net_inflow_yi=snap.net_inflow_yi,
        turnover_yi=snap.turnover_yi,
        source=snap.source.value,
        captured_at=snap.captured_at,
    )
    self._session.add(db)
    await self._session.commit()
    return True
```

### 5.4 `upsert_index_th`

```python
async def upsert_index_th(self, rows: list[ConceptIndexTH]) -> int:
    """批量 upsert 概念指数日 K（按 (name, trade_date) 冲突更新）

    Returns: 实际写入条数
    """
    if not rows:
        return 0
    values = [
        {
            "concept_name": r.concept_name,
            "trade_date": r.trade_date,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": r.volume,
            "amount": r.amount,
            "captured_at": r.captured_at,
        }
        for r in rows
    ]
    stmt = pg_insert(ConceptIndexTHDB).values(values).on_conflict_do_update(
        index_elements=["concept_name", "trade_date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "volume": stmt.excluded.volume,
            "amount": stmt.excluded.amount,
            "captured_at": stmt.excluded.captured_at,
        },
    )
    result = await self._session.execute(stmt)
    await self._session.commit()
    return result.rowcount
```

### 5.5 `list_snapshot`（前端用）

```python
async def list_snapshot(
    self,
    concept_name: str,
) -> Optional[ConceptSnapshotVO]:
    """取指定概念最新一条快照（按 captured_at DESC 排序取 1 条）"""
    stmt = (
        select(ConceptSnapshotDB)
        .where(ConceptSnapshotDB.concept_name == concept_name)
        .order_by(ConceptSnapshotDB.captured_at.desc())
        .limit(1)
    )
    row = (await self._session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return ConceptSnapshotVO.from_db(row)
```

---

## 六、新增应用层 Service

### 6.1 `ConceptMembershipSyncOperation`

```python
class ConceptMembershipSyncOperation:
    """成分股 M:N 反查累加同步

    步骤：
    1. 从 DB 拉 stock_infos 表所有 (symbol, list_status='L') 的股票
    2. 逐只股票调用 adata.get_concept_east(symbol)
    3. 对返回的每个 concept_name：
       a. 查 (name, source=ths) 是否已有；无则 upsert_concept
       b. 取 concept_id，调用 upsert_single_member 写入 stock_concept_members
    4. 统计：成功股票数 / 失败股票数 / 新增关联数 / 总关联数

    性能：
    - 全量 ~5000 只股票 × 0.5s = 42 分钟
    - 增量：仅同步 stock_infos.first_seen_at > 上次同步时间的股票

    失败容忍：
    - 单只股票反查失败 → 累计 fail，不中断
    - 单只股票入库失败 → 累计 fail，不中断
    """

    def __init__(
        self,
        repo: ConceptRepository,
        adata_fetcher: AdataConceptFetcher,
        stock_info_repo: StockInfoRepository,
    ):
        self._repo = repo
        self._adata = adata_fetcher
        self._stock_info_repo = stock_info_repo

    async def sync_membership(
        self,
        mode: Literal["full", "incremental"] = "full",
    ) -> MembershipSyncResult:
        ...

    async def _sync_one_stock(self, symbol: str) -> int:
        """返回新增关联数"""
        ...
```

### 6.2 `ConceptSnapshotSyncOperation`

```python
class ConceptSnapshotSyncOperation:
    """概念行情快照采集（每 5 分钟）

    步骤：
    1. 从 DB 拉所有 is_active=True 的 concepts（375 个）
    2. 逐个调用 ak.stock_board_concept_info_ths(name)
    3. 解析 → ConceptSnapshot
    4. upsert_snapshot（INSERT 新行，保留历史）
    5. 统计：成功数 / 失败数

    性能：
    - 375 个 × 0.3s = 约 2 分钟/全量
    - 调度：交易日 09:30-15:00 每 5 分钟
    """

    def __init__(
        self,
        repo: ConceptRepository,
        akshare_fetcher: AkShareConceptFetcher,
    ):
        ...

    async def sync_snapshots(self) -> SnapshotSyncResult:
        ...

    async def _sync_one(self, name: str) -> bool:
        ...

    @staticmethod
    def _parse_pct_change(raw: str) -> float:
        """'-1.32%' → -1.32"""
        return float(raw.rstrip('%'))
```

### 6.3 `ConceptIndexTHSyncOperation`（P1）

```python
class ConceptIndexTHSyncOperation:
    """概念指数日 K 采集（按需触发）

    步骤：
    1. 从 DB 拉所有 is_active=True 的 concepts
    2. 逐个调用 ak.stock_board_concept_index_ths(name, start_date, end_date)
    3. upsert_index_th（按 (name, date) 冲突更新）
    """

    def __init__(self, ...): ...

    async def sync_index_th(
        self,
        start_date: date,
        end_date: date,
    ) -> IndexSyncResult:
        ...
```

---

## 七、BaseCollectTask 子类（采集管理用）

| Task 类 | name | run 入口 |
|:---|:---|:---|
| `ConceptCollectTask`（已有） | `concept` | 清单同步 |
| `MembershipCollectTask` 🆕 | `concept_membership` | 反查累加 |
| `SnapshotCollectTask` 🆕 | `concept_snapshot` | 行情快照 |

```python
class MembershipCollectTask(BaseCollectTask):
    name = "concept_membership"
    description = "概念-股票 M:N 反查累加（adata 反查）"

    async def estimate_total(self, params: dict) -> int:
        mode = params.get("mode", "full")
        if mode == "incremental":
            return await self._count_new_stocks_since_last_sync()
        return await self._count_active_stocks()

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        # 调 ConceptMembershipSyncOperation
        ...
```

```python
class SnapshotCollectTask(BaseCollectTask):
    name = "concept_snapshot"
    description = "概念行情快照采集（THS info）"

    async def estimate_total(self, params: dict) -> int:
        return await self._repo.count_active_concepts()

    async def run(self, params: dict, on_unit_done) -> TaskSummary:
        # 调 ConceptSnapshotSyncOperation
        ...
```

---

## 八、路由新增

| 方法 | 路径 | 用途 |
|:---|:---|:---|
| GET | `/api/v1/concepts/{name}/snapshot` | 取单概念最新快照 |
| GET | `/api/v1/concepts/{name}/index-th?start_date=&end_date=` | 取概念指数日 K |
| POST | `/api/v1/concepts/sync/membership` | 触发 M:N 反查同步 |

```python
@router.get("/{name}/snapshot")
async def get_concept_snapshot(name: str) -> ConceptSnapshotVO:
    """取单概念最新行情快照"""
    return await concept_service.get_snapshot(name)

@router.get("/{name}/index-th")
async def get_concept_index_th(
    name: str,
    start_date: date,
    end_date: date,
) -> list[ConceptIndexTHVO]:
    """取概念指数日 K"""
    return await concept_service.get_index_th(name, start_date, end_date)

@router.post("/sync/membership")
async def sync_membership(
    req: MembershipSyncRequest,
) -> TaskCreatedResponse:
    """触发 M:N 反查同步任务"""
    return await collect_task_dispatcher.create(
        task_type="concept_membership",
        params=req.model_dump(),
    )
```

---

## 九、前端类型（增量）

```typescript
// views/stock-info/api.ts
export interface ConceptSnapshotVO {
  concept_name: string
  pct_change: number          // -1.32
  rank_current: number        // 191
  rank_total: number          // 390
  rank_label: string          // "191/390"
  up_count: number
  down_count: number
  up_down_label: string       // "90/372"
  net_inflow_yi: number
  turnover_yi: number
  color: 'up' | 'down' | 'flat'
  captured_at: string
}

export interface ConceptIndexTHVO {
  concept_name: string
  trade_date: string          // ISO date
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
}

// 新增 API
export function getConceptSnapshot(name: string) {
  return request.get<ConceptSnapshotVO>(`/concepts/${name}/snapshot`)
}

export function getConceptIndexTH(name: string, start: string, end: string) {
  return request.get<ConceptIndexTHVO[]>(
    `/concepts/${name}/index-th?start_date=${start}&end_date=${end}`
  )
}

export function syncMembership(params: { mode: 'full' | 'incremental' }) {
  return request.post<{ task_id: number; message: string }>(
    '/concepts/sync/membership',
    params,
  )
}
```

---

## 十、关联改动（08concept 已实现部分）

- ✅ `ConceptBriefVO.concept_type`（08concept）
- ✅ `ConceptMainVO` / `ConceptTag` 组件（08concept）
- ✅ `StockInfoList` 主概念 Tag 列（08concept）
- ✅ 详情抽屉「概念」Tab 按类型分组（08concept）

**本期新增**：涨跌数据 → 主概念 Tag 染色；ConceptTab 加"涨跌"列。

---

## 十一、命名一致性（按 `03dataana §0.1`）

| 类型 | 类名 | 表名 | 一致？ |
|:---|:---|:---|:---:|
| 实体 | `ConceptSnapshot` | `concept_snapshots` | ✅ |
| 实体 | `ConceptIndexTH` | `concept_index_ths` | ✅ |
| VO | `ConceptSnapshotVO` | — | ✅ |
| VO | `ConceptIndexTHVO` | — | ✅ |
| BO | `ConceptSnapshotBO` | — | ✅ |
| BO | `ConceptIndexTHBO` | — | ✅ |
| 字段 | `concept_name` (snake_case) | — | ✅ |
| 数据源 | `ths` / `em` / `adata` | — | ✅ |

> **`concept_index_ths`** 表名解释：「`concept_index` + `_th` + `s`」表示"同花顺概念指数的复数表"。`_th` 后缀避免和未来可能的 `concept_index_em` 冲突。

---

## 十二、测试要点

| 测试 | 类型 | 覆盖 |
|:---|:---|:---|
| `test_concept_snapshot_vo.py` | 单元 | `color` 判定（>0/<0/=0） |
| `test_concept_snapshot_sync.py` | 单元 | `_parse_pct_change` 解析（含 `+`/`-`/`%` 边界） |
| `test_upsert_single_member.py` | 单元 | 同 (symbol, concept_id) 重复插入 NOOP |
| `test_membership_sync.py` | 单元 | 全量 / 增量模式计数 |
| `test_route_snapshot.py` | 集成 | `GET /concepts/{name}/snapshot` 200 / 404 |
| `test_route_membership_sync.py` | 集成 | `POST /concepts/sync/membership` 创建任务 |
| `ConceptTag.spec.ts` | 单元 | 涨跌染色（红/绿/灰）|
| `ConceptTab.spec.ts` | 单元 | 新增"涨跌"列渲染 |
| `CollectManage.spec.ts` | 集成 | 三子任务 UI |
