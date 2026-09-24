# 数据分析层 — 前后端实施开发指南

> **本文档目的**：step 6 数据分析层的前后端完整实施路线图。包含表改名、14 张新表建模、新增采集器、API 路由、前端视图，全量代码实现指引。
>
> **前置条件**：已确认 `backend/docs/03dataana/01data.md` 表设计方案；本文档专注**代码落地**。

---

## 文档结构

| # | 章节 | 内容 |
|---|------|------|
| 1 | [后端 ORM 与模型](#1-后端-orm-与模型) | 已有表改名 + 14 张新 ORM 模型 |
| 2 | [后端领域层](#2-后端领域层) | 领域实体、值对象、仓储接口 |
| 3 | [后端仓储实现](#3-后端仓储实现) | 14 张新表的仓储实现 + 改名表的仓储更新 |
| 4 | [后端采集器](#4-后端采集器) | 14 个 Tushare fetcher + parser + 通用采集服务 |
| 5 | [后端应用服务](#5-后端应用服务) | 应用层 DTO / Service |
| 6 | [后端 API 路由](#6-后端-api-路由) | REST 路由设计 + 请求/响应 schema |
| 7 | [数据库迁移](#7-数据库迁移) | Alembic 迁移脚本（含表改名） |
| 8 | [前端](#8-前端) | API 封装、视图组件、看板 |
| 9 | [实施阶段](#9-实施阶段) | P0-P5 实施顺序与验收标准 |

---

## 1. 后端 ORM 与模型

### 1.1 目录结构

```
backend/src/infrastructure/database/models/
├── __init__.py          ← 全量导出所有 ORM 模型
├── kline.py             ← [改名] tech_kline_daily (原 daily_kline)
├── stock_info.py        ← [已有] stock_info (不变)
├── pool.py              ← [已有] stock_pool / stock_pool_member / pool_operation
├── tech_kline.py        ← [改名后重写] tech_kline_daily ORM（见 1.3）
├── fin_report.py        ← [新建] fin_report
├── fin_daily_basic.py   ← [改名] fin_daily_basic (原 daily_basic_metric)
├── cap_margin.py        ← [改名] cap_margin (原 margin_data)
├── cap_moneyflow.py     ← [新建] cap_moneyflow
├── cap_margin_detail.py ← [新建] cap_margin_detail
├── cap_top_list.py      ← [新建] cap_top_list
├── cap_top_inst.py      ← [新建] cap_top_inst
├── cap_block_trade.py   ← [新建] cap_block_trade
├── cap_holder_num.py   ← [新建] cap_holder_num
├── fin_top10_holders.py ← [新建] fin_top10_holders
├── fin_top10_float.py   ← [新建] fin_top10_floatholders
├── base_adj_factor.py   ← [新建] base_adj_factor
├── base_dividend.py    ← [新建] base_dividend
├── base_suspend.py     ← [新建] base_suspend
├── base_name_change.py  ← [新建] base_name_change
├── mkt_calendar.py     ← [改名] mkt_calendar (原 trading_calendar)
├── mkt_market_daily.py ← [改名] mkt_market_daily (原 market_daily)
├── mkt_sector_daily.py ← [新建] mkt_sector_daily
├── mkt_index_member.py ← [新建] mkt_index_member
└── collection_log.py  ← [已有] data_collection_log (不变)
```

> **注意**：由于 `kline.py` 已有，且类名 `DailyKlineDB` 对应旧名，改为 `tech_kline_daily` 需要重写整个文件（见 1.3）。

### 1.2 ORM 命名约定

| 概念 | 规则 | 示例 |
|------|------|------|
| 类名（Python） | 单数 + PascalCase + 前缀 | `CapMoneyflowDB` |
| 物理表名 `__tablename__` | 复数 snake_case + 前缀 | `cap_moneyflows` |
| 字段名 | snake_case，与 tushare 输出一致 | `net_mf_amount` |
| 主键 | `id: Mapped[int]` + `autoincrement=True` | |
| 逻辑外键 | `symbol: Mapped[str]` + `index=True`（不强加 FK 约束） | |
| 时间戳 | 使用 `TimestampMixin`（`created_at` / `updated_at`） | |

### 1.3 已有名改动：`kline.py` → `tech_kline_daily`

> **原因**：表名从 `daily_klines` 改为 `tech_kline_dailys`，类名从 `DailyKlineDB` 改为 `TechKlineDailyDB`。

**新文件路径**：`infrastructure/database/models/tech_kline.py`

```python
"""日 K 线 ORM 模型（含 17 个技术指标列）"""

from datetime import date
from sqlalchemy import String, Float, Integer, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class TechKlineDailyDB(Base, TimestampMixin):
    """日K线数据库模型（PO）

    物理表名: tech_kline_dailys
    UK: (symbol, date)
    """

    __tablename__ = "tech_kline_dailys"

    # ── 主键 ─────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 基础字段 ────────────────────────────────────────
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 技术指标（17 列展宽）────────────────────────────
    # 均线
    ma5:  Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma60: Mapped[float | None] = mapped_column(Float, nullable=True)
    # EMA
    ema12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema26: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MACD
    macd_dif:  Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea:  Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_bar:  Mapped[float | None] = mapped_column(Float, nullable=True)
    # RSI
    rsi6:  Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Float, nullable=True)
    # KDJ
    kdj_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Float, nullable=True)
    # BOLL
    boll_up:  Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_dn:  Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_tech_kline_symbol_date"),
        Index("ix_tech_kline_symbol_date", "symbol", "date"),
    )

    def __repr__(self) -> str:
        return f"<TechKlineDailyDB {self.symbol} {self.date} close={self.close}>"
```

> **旧文件处理**：`kline.py` 删除（或重命名为 `tech_kline.py` 并清空内容后重写）。

### 1.4 14 张新 ORM 模型模板

#### 模板 A — 日频表（有 UK symbol + trade_date）

```python
"""cap_moneyflow — 个股资金流向 ORM"""

from datetime import date
from sqlalchemy import String, Float, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class CapMoneyflowDB(Base, TimestampMixin):
    """个股资金流向

    物理表名: cap_moneyflows
    UK: (symbol, trade_date)
    """

    __tablename__ = "cap_moneyflows"

    # ── 主键（不暴露给领域层，纯 DB 维度）─────────────
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── UK 字段 ──────────────────────────────────────
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)

    # ── 资金字段 ──────────────────────────────────────
    buy_sm_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_sm_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_sm_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_sm_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_md_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_md_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_md_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_md_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_lg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_lg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_lg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_lg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_elg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    buy_elg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_elg_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    sell_elg_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_mf_vol: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_mf_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── 审计字段 ──────────────────────────────────────
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", name="uq_cap_moneyflow_symbol_date"),
        Index("ix_cap_moneyflow_date", "trade_date"),
    )
```

#### 模板 B — 季频表（UK 含 end_date + ann_date）

```python
"""fin_top10_holders — 前十大股东 ORM"""

from datetime import date
from sqlalchemy import String, Float, Date, Integer, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class FinTop10HolderDB(Base, TimestampMixin):
    """前十大股东

    物理表名: fin_top10_holders
    UK: (symbol, end_date, ann_date, holder_name)
    """

    __tablename__ = "fin_top10_holders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    holder_name: Mapped[str] = mapped_column(String(128), nullable=False)
    hold_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_float_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    hold_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    holder_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")

    __table_args__ = (
        UniqueConstraint(
            "symbol", "end_date", "ann_date", "holder_name",
            name="uq_fin_top10_holders_uk",
        ),
        Index("ix_fin_top10_holders_symbol", "symbol"),
        Index("ix_fin_top10_holders_date", "end_date"),
    )
```

#### 模板 C — 事件表（无 trade_date，UK 含 start_date）

```python
"""base_name_change — 股票曾用名 ORM"""

from datetime import date
from sqlalchemy import String, Date, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base
from infrastructure.database.mixins import TimestampMixin


class BaseNameChangeDB(Base, TimestampMixin):
    """股票曾用名

    物理表名: base_name_changes
    UK: (symbol, start_date)
    """

    __tablename__ = "base_name_changes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_source: Mapped[str] = mapped_column(String(16), default="tushare")

    __table_args__ = (
        UniqueConstraint("symbol", "start_date", name="uq_base_name_change_uk"),
        Index("ix_base_name_change_symbol", "symbol"),
    )
```

### 1.5 完整 ORM 模型清单

下表直接对应 `infrastructure/database/models/` 下的文件：

| 文件名 | 类名 | 物理表名 | UK | 来源 |
|--------|------|----------|----|------|
| `tech_kline.py` | `TechKlineDailyDB` | `tech_kline_dailys` | `(symbol, date)` | 改名自 `kline.py` |
| `fin_report.py` | `FinReportDB` | `fin_reports` | `(symbol, end_date)` | 新建 |
| `fin_daily_basic.py` | `FinDailyBasicDB` | `fin_daily_basics` | `(symbol, trade_date)` | 改名 |
| `cap_margin.py` | `CapMarginDB` | `cap_margins` | `(exchange_id, trade_date)` | 改名 |
| `cap_moneyflow.py` | `CapMoneyflowDB` | `cap_moneyflows` | `(symbol, trade_date)` | 新建 |
| `cap_margin_detail.py` | `CapMarginDetailDB` | `cap_margin_details` | `(symbol, trade_date)` | 新建 |
| `cap_top_list.py` | `CapTopListDB` | `cap_top_lists` | `(trade_date, symbol, reason)` | 新建 |
| `cap_top_inst.py` | `CapTopInstDB` | `cap_top_insts` | `(id)` + `(symbol, trade_date)` | 新建 |
| `cap_block_trade.py` | `CapBlockTradeDB` | `cap_block_trades` | `(id)` + `(symbol, trade_date)` | 新建 |
| `cap_holder_num.py` | `CapHolderNumDB` | `cap_holder_nums` | `(symbol, end_date)` | 新建 |
| `fin_top10_holders.py` | `FinTop10HolderDB` | `fin_top10_holders` | `(symbol, end_date, ann_date, holder_name)` | 新建 |
| `fin_top10_float.py` | `FinTop10FloatDB` | `fin_top10_floatholders` | 同上 | 新建 |
| `base_adj_factor.py` | `BaseAdjFactorDB` | `base_adj_factors` | `(symbol, trade_date)` | 新建 |
| `base_dividend.py` | `BaseDividendDB` | `base_dividends` | `(symbol, end_date, div_proc)` | 新建 |
| `base_suspend.py` | `BaseSuspendDB` | `base_suspends` | `(id)` + `(symbol, trade_date)` | 新建 |
| `base_name_change.py` | `BaseNameChangeDB` | `base_name_changes` | `(symbol, start_date)` | 新建 |
| `mkt_calendar.py` | `MktCalendarDB` | `mkt_calendars` | `(cal_date, exchange)` | 改名 |
| `mkt_market_daily.py` | `MktMarketDailyDB` | `mkt_market_dailys` | `(market, trade_date)` | 改名 |
| `mkt_sector_daily.py` | `MktSectorDailyDB` | `mkt_sector_dailys` | `(sector_type, sector_code, trade_date)` | 新建 |
| `mkt_index_member.py` | `MktIndexMemberDB` | `mkt_index_members` | `(sector_type, sector_code, symbol, effective_date)` | 新建 |

---

## 2. 后端领域层

### 2.1 目录结构

```
backend/src/domain/
├── kline/
│   ├── entity.py       ← [已有] Kline (不变，只需改 UK 注释)
│   ├── repository.py   ← [已有] KlineRepository 接口 (不变)
│   ├── schemas.py       ← [已有] KlineBO (不变)
│   └── value_objects.py ← [已有] StockCode (不变)
├── stock_info/         ← [已有，不变]
├── stock_pool/         ← [已有，不变]
├── fin_report/         ← [新建] FinReport 领域实体
├── fin_daily_basic/    ← [新建] FinDailyBasic 领域实体
├── cap_moneyflow/      ← [新建] CapMoneyflow 领域实体
├── cap_margin_detail/   ← [新建] CapMarginDetail 领域实体
├── cap_top_list/       ← [新建] CapTopList 领域实体
├── cap_top_inst/       ← [新建] CapTopInst 领域实体
├── cap_block_trade/    ← [新建] CapBlockTrade 领域实体
├── cap_holder_num/    ← [新建] CapHolderNum 领域实体
├── fin_top10_holders/  ← [新建] FinTop10Holder 领域实体
├── fin_top10_float/    ← [新建] FinTop10FloatHolder 领域实体
├── base_adj_factor/    ← [新建] BaseAdjFactor 领域实体
├── base_dividend/      ← [新建] BaseDividend 领域实体
├── base_suspend/       ← [新建] BaseSuspend 领域实体
├── base_name_change/   ← [新建] BaseNameChange 领域实体
├── mkt_calendar/       ← [新建] MktCalendar 领域实体
├── mkt_market_daily/    ← [新建] MktMarketDaily 领域实体
├── mkt_sector_daily/    ← [新建] MktSectorDaily 领域实体
└── mkt_index_member/   ← [新建] MktIndexMember 领域实体
```

### 2.2 领域实体命名模式

每个新领域的 `entity.py` 结构统一：

```python
"""cap_moneyflow — 领域实体"""

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class CapMoneyflow:
    """个股资金流向（领域实体）"""

    symbol: str
    trade_date: date
    # 小单
    buy_sm_vol: Optional[float] = None
    buy_sm_amount: Optional[float] = None
    sell_sm_vol: Optional[float] = None
    sell_sm_amount: Optional[float] = None
    # 中单
    buy_md_vol: Optional[float] = None
    buy_md_amount: Optional[float] = None
    sell_md_vol: Optional[float] = None
    sell_md_amount: Optional[float] = None
    # 大单
    buy_lg_vol: Optional[float] = None
    buy_lg_amount: Optional[float] = None
    sell_lg_vol: Optional[float] = None
    sell_lg_amount: Optional[float] = None
    # 特大单
    buy_elg_vol: Optional[float] = None
    buy_elg_amount: Optional[float] = None
    sell_elg_vol: Optional[float] = None
    sell_elg_amount: Optional[float] = None
    # 净流入
    net_mf_vol: Optional[float] = None
    net_mf_amount: Optional[float] = None
    data_source: str = "tushare"
```

### 2.3 领域仓储接口命名模式

每个新领域下 `repository.py`：

```python
"""cap_moneyflow — 领域仓储接口"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from domain.cap_moneyflow.entity import CapMoneyflow


class CapMoneyflowRepository(ABC):
    """个股资金流向仓储接口（领域层定义，基础设施层实现）"""

    @abstractmethod
    async def save(self, entity: CapMoneyflow) -> CapMoneyflow: ...

    @abstractmethod
    async def save_batch(self, entities: list[CapMoneyflow]) -> int: ...

    @abstractmethod
    async def find_by_symbol_date(
        self, symbol: str, trade_date: date
    ) -> Optional[CapMoneyflow]: ...

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMoneyflow]: ...
```

---

## 3. 后端仓储实现

### 3.1 目录结构

```
backend/src/infrastructure/repositories/
├── __init__.py
├── kline_repository.py     ← [已有] 需改 UK 名（uq_kline_symbol_date → uq_tech_kline_symbol_date）
├── stock_repository.py      ← [已有，不变]
├── pool_repository.py      ← [已有，不变]
├── pool_operation_repository.py ← [已有，不变]
├── cap_moneyflow_repository.py  ← [新建]
├── cap_margin_detail_repository.py ← [新建]
├── cap_top_list_repository.py ← [新建]
├── cap_top_inst_repository.py ← [新建]
├── cap_block_trade_repository.py ← [新建]
├── cap_holder_num_repository.py ← [新建]
├── fin_top10_holders_repository.py ← [新建]
├── fin_top10_float_repository.py ← [新建]
├── base_adj_factor_repository.py ← [新建]
├── base_dividend_repository.py ← [新建]
├── base_suspend_repository.py ← [新建]
├── base_name_change_repository.py ← [新建]
├── fin_report_repository.py ← [新建]
├── fin_daily_basic_repository.py ← [新建]
├── mkt_calendar_repository.py ← [新建]
├── mkt_market_daily_repository.py ← [新建]
├── mkt_sector_daily_repository.py ← [新建]
└── mkt_index_member_repository.py ← [新建]
```

### 3.2 仓储实现模板（日频表）

```python
"""cap_moneyflow_repository — 仓储实现"""

from datetime import date
from typing import Optional

from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from domain.cap_moneyflow.entity import CapMoneyflow
from domain.cap_moneyflow.repository import CapMoneyflowRepository
from infrastructure.database.models.cap_moneyflow import CapMoneyflowDB


class CapMoneyflowRepoImpl(CapMoneyflowRepository):
    """个股资金流向仓储实现"""

    def __init__(self, session: AsyncSession):
        self._session = session

    def _to_entity(self, row: CapMoneyflowDB) -> CapMoneyflow:
        return CapMoneyflow(
            symbol=row.symbol,
            trade_date=row.trade_date,
            buy_sm_vol=row.buy_sm_vol,
            buy_sm_amount=row.buy_sm_amount,
            # ... 其余字段同理 ...
            net_mf_vol=row.net_mf_vol,
            net_mf_amount=row.net_mf_amount,
            data_source=row.data_source or "tushare",
        )

    @staticmethod
    def _to_row(e: CapMoneyflow) -> dict:
        return {
            "symbol": e.symbol,
            "trade_date": e.trade_date,
            "buy_sm_vol": e.buy_sm_vol,
            "buy_sm_amount": e.buy_sm_amount,
            # ...
            "net_mf_vol": e.net_mf_vol,
            "net_mf_amount": e.net_mf_amount,
            "data_source": e.data_source,
        }

    async def save(self, entity: CapMoneyflow) -> CapMoneyflow:
        row = CapMoneyflowDB(**self._to_row(entity))
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return entity

    async def save_batch(self, entities: list[CapMoneyflow]) -> int:
        if not entities:
            return 0
        rows = [self._to_row(e) for e in entities]
        excluded = pg_insert(CapMoneyflowDB).excluded
        upsert_set = {k: getattr(excluded, k) for k in self._to_row(entities[0])}
        stmt = (
            pg_insert(CapMoneyflowDB)
            .values(rows)
            .on_conflict_do_update(
                constraint="uq_cap_moneyflow_symbol_date",
                set_=upsert_set,
            )
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount

    async def find_by_symbol_date(
        self, symbol: str, trade_date: date
    ) -> Optional[CapMoneyflow]:
        stmt = select(CapMoneyflowDB).where(
            CapMoneyflowDB.symbol == symbol,
            CapMoneyflowDB.trade_date == trade_date,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_by_symbol(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> list[CapMoneyflow]:
        stmt = select(CapMoneyflowDB).where(CapMoneyflowDB.symbol == symbol)
        if start_date:
            stmt = stmt.where(CapMoneyflowDB.trade_date >= start_date)
        if end_date:
            stmt = stmt.where(CapMoneyflowDB.trade_date <= end_date)
        stmt = stmt.order_by(CapMoneyflowDB.trade_date.asc())
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_entity(r) for r in rows]
```

---

## 4. 后端采集器

### 4.1 目录结构

```
backend/src/infrastructure/collectors/
├── __init__.py
├── interfaces.py      ← [已有] FetcherProtocol / CollectParams (不变)
├── base.py            ← [已有] BaseCollector (不变)
├── tushare/
│   ├── __init__.py
│   ├── parser.py       ← [已有] TushareKlineParser (不变)
│   ├── fetcher.py      ← [已有] TushareFetcher (不变，仅 KlineBO)
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── cap_moneyflow_parser.py   ← [新建]
│   │   ├── cap_margin_detail_parser.py ← [新建]
│   │   ├── cap_top_list_parser.py     ← [新建]
│   │   ├── fin_top10_parser.py        ← [新建]
│   │   ├── base_adj_factor_parser.py  ← [新建]
│   │   ├── base_dividend_parser.py   ← [新建]
│   │   ├── base_suspend_parser.py     ← [新建]
│   │   ├── mkt_sector_daily_parser.py ← [新建]
│   │   └── mkt_index_member_parser.py  ← [新建]
│   └── fetchers/
│       ├── __init__.py
│       ├── cap_moneyflow_fetcher.py   ← [新建]
│       ├── cap_margin_detail_fetcher.py ← [新建]
│       ├── cap_top_list_fetcher.py     ← [新建]
│       ├── cap_top_inst_fetcher.py     ← [新建]
│       ├── cap_block_trade_fetcher.py  ← [新建]
│       ├── cap_holder_num_fetcher.py   ← [新建]
│       ├── fin_top10_holders_fetcher.py ← [新建]
│       ├── fin_top10_float_fetcher.py  ← [新建]
│       ├── base_adj_factor_fetcher.py  ← [新建]
│       ├── base_dividend_fetcher.py   ← [新建]
│       ├── base_suspend_fetcher.py    ← [新建]
│       ├── base_name_change_fetcher.py ← [新建]
│       ├── fin_report_fetcher.py      ← [新建]
│       ├── fin_daily_basic_fetcher.py ← [新建]
│       ├── mkt_calendar_fetcher.py   ← [新建]
│       ├── mkt_market_daily_fetcher.py ← [新建]
│       ├── mkt_sector_daily_fetcher.py ← [新建]
│       └── mkt_index_member_fetcher.py ← [新建]
```

### 4.2 Tushare Fetcher 统一基类

所有新 fetcher 继承 `BaseCollector`，通用逻辑：

```python
"""cap_moneyflow_fetcher — Tushare 个股资金流向采集器"""

import logging
from datetime import date, timedelta

import pandas as pd

from domain.cap_moneyflow.schemas import CapMoneyflowBO
from infrastructure.collectors.base import BaseCollector
from infrastructure.collectors.interfaces import CollectParams
from infrastructure.collectors.tushare.parsers.cap_moneyflow_parser import (
    CapMoneyflowParser,
)

logger = logging.getLogger(__name__)


class CapMoneyflowFetcher(BaseCollector):
    """Tushare moneyflow 接口采集器"""

    API_NAME = "moneyflow"

    def __init__(self):
        super().__init__()
        self._parser = CapMoneyflowParser()
        self._init_tushare()

    def _init_tushare(self):
        import tushare as ts
        from infrastructure.config import get_settings
        token = get_settings().TUSHARE_TOKEN
        if not token:
            raise RuntimeError("TUSHARE_TOKEN 未配置")
        ts.set_token(token)
        self._pro = ts.pro_api()

    def fetch(self, params: CollectParams) -> list[CapMoneyflowBO]:
        """采集个股资金流向（按 symbol 或全市场）"""
        if params.symbol:
            return self._fetch_single(params.symbol)
        return self._fetch_all()

    def _fetch_single(self, symbol: str) -> list[CapMoneyflowBO]:
        ts_code = self._symbol_to_ts_code(symbol)
        end_date = date.today()
        start_date = end_date - timedelta(days=params.days)
        df = self._pro.moneyflow(
            ts_code=ts_code,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return []
        return self._parser.parse(df, symbol)

    def _fetch_all(self) -> list[CapMoneyflowBO]:
        """全市场采集：按 trade_date 拉一次（moneyflow 支持按日期查全市场）"""
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # 增量取最近 7 天
        df = self._pro.moneyflow(
            trade_date=end_date.strftime("%Y%m%d"),
        )
        if df is None or df.empty:
            return []
        # parser 会自动从 ts_code 提取 symbol
        return self._parser.parse(df)

    def _symbol_to_ts_code(self, symbol: str) -> str:
        # 同 TushareFetcher 的逻辑，抽取为工具函数
        from infrastructure.collectors.tushare.fetcher import symbol_to_ts_code
        return symbol_to_ts_code(symbol)
```

### 4.3 Parser 模板（与 fetcher 配对）

```python
"""cap_moneyflow_parser — 资金流向解析器"""

from typing import Optional

import pandas as pd

from domain.cap_moneyflow.schemas import CapMoneyflowBO


class CapMoneyflowParser:
    """将 tushare moneyflow DataFrame 解析为 CapMoneyflowBO 列表"""

    FIELD_MAP = {
        "symbol": "symbol",
        "trade_date": "trade_date",
        "buy_sm_vol": "buy_sm_vol",
        "buy_sm_amount": "buy_sm_amount",
        # ...
        "net_mf_vol": "net_mf_vol",
        "net_mf_amount": "net_mf_amount",
    }

    def parse(self, df: pd.DataFrame, symbol: Optional[str] = None) -> list[CapMoneyflowBO]:
        if df is None or df.empty:
            return []
        if "ts_code" in df.columns and symbol is None:
            # 从 ts_code 提取 symbol（6位纯数字）
            df = df.copy()
            df["symbol"] = df["ts_code"].str[:6]
        results = []
        for _, row in df.iterrows():
            try:
                results.append(self._row_to_bo(row))
            except Exception:
                continue
        return results

    def _row_to_bo(self, row: pd.Series) -> CapMoneyflowBO:
        return CapMoneyflowBO(
            symbol=str(row.get("symbol", "")),
            trade_date=self._parse_date(row.get("trade_date")),
            buy_sm_vol=self._f(row.get("buy_sm_vol")),
            # ...
            net_mf_vol=self._f(row.get("net_mf_vol")),
            net_mf_amount=self._f(row.get("net_mf_amount")),
        )

    @staticmethod
    def _parse_date(v) -> Optional[str]:
        if v is None:
            return None
        s = str(v)
        if len(s) == 8:
            return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
        return s

    @staticmethod
    def _f(v) -> Optional[float]:
        if v is None:
            return None
        try:
            f = float(v)
            return None if (pd.isna(f) or f != f) else f
        except (ValueError, TypeError):
            return None
```

### 4.4 通用采集服务（任务编排层）

新建 `infrastructure/tasks/collect_task.py`：

```python
"""通用数据采集任务"""

from datetime import date
from typing import TypeVar, Generic

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class CollectTask(Generic[T]):
    """通用采集任务

    所有 14 张新表的采集任务统一用此类编排。
    """

    def __init__(
        self,
        fetcher,
        parser,
        repo_impl,
        session: AsyncSession,
    ):
        self._fetcher = fetcher
        self._parser = parser
        self._repo = repo_impl(session)
        self._session = session

    async def run(
        self,
        symbol: str | None = None,
        trade_date: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """统一采集入口"""
        from infrastructure.collectors.interfaces import CollectParams
        params = CollectParams(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            trade_date=trade_date,
            days=30,
        )
        raw = self._fetcher.fetch(params)
        entities = [r.to_entity() for r in raw]
        saved = await self._repo.save_batch(entities)
        await self._session.commit()
        return {
            "total": len(raw),
            "saved": saved,
            "source": self._fetcher.source_name,
        }
```

---

## 5. 后端应用服务

### 5.1 目录结构

```
backend/src/application/
├── __init__.py
├── dto/
│   ├── kline.py          ← [已有] KlineCollectRequest / Response (不变)
│   ├── stock.py           ← [已有] (不变)
│   ├── pool.py            ← [已有] (不变)
│   ├── pool_operation.py ← [已有] (不变)
│   ├── fin_report.py      ← [新建] FinReportDTO
│   ├── fin_daily_basic.py ← [新建] FinDailyBasicDTO
│   ├── cap_moneyflow.py   ← [新建] CapMoneyflowDTO
│   ├── cap_margin_detail.py ← [新建] CapMarginDetailDTO
│   ├── cap_top_list.py    ← [新建] CapTopListDTO
│   ├── cap_top_inst.py    ← [新建] CapTopInstDTO
│   ├── cap_block_trade.py ← [新建] CapBlockTradeDTO
│   ├── cap_holder_num.py  ← [新建] CapHolderNumDTO
│   ├── fin_top10_holders.py ← [新建] FinTop10HolderDTO
│   ├── base_adj_factor.py  ← [新建] BaseAdjFactorDTO
│   ├── base_dividend.py   ← [新建] BaseDividendDTO
│   ├── base_suspend.py    ← [新建] BaseSuspendDTO
│   ├── mkt_sector_daily.py ← [新建] MktSectorDailyDTO
│   └── mkt_index_member.py  ← [新建] MktIndexMemberDTO
├── services/
│   ├── kline_service.py   ← [已有] (UK 注释需更新)
│   ├── stock_service.py    ← [已有] (不变)
│   ├── pool_service.py     ← [已有] (不变)
│   ├── pool_operation_service.py ← [已有] (不变)
│   ├── fin_report_service.py    ← [新建]
│   ├── fin_daily_basic_service.py ← [新建]
│   ├── cap_moneyflow_service.py ← [新建]
│   ├── cap_margin_detail_service.py ← [新建]
│   ├── cap_top_list_service.py ← [新建]
│   ├── base_adj_factor_service.py ← [新建]
│   └── mkt_sector_daily_service.py ← [新建]
```

### 5.2 应用服务 DTO 模板

```python
"""cap_moneyflow — 采集/查询请求响应 DTO"""

from datetime import date
from pydantic import BaseModel, Field
from typing import Optional


class CapMoneyflowQueryRequest(BaseModel):
    symbol: Optional[str] = Field(None, description="股票代码，不填查全市场")
    trade_date: Optional[date] = Field(None, description="交易日期")
    start_date: Optional[date] = Field(None, description="开始日期")
    end_date: Optional[date] = Field(None, description="结束日期")


class CapMoneyflowItem(BaseModel):
    symbol: str
    trade_date: date
    net_mf_amount: Optional[float] = Field(None, description="净流入额（万元）")
    net_mf_vol: Optional[float] = Field(None, description="净流入量（手）")
    buy_lg_amount: Optional[float] = Field(None, description="大单买入额（万元）")
    sell_lg_amount: Optional[float] = Field(None, description="大单卖出额（万元）")
    buy_elg_amount: Optional[float] = Field(None, description="特大单买入额（万元）")
    sell_elg_amount: Optional[float] = Field(None, description="特大单卖出额（万元）")


class CapMoneyflowCollectResponse(BaseModel):
    symbol: str
    total_count: int
    saved_count: int
    message: str


class CapMoneyflowListResponse(BaseModel):
    total: int
    items: list[CapMoneyflowItem]
```

### 5.3 应用服务实现模板

```python
"""cap_moneyflow — 应用服务"""

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.cap_moneyflow import (
    CapMoneyflowQueryRequest,
    CapMoneyflowListResponse,
    CapMoneyflowCollectResponse,
)
from application.exceptions import CollectionError
from domain.cap_moneyflow.entity import CapMoneyflow
from domain.cap_moneyflow.repository import CapMoneyflowRepository
from infrastructure.collectors.interfaces import CollectParams
from infrastructure.repositories.cap_moneyflow_repository import CapMoneyflowRepoImpl


class CapMoneyflowAppService:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo: CapMoneyflowRepository = CapMoneyflowRepoImpl(session)

    async def collect(
        self,
        request: CapMoneyflowQueryRequest,
        fetcher,
    ) -> CapMoneyflowCollectResponse:
        try:
            params = CollectParams(
                symbol=request.symbol,
                start_date=request.start_date,
                end_date=request.end_date,
            )
            raw_data = fetcher.fetch(params)
            entities: list[CapMoneyflow] = [r.to_entity() for r in raw_data]
            saved = await self._repo.save_batch(entities)
            await self._session.commit()
            return CapMoneyflowCollectResponse(
                symbol=request.symbol or "ALL",
                total_count=len(entities),
                saved_count=saved,
                message=f"成功保存 {saved} 条",
            )
        except Exception as e:
            raise CollectionError(request.symbol or "moneyflow", str(e))

    async def query(
        self,
        request: CapMoneyflowQueryRequest,
    ) -> CapMoneyflowListResponse:
        entities = await self._repo.find_by_symbol(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
        )
        items = [self._entity_to_item(e) for e in entities]
        return CapMoneyflowListResponse(total=len(items), items=items)

    @staticmethod
    def _entity_to_item(e: CapMoneyflow) -> "CapMoneyflowItem":
        from application.dto.cap_moneyflow import CapMoneyflowItem
        return CapMoneyflowItem(
            symbol=e.symbol,
            trade_date=e.trade_date,
            net_mf_amount=e.net_mf_amount,
            net_mf_vol=e.net_mf_vol,
            buy_lg_amount=e.buy_lg_amount,
            sell_lg_amount=e.sell_lg_amount,
            buy_elg_amount=e.buy_elg_amount,
            sell_elg_amount=e.sell_elg_amount,
        )
```

---

## 6. 后端 API 路由

### 6.1 目录结构

```
backend/src/route/api/v1/
├── kline.py          ← [已有] GET /klines/{symbol} (UK 注释更新)
├── stock.py          ← [已有] (不变)
├── stock_analysis.py ← [已有] (不变)
├── pool.py           ← [已有] (不变)
├── cap_moneyflow.py  ← [新建] 资金流向路由
├── cap_margin.py     ← [新建] 两融明细路由
├── cap_top_list.py   ← [新建] 龙虎榜路由
├── fin_report.py    ← [新建] 财务报表路由
├── fin_daily_basic.py ← [新建] 日频估值路由
├── base_adj_factor.py ← [新建] 复权因子路由
├── mkt_sector.py     ← [新建] 板块行情路由
└── mkt_index.py      ← [新建] 板块成分路由
```

### 6.2 API 路由模板

```python
"""cap_moneyflow — 资金流向 API 路由"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.cap_moneyflow import (
    CapMoneyflowQueryRequest,
    CapMoneyflowCollectResponse,
    CapMoneyflowListResponse,
)
from application.services.cap_moneyflow_service import CapMoneyflowAppService
from infrastructure.collectors.interfaces import FetcherProtocol
from infrastructure.database.connection import get_db
from route.schemas.response import R

router = APIRouter(prefix="/moneyflows", tags=["资金流向"])


def get_service(db: AsyncSession = Depends(get_db)) -> CapMoneyflowAppService:
    return CapMoneyflowAppService(session=db)


@router.get(
    "/",
    summary="查询个股资金流向",
    description="按 symbol 和日期范围查询净流入数据",
)
async def query_moneyflow(
    symbol: Optional[str] = Query(None, description="股票代码"),
    trade_date: Optional[date] = Query(None, description="交易日期"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000),
    service: CapMoneyflowAppService = Depends(get_service),
):
    request = CapMoneyflowQueryRequest(
        symbol=symbol,
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    response = await service.query(request)
    # limit 截断
    items = response.items[:limit]
    return R.ok({"total": response.total, "items": [i.model_dump() for i in items]})


@router.post(
    "/collect",
    summary="采集资金流向",
    status_code=status.HTTP_201_CREATED,
)
async def collect_moneyflow(
    symbol: Optional[str] = Query(None, description="股票代码，不填则全市场"),
    trade_date: Optional[date] = Query(None, description="指定日期"),
    service: CapMoneyflowAppService = Depends(get_service),
    fetcher: FetcherProtocol = Depends(lambda: ...),  # 见 6.3
):
    request = CapMoneyflowQueryRequest(symbol=symbol, trade_date=trade_date)
    response = await service.collect(request, fetcher)
    return R.created(response.model_dump())
```

### 6.3 Fetcher 依赖注入（工厂）

在 `route/api/v1/` 下新建 `dependencies.py`：

```python
"""API 层 Fetcher 工厂（避免循环导入）"""

from functools import lru_cache

from infrastructure.collectors.interfaces import FetcherProtocol


@lru_cache
def get_cap_moneyflow_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.cap_moneyflow_fetcher import (
        CapMoneyflowFetcher,
    )
    return CapMoneyflowFetcher()


@lru_cache
def get_cap_margin_detail_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.cap_margin_detail_fetcher import (
        CapMarginDetailFetcher,
    )
    return CapMarginDetailFetcher()


@lru_cache
def get_cap_top_list_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.cap_top_list_fetcher import (
        CapTopListFetcher,
    )
    return CapTopListFetcher()


@lru_cache
def get_fin_top10_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.fin_top10_holders_fetcher import (
        FinTop10HolderFetcher,
    )
    return FinTop10HolderFetcher()


@lru_cache
def get_base_adj_factor_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.base_adj_factor_fetcher import (
        BaseAdjFactorFetcher,
    )
    return BaseAdjFactorFetcher()


@lru_cache
def get_mkt_sector_daily_fetcher() -> FetcherProtocol:
    from infrastructure.collectors.tushare.fetchers.mkt_sector_daily_fetcher import (
        MktSectorDailyFetcher,
    )
    return MktSectorDailyFetcher()
```

路由中 `Depends(get_cap_moneyflow_fetcher)` 引用此工厂。

### 6.4 完整 API 路由清单

| 方法 | 路径 | 服务 | 说明 |
|------|------|------|------|
| GET | `/moneyflows/` | `CapMoneyflowAppService` | 查询个股资金流向 |
| POST | `/moneyflows/collect` | `CapMoneyflowAppService` | 采集资金流向 |
| GET | `/margin-details/` | `CapMarginDetailAppService` | 查询个股两融明细 |
| POST | `/margin-details/collect` | `CapMarginDetailAppService` | 采集两融明细 |
| GET | `/top-lists/` | `CapTopListAppService` | 查询龙虎榜 |
| POST | `/top-lists/collect` | `CapTopListAppService` | 采集龙虎榜 |
| GET | `/top-insts/` | `CapTopInstAppService` | 查询机构席位 |
| GET | `/block-trades/` | `CapBlockTradeAppService` | 查询大宗交易 |
| POST | `/block-trades/collect` | `CapBlockTradeAppService` | 采集大宗交易 |
| GET | `/holder-nums/` | `CapHolderNumAppService` | 查询股东户数 |
| GET | `/fin-reports/` | `FinReportAppService` | 查询财务报表 |
| POST | `/fin-reports/collect` | `FinReportAppService` | 采集财务报表 |
| GET | `/fin-daily-basics/` | `FinDailyBasicAppService` | 查询日频估值 |
| POST | `/fin-daily-basics/collect` | `FinDailyBasicAppService` | 采集日频估值 |
| GET | `/top10-holders/` | `FinTop10HolderAppService` | 查询十大股东 |
| POST | `/top10-holders/collect` | `FinTop10HolderAppService` | 采集十大股东 |
| GET | `/adj-factors/` | `BaseAdjFactorAppService` | 查询复权因子 |
| POST | `/adj-factors/collect` | `BaseAdjFactorAppService` | 采集复权因子 |
| GET | `/dividends/` | `BaseDividendAppService` | 查询分红送股 |
| POST | `/dividends/collect` | `BaseDividendAppService` | 采集分红送股 |
| GET | `/suspends/` | `BaseSuspendAppService` | 查询停复牌 |
| POST | `/suspends/collect` | `BaseSuspendAppService` | 采集停复牌 |
| GET | `/sector-dailys/` | `MktSectorDailyAppService` | 查询板块日行情 |
| POST | `/sector-dailys/collect` | `MktSectorDailyAppService` | 采集板块日行情 |
| GET | `/index-members/` | `MktIndexMemberAppService` | 查询板块成分 |
| POST | `/index-members/collect` | `MktIndexMemberAppService` | 采集板块成分 |

> **注**：部分 POST collect 接口根据 tushare 接口特性（全市场 vs 单只），symbol 参数可选或不填。

---

## 7. 数据库迁移

### 7.1 Alembic 初始化（若尚未初始化）

```bash
cd backend
alembic init alembic
```

### 7.2 迁移脚本模板

所有迁移统一放在 `alembic/versions/` 下：

#### 迁移 001：重命名 tech_kline_daily（原 daily_kline）

```python
"""rename_daily_kline_to_tech_kline_daily

Revision ID: 001_rename_kline
Revises:
Create Date: 2026-09-15

注意：PostgreSQL 重命名表不锁表，执行迅速。
"""
from alembic import op
import sqlalchemy as sa

revision = "001_rename_kline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS daily_klines RENAME TO tech_kline_dailys")
    op.execute(
        "ALTER INDEX IF EXISTS ix_daily_kline_symbol_date "
        "RENAME TO ix_tech_kline_symbol_date"
    )
    op.execute(
        "ALTER INDEX IF EXISTS uq_kline_symbol_date "
        "RENAME TO uq_tech_kline_symbol_date"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS tech_kline_dailys RENAME TO daily_klines")
    op.execute(
        "ALTER INDEX IF EXISTS ix_tech_kline_symbol_date "
        "RENAME TO ix_daily_kline_symbol_date"
    )
    op.execute(
        "ALTER INDEX IF EXISTS uq_tech_kline_symbol_date "
        "RENAME TO uq_kline_symbol_date"
    )
```

#### 迁移 002：创建 cap_moneyflows（新表）

```python
"""create_cap_moneyflows

Revision ID: 002_create_cap_moneyflows
Revises: 001_rename_kline
"""
from alembic import op
import sqlalchemy as sa

revision = "002_create_cap_moneyflows"
down_revision = "001_rename_kline"


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cap_moneyflows (
            id              BIGSERIAL PRIMARY KEY,
            symbol          VARCHAR(10) NOT NULL,
            trade_date      DATE NOT NULL,
            buy_sm_vol      DOUBLE PRECISION,
            buy_sm_amount   DOUBLE PRECISION,
            sell_sm_vol     DOUBLE PRECISION,
            sell_sm_amount  DOUBLE PRECISION,
            buy_md_vol      DOUBLE PRECISION,
            buy_md_amount   DOUBLE PRECISION,
            sell_md_vol     DOUBLE PRECISION,
            sell_md_amount  DOUBLE PRECISION,
            buy_lg_vol      DOUBLE PRECISION,
            buy_lg_amount   DOUBLE PRECISION,
            sell_lg_vol     DOUBLE PRECISION,
            sell_lg_amount  DOUBLE PRECISION,
            buy_elg_vol     DOUBLE PRECISION,
            buy_elg_amount  DOUBLE PRECISION,
            sell_elg_vol    DOUBLE PRECISION,
            sell_elg_amount DOUBLE PRECISION,
            net_mf_vol      DOUBLE PRECISION,
            net_mf_amount   DOUBLE PRECISION,
            data_source     VARCHAR(16) DEFAULT 'tushare',
            created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE (symbol, trade_date),
            INDEX ix_cap_moneyflow_date (trade_date)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cap_moneyflows")
```

#### 迁移 003-015：其他 13 张新表

按 `01data.md` §3 的字段定义，参照迁移 002 模板逐一编写。每张表一个迁移文件，revision 连续递增。

#### 迁移 N：重命名其余 5 张已有表

```python
"""rename_existing_tables

Revision ID: 00N_rename_existing
Revises: 00N-1_create_xxx
"""
from alembic import op

revision = "00N_rename_existing"
down_revision = "00N-1_create_xxx"


def upgrade() -> None:
    # margin_data → cap_margins
    op.execute("ALTER TABLE IF EXISTS margin_data RENAME TO cap_margins")
    # financial_report → fin_reports
    op.execute("ALTER TABLE IF EXISTS financial_report RENAME TO fin_reports")
    # daily_basic_metric → fin_daily_basics
    op.execute("ALTER TABLE IF EXISTS daily_basic_metric RENAME TO fin_daily_basics")
    # trading_calendar → mkt_calendars
    op.execute("ALTER TABLE IF EXISTS trading_calendar RENAME TO mkt_calendars")
    # market_daily → mkt_market_dailys
    op.execute("ALTER TABLE IF EXISTS market_daily RENAME TO mkt_market_dailys")


def downgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS cap_margins RENAME TO margin_data")
    op.execute("ALTER TABLE IF EXISTS fin_reports RENAME TO financial_report")
    op.execute("ALTER TABLE IF EXISTS fin_daily_basics RENAME TO daily_basic_metric")
    op.execute("ALTER TABLE IF EXISTS mkt_calendars RENAME TO trading_calendar")
    op.execute("ALTER TABLE IF EXISTS mkt_market_dailys RENAME TO market_daily")
```

> **执行顺序**：先执行所有新建表迁移（002-015），最后执行重命名迁移（N），保证 down_revision 链路正确。

### 7.3 主 `main.py` 改动

删除原有的 3 个兼容迁移函数（`_migrate_daily_klines_indicators` / `_migrate_stock_infos` / `_ensure_default_pool`），改由 Alembic 管理：

```python
# main.py — 简化后
from alembic.config import Config
from alembic import command

async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        # Alembic 自动执行所有 pending 迁移
        cfg = Config("alembic.ini")
        command.upgrade(cfg, revision="head")
    yield
    await close_db()
```

---

## 8. 前端

### 8.1 目录结构

```
frontend/src/
├── common/utils/http.ts         ← [已有] Axios 封装（不变）
├── stores/
│   ├── kline.ts               ← [已有] K 线 Store（UK 注释更新）
│   ├── pool.ts                ← [已有] 操作池 Store（不变）
│   ├── moneyflow.ts          ← [新建] 资金流向 Store
│   ├── fin_report.ts          ← [新建] 财务报表 Store
│   ├── sector.ts             ← [新建] 板块行情 Store
│   └── dashboard.ts           ← [已有] 扩展
├── views/
│   ├── Dashboard.vue           ← [已有] 扩展统计卡片 + 资金面入口
│   ├── stock-info/
│   │   ├── api.ts            ← [已有] 扩展新数据查询（见 8.2）
│   │   └── components/
│   │       ├── MoneyflowPanel.vue     ← [新建] 资金流向面板
│   │       ├── ValuationPanel.vue    ← [新建] 估值面板（PE/PB/PS）
│   │       └── HolderPanel.vue       ← [新建] 股东结构面板
│   └── stock-pool/
│       ├── components/
│       │   ├── AnalysisDetailPanel.vue ← [已有] 扩展资金面 Tab
│       │   └── SectorPanel.vue         ← [新建] 板块对比面板
├── views/market/               ← [新建] 市场全局视图
│   ├── MarketDashboard.vue      ← [新建] 市场大盘（行业涨幅/龙虎榜）
│   ├── SectorBoard.vue          ← [新建] 板块行情列表
│   └── api.ts                  ← [新建] 市场全局 API
```

### 8.2 API 封装（`views/stock-info/api.ts` 扩展）

在现有 `api.ts` 末尾追加：

```typescript
// ═══════════════════════════════════════════════════════════════
//  🆕 资金流向 API
// ═══════════════════════════════════════════════════════════════

/** 资金流向项 */
export interface MoneyflowItem {
  symbol: string
  trade_date: string
  net_mf_amount: number | null
  net_mf_vol: number | null
  buy_lg_amount: number | null
  sell_lg_amount: number | null
  buy_elg_amount: number | null
  sell_elg_amount: number | null
}

/** GET /moneyflows/ 查询资金流向 */
export const getMoneyflows = (params: {
  symbol?: string
  trade_date?: string
  start_date?: string
  end_date?: string
  limit?: number
}) => http.get<{ total: number; items: MoneyflowItem[] }>('/moneyflows/', { params }).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  🆕 估值/基本面 API
// ═══════════════════════════════════════════════════════════════

/** 日频估值项 */
export interface DailyBasicItem {
  symbol: string
  trade_date: string
  pe: number | null
  pe_ttm: number | null
  pb: number | null
  ps: number | null
  turnover_rate: number | null
  total_mv: number | null
  circ_mv: number | null
}

/** GET /fin-daily-basics/ 查询日频估值 */
export const getFinDailyBasics = (params: {
  symbol: string
  start_date?: string
  end_date?: string
  limit?: number
}) => http.get<{ total: number; items: DailyBasicItem[] }>('/fin-daily-basics/', { params }).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  🆕 龙虎榜 API
// ═══════════════════════════════════════════════════════════════

export interface TopListItem {
  trade_date: string
  symbol: string
  name: string
  close: number
  pct_chg: number
  net_amount: number
  reason: string
}

/** GET /top-lists/ 查询龙虎榜 */
export const getTopLists = (params: {
  trade_date?: string
  start_date?: string
  end_date?: string
}) => http.get<{ total: number; items: TopListItem[] }>('/top-lists/', { params }).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  🆕 板块行情 API
// ═══════════════════════════════════════════════════════════════

export interface SectorDailyItem {
  sector_type: string
  sector_code: string
  sector_name: string
  trade_date: string
  close: number
  pct_change: number
  amount: number
  turnover_rate: number
}

/** GET /sector-dailys/ 查询板块日行情 */
export const getSectorDailys = (params: {
  sector_type?: string
  trade_date?: string
  limit?: number
}) => http.get<{ total: number; items: SectorDailyItem[] }>('/sector-dailys/', { params }).then(unwrap)

// ═══════════════════════════════════════════════════════════════
//  🆕 复权因子 API
// ═══════════════════════════════════════════════════════════════

export interface AdjFactorItem {
  symbol: string
  trade_date: string
  adj_factor: number
}

/** GET /adj-factors/ 查询复权因子 */
export const getAdjFactors = (params: {
  symbol: string
  start_date?: string
  end_date?: string
}) => http.get<{ total: number; items: AdjFactorItem[] }>('/adj-factors/', { params }).then(unwrap)
```

### 8.3 Pinia Store 模板（资金流向）

```typescript
// stores/moneyflow.ts

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getMoneyflows } from '@/views/stock-info/api'
import type { MoneyflowItem } from '@/views/stock-info/api'

export const useMoneyflowStore = defineStore('moneyflow', () => {
  const items = ref<MoneyflowItem[]>([])
  const loading = ref(false)

  async function fetch(symbol: string, days = 30) {
    loading.value = true
    try {
      const end = new Date().toISOString().slice(0, 10)
      const start = new Date(Date.now() - days * 86400000).toISOString().slice(0, 10)
      const res = await getMoneyflows({ symbol, start_date: start, end_date: end, limit: 100 })
      items.value = res.items
    } finally {
      loading.value = false
    }
  }

  /** 净流入额趋势（最近 N 天） */
  function netFlowTrend() {
    return items.value
      .slice()
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
      .map(i => ({ date: i.trade_date, value: i.net_mf_amount ?? 0 }))
  }

  /** 大单净流入趋势 */
  function lgNetFlow() {
    return items.value
      .sort((a, b) => a.trade_date.localeCompare(b.trade_date))
      .map(i => ({
        date: i.trade_date,
        buy: i.buy_lg_amount ?? 0,
        sell: i.sell_lg_amount ?? 0,
        net: ((i.buy_lg_amount ?? 0) - (i.sell_lg_amount ?? 0)),
      }))
  }

  return { items, loading, fetch, netFlowTrend, lgNetFlow }
})
```

### 8.4 组件模板：资金流向面板

```vue
<!-- views/stock-info/components/MoneyflowPanel.vue -->
<template>
  <el-card v-loading="store.loading" class="moneyflow-panel">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-bold">💰 资金流向</span>
        <el-select v-model="days" size="small" style="width: 80px" @change="reload">
          <el-option :value="5" label="5日" />
          <el-option :value="20" label="20日" />
          <el-option :value="60" label="60日" />
        </el-select>
      </div>
    </template>

    <div v-if="store.items.length === 0" class="text-gray-400 text-center py-8">
      暂无数据
    </div>

    <div v-else>
      <!-- 汇总指标 -->
      <el-row :gutter="12" class="mb-4">
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-label">5日净流入</div>
            <div :class="['stat-value', net5d >= 0 ? 'text-red-500' : 'text-green-500']">
              {{ formatMoney(net5d) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-label">大单净流入</div>
            <div :class="['stat-value', lgNet >= 0 ? 'text-red-500' : 'text-green-500']">
              {{ formatMoney(lgNet) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="stat-item">
            <div class="stat-label">特大单净流入</div>
            <div :class="['stat-value', elgNet >= 0 ? 'text-red-500' : 'text-green-500']">
              {{ formatMoney(elgNet) }}
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 柱状图占位（可接入 ECharts） -->
      <div class="chart-area">
        <div v-for="item in store.items.slice(-20)" :key="item.trade_date" class="bar">
          <div
            class="bar-fill"
            :style="{
              height: Math.abs(item.net_mf_amount ?? 0) / maxAbs * 100 + '%',
              background: (item.net_mf_amount ?? 0) >= 0 ? '#f87171' : '#34d399'
            }"
          />
          <div class="bar-label">{{ item.trade_date.slice(5) }}</div>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMoneyflowStore } from '@/stores/moneyflow'

const props = defineProps<{ symbol: string }>()
const store = useMoneyflowStore()
const days = ref(20)

const maxAbs = computed(() =>
  Math.max(...store.items.map(i => Math.abs(i.net_mf_amount ?? 0)), 1
)
const net5d = computed(() =>
  store.items.slice(-5).reduce((s, i) => s + (i.net_mf_amount ?? 0), 0)
)
const lgNet = computed(() =>
  store.items.reduce((s, i) => s + ((i.buy_lg_amount ?? 0) - (i.sell_lg_amount ?? 0)), 0)
)
const elgNet = computed(() =>
  store.items.reduce((s, i) => s + ((i.buy_elg_amount ?? 0) - (i.sell_elg_amount ?? 0)), 0)
)

function reload() { store.fetch(props.symbol, days.value) }

function formatMoney(v: number) {
  if (Math.abs(v) >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toFixed(2)
}

onMounted(reload)
</script>
```

### 8.5 Dashboard 扩展

`Dashboard.vue` 已有 4 张统计卡片，扩展为 8 张，新增：

| 新卡片 | 数据来源 | 图标 |
|--------|----------|------|
| 资金流向覆盖 | `cap_moneyflows` COUNT(DISTINCT symbol) | 💰 |
| 两融覆盖 | `cap_margin_details` COUNT(DISTINCT symbol) | 📊 |
| 龙虎榜记录 | `cap_top_lists` COUNT(*) today | 🏆 |
| 板块行情 | `mkt_sector_dailys` COUNT(DISTINCT sector_name) | 🏭 |

### 8.6 新增路由

`router/home.ts` 新增：

```typescript
// router/home.ts
{
  path: '/home/market',
  name: 'MarketDashboard',
  component: () => import('@/views/market/MarketDashboard.vue'),
  meta: { title: '市场全局' },
},
```

---

## 9. 实施阶段

### P0 — ORM 与迁移（1 周）

| 任务 | 负责 |
|------|------|
| 重写 `tech_kline.py`（类名/表名改名） | 后端 |
| 删除 `kline.py` 旧文件 | 后端 |
| 新建 14 个 ORM 模型文件 | 后端 |
| 新建 Alembic 迁移脚本（001-015+N） | 后端 |
| `main.py` 删除兼容迁移函数，改用 Alembic | 后端 |

**验收标准**：`alembic upgrade head` 成功，无报错。

### P1 — 基础数据层采集（1-2 周）

| 任务 | 负责 |
|------|------|
| `base_adj_factor` fetcher + parser + 仓储 + 服务 + 路由 | 后端 |
| `base_dividend` 同上 | 后端 |
| `base_suspend` 同上 | 后端 |
| `base_name_change` 同上 | 后端 |

**验收标准**：4 张表全量入库，`GET /adj-factors/?symbol=000001` 有数据返回。

### P2 — 资金面核心采集（1-2 周）

| 任务 | 负责 |
|------|------|
| `cap_moneyflow` 全链路 | 后端 |
| `cap_margin_detail` 全链路 | 后端 |
| `cap_top_list` 全链路 | 后端 |
| 前端 `MoneyflowPanel.vue` 组件 | 前端 |
| 前端 `TopListPanel.vue` 组件 | 前端 |

**验收标准**：前端股票详情抽屉能展示资金流向柱状图和龙虎榜记录。

### P3 — 基本面扩展（1 周）

| 任务 | 负责 |
|------|------|
| `fin_daily_basic` 全链路 | 后端 |
| `fin_top10_holders` 全链路 | 后端 |
| `fin_top10_floatholders` 全链路 | 后端 |
| `fin_report` 全链路 | 后端 |
| 前端 `ValuationPanel.vue` + `HolderPanel.vue` | 前端 |

### P4 — 市场全局（1 周）

| 任务 | 负责 |
|------|------|
| `mkt_sector_daily` 全链路 | 后端 |
| `mkt_index_member` 全链路 | 后端 |
| `mkt_calendar` + `mkt_market_daily` 改名入库 | 后端 |
| `MarketDashboard.vue` + `SectorBoard.vue` | 前端 |
| Dashboard 扩展统计卡片 | 前端 |

### P5 — 资金面深度 + 剩余表（1 周）

| 任务 | 负责 |
|------|------|
| `cap_top_inst` / `cap_block_trade` / `cap_holder_num` | 后端 |
| 前端龙虎榜详情、股东户数趋势图 | 前端 |
| 集成测试 + 端到端验收 | 前后端联调 |

---

## 附录 A：文件清单（按实施顺序）

```
backend/src/infrastructure/database/models/tech_kline.py       ← 重写
backend/src/infrastructure/database/models/fin_report.py      ← 新建
backend/src/infrastructure/database/models/fin_daily_basic.py ← 新建
backend/src/infrastructure/database/models/cap_margin.py      ← 新建
backend/src/infrastructure/database/models/cap_moneyflow.py  ← 新建
backend/src/infrastructure/database/models/cap_margin_detail.py ← 新建
backend/src/infrastructure/database/models/cap_top_list.py    ← 新建
backend/src/infrastructure/database/models/cap_top_inst.py    ← 新建
backend/src/infrastructure/database/models/cap_block_trade.py ← 新建
backend/src/infrastructure/database/models/cap_holder_num.py  ← 新建
backend/src/infrastructure/database/models/fin_top10_holders.py ← 新建
backend/src/infrastructure/database/models/fin_top10_float.py ← 新建
backend/src/infrastructure/database/models/base_adj_factor.py   ← 新建
backend/src/infrastructure/database/models/base_dividend.py   ← 新建
backend/src/infrastructure/database/models/base_suspend.py     ← 新建
backend/src/infrastructure/database/models/base_name_change.py ← 新建
backend/src/infrastructure/database/models/mkt_calendar.py    ← 新建
backend/src/infrastructure/database/models/mkt_market_daily.py ← 新建
backend/src/infrastructure/database/models/mkt_sector_daily.py ← 新建
backend/src/infrastructure/database/models/mkt_index_member.py ← 新建

backend/src/infrastructure/database/models/__init__.py          ← 更新导出

backend/src/domain/fin_report/  (entity, repository, schemas) ← 新建
backend/src/domain/cap_moneyflow/ 同上 ← 新建
...（其余 13 个领域同上）

backend/src/infrastructure/repositories/*.py                  ← 新建
backend/src/infrastructure/collectors/tushare/fetchers/*.py   ← 新建
backend/src/infrastructure/collectors/tushare/parsers/*.py     ← 新建
backend/src/infrastructure/tasks/collect_task.py              ← 新建

backend/src/application/dto/*.py                               ← 新建
backend/src/application/services/*.py                         ← 新建

backend/src/route/api/v1/*.py                                ← 新建
backend/src/route/api/v1/dependencies.py                    ← 新建

backend/alembic/versions/001_rename_kline.py                 ← 新建
backend/alembic/versions/002_create_cap_moneyflows.py        ← 新建
...（014 张新表迁移）
backend/alembic/versions/0NN_rename_existing.py              ← 新建

frontend/src/stores/moneyflow.ts                            ← 新建
frontend/src/stores/sector.ts                               ← 新建
frontend/src/views/stock-info/api.ts                         ← 扩展
frontend/src/views/stock-info/components/MoneyflowPanel.vue    ← 新建
frontend/src/views/stock-info/components/ValuationPanel.vue   ← 新建
frontend/src/views/stock-info/components/HolderPanel.vue     ← 新建
frontend/src/views/market/MarketDashboard.vue                ← 新建
frontend/src/views/market/SectorBoard.vue                   ← 新建
frontend/src/views/market/api.ts                            ← 新建
frontend/src/router/home.ts                                 ← 扩展
frontend/src/views/Dashboard.vue                            ← 扩展
```

**总计**：约 **60 个新文件**，分布在 5 个实施阶段（4-6 周）。

---

**文档结束。请审阅，确认后进入实施。**
