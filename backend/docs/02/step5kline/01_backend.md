# Step 5: K 线 + 指标 + 归因分析 — 后端实现指南

> 本文档描述后端如何对接 Tushare `daily` 接口、拉取 K 线数据、计算技术指标、并为前端/AI 提供统一的「股票分析」接口。
>
> **核心决策：技术指标不再单独成表,而是展宽到 `daily_klines` 表（方案 A）**。下文会解释为什么这样做,以及落地细节。

---

## 1. 目标与范围

### 功能目标

| 目标 | 说明 |
|------|------|
| **K 线拉取** | 单只股票 / 操作池批量, 从 Tushare Pro `daily` 接口获取 |
| **指标计算** | 基于日 K 线计算 MA / EMA / MACD / RSI / KDJ / BOLL |
| **数据持久化** | K 线 + 指标 **同表存储**（一行一交易日,展宽字段） |
| **AI 归因分析接口** | `GET /stocks/{symbol}/analysis` 一次返回 K 线 + 指标 + 技术形态摘要 + 所在池, 直接喂给大模型 |
| **异步任务** | 池级批量拉取走后台任务, 支持进度轮询 |

### 数据源

- **接口**：`pro.daily(ts_code, start_date, end_date)`
- **数据频率**：日 K 线（不复权）
- **积分限制**：每分钟 500 次, 每次最多 6000 条
- **入库时间**：交易日 15:00 – 16:00

---

## 2. 为什么用方案 A（指标展宽到 kline 表）

### 数据规模估算（A 股全市场约 5400 只）

| 数据 | 行数估算 | 单行字节 | 总大小 |
|------|----------|----------|--------|
| **daily_klines（23 年）** | ~3000 万 | ~70 字节 | ~2 GB |
| ~~daily_indicators（独立长表）~~ | ❌ **~5.4 亿** | ~80 字节 | ❌ **~40 GB** |
| **daily_klines + 17 指标列** ✅ | ~3000 万 | ~150 字节 | ~4.5 GB |

> 18 个指标 × 5400 股 × 240 天 × 23 年 = **5.4 亿行** → 独立长表方案会撑爆。**指标展宽到 K 线表**, 行数仍是 3000 万, 但每行多了 17 个 `NUMERIC` 列。

### 三方案对比

| 方案 | A. 展宽到 kline ✅ | B. 独立长表 | C. JSON 字段 |
|------|------|------|------|
| 行数 | 3000 万 | 5.4 亿 | 3000 万 |
| 总大小 | ~4.5 GB | ~4.5 GB | ~7.5 GB |
| 查询 | 一次 SELECT 取齐 ✅ | JOIN + GROUP | JSONB 解析 |
| 写 | UPSERT 单表 ✅ | 多次 INSERT | JSON 序列化 |
| 扩展 | ALTER TABLE ✅ | 加行 ✅ | 加字段 |
| AI 友好 | 数据扁平,直接喂 ✅ | 需服务端聚合 | 需服务端解析 |

### 唯一妥协

新增指标要 `ALTER TABLE`。但归因分析用到的指标就这十几个, **实际上不怎么会变**。

---

## 3. 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│                          API 层 (route)                          │
│  GET  /klines/{symbol}                  查询 K 线 + 指标        │
│  POST /klines/collect                  单只采集                │
│  POST /pools/{id}/operations            池级批量采集（异步）     │
│  GET  /operations/{id}/progress         轮询进度                │
│  GET  /stocks/{symbol}/analysis         🆕 AI 归因分析入口     │
│  POST /admin/indicators/recalculate    🆕 全市场重算（管理）    │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                       应用层 (application)                       │
│  KlineAppService           — K 线采集 / 查询 / 指标计算（合并）   │
│  PoolOperationAppService   — 池操作编排（已有）                  │
│  StockAnalysisService      — 🆕 聚合 AI 所需数据 + 形态摘要     │
└──────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌────────────────────┐ ┌─────────────────┐ ┌─────────────────────┐
│   领域层            │ │ 基础设施层       │ │   异步任务           │
│  Kline BO/VO       │ │ 采集器           │ │  OperationDispatcher │
│  (扩展指标字段)    │ │ TushareFetcher   │ │  TaskRegistry        │
│                    │ │ KlineRepoImpl    │ │  (asyncio)           │
│                    │ │ IndicatorCalc    │ └─────────────────────┘
└────────────────────┘ └─────────────────┘
                                │
                                ▼
                      ┌─────────────────────┐
                      │   数据库              │
                      │  stock_infos        │
                      │  daily_klines       │
                      │    + 17 指标列     │
                      │  stock_pools        │
                      │  stock_pool_members │
                      │  pool_operations    │
                      └─────────────────────┘
```

**关键变化**：
- ❌ ~~`IndicatorAppService`~~ → 合并到 `KlineAppService`
- ❌ ~~`daily_indicators` 表~~ → 字段直接展宽
- ❌ ~~`IndicatorRepoImpl`~~ → 走 `KlineRepoImpl.upsert_with_indicators()`
- 🆕 `StockAnalysisService` — 给 AI 用的聚合服务

---

## 4. 数据模型

### 4.1 `daily_klines`（扩展后）

```python
# infrastructure/database/models/kline.py
class DailyKlineDB(Base, TimestampMixin):
    __tablename__ = "daily_klines"

    # ── K 线基础字段（已有）─────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[float]
    high: Mapped[float]
    low: Mapped[float]
    close: Mapped[float]
    volume: Mapped[int]
    amount: Mapped[float]
    change_pct: Mapped[float | None]

    # ── 🆕 技术指标字段（NUMERIC, 允许 NULL）─────────────
    # 均线
    ma5:  Mapped[float | None] = mapped_column(Float, nullable=True)
    ma10: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma20: Mapped[float | None] = mapped_column(Float, nullable=True)
    ma60: Mapped[float | None] = mapped_column(Float, nullable=True)
    # EMA
    ema12: Mapped[float | None] = mapped_column(Float, nullable=True)
    ema26: Mapped[float | None] = mapped_column(Float, nullable=True)
    # MACD
    macd_dif: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_bar: Mapped[float | None] = mapped_column(Float, nullable=True)
    # RSI
    rsi6:  Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Float, nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Float, nullable=True)
    # KDJ
    kdj_k: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Float, nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Float, nullable=True)
    # BOLL
    boll_up: Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Float, nullable=True)
    boll_dn: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("symbol", "date", name="uq_kline_symbol_date"),
        Index("ix_kline_symbol_date", "symbol", "date"),
    )
```

### 4.2 Alembic Migration

```python
# alembic/versions/xxxx_add_indicators_to_daily_klines.py

def upgrade():
    op.add_column("daily_klines", sa.Column("ma5",     sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("ma10",    sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("ma20",    sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("ma60",    sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("ema12",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("ema26",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("macd_dif", sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("macd_dea", sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("macd_bar", sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("rsi6",    sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("rsi12",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("rsi24",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("kdj_k",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("kdj_d",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("kdj_j",   sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("boll_up", sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("boll_mid",sa.Float(), nullable=True))
    op.add_column("daily_klines", sa.Column("boll_dn", sa.Float(), nullable=True))

def downgrade():
    for col in ["ma5","ma10","ma20","ma60",
                "ema12","ema26",
                "macd_dif","macd_dea","macd_bar",
                "rsi6","rsi12","rsi24",
                "kdj_k","kdj_d","kdj_j",
                "boll_up","boll_mid","boll_dn"]:
        op.drop_column("daily_klines", col)
```

> **A 股 23 年 ~3000 万行**：PostgreSQL 单表 1 亿行以下不需分区, `ALTER TABLE ADD COLUMN ... NULL` 在 PG11+ 是元数据级操作（毫秒级）, 完全无压力。

### 4.3 领域层 Kline 实体扩展

```python
# domain/kline/entity.py
@dataclass
class Kline(AggregateRoot):
    # ... 原有字段 ...
    change_pct: Optional[float] = None

    # 🆕 指标字段
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_bar: Optional[float] = None
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_up: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn: Optional[float] = None
```

> 指标逻辑上属于 K 线的「派生属性」（基于历史 close 计算）, 不是独立聚合根。展宽到 Kline 实体最自然。

---

## 5. Tushare daily 接口集成

> 字段映射、Parser 实现与原文档一致, 此处只列出与方案 A 相关的差异。

### 5.1 K 线入库后立即触发指标计算

```python
# application/kline_service.py
class KlineAppService:
    """K 线服务（采集 / 查询 / 指标计算 三合一）"""

    def __init__(
        self,
        kline_repo: KlineRepository,
        fetcher: TushareFetcher,
        indicator_calc: IndicatorCalculator,   # 🆕 注入分析模块的计算器
    ):
        self._repo = kline_repo
        self._fetcher = fetcher
        self._calc = indicator_calc

    async def collect(self, symbol: str, days: int = 365) -> KlineCollectResponse:
        """拉取并入库, 自动算指标"""
        # 1) 拉 K 线
        klines = await self._fetcher.fetch(CollectParams(symbol=symbol, days=days))

        # 2) 计算指标（整个时间区间一起算, 保证窗口连续）
        klines_with_ind = self._enrich_with_indicators(klines)

        # 3) UPSERT 入库（kline + 指标一同写入）
        saved = await self._repo.upsert_batch(klines_with_ind)
        return KlineCollectResponse(saved_count=saved, total_count=len(klines))

    def _enrich_with_indicators(self, klines: list[Kline]) -> list[Kline]:
        """用分析模块的 IndicatorCalculator 给 kline 列表补齐指标字段"""
        df = self._klines_to_df(klines)
        ind_df = self._calc.to_dataframe(df)   # 见 §6.1
        # 把 ind_df 的列写回 Kline 对象
        for i, k in enumerate(klines):
            row = ind_df.iloc[i]
            k.ma5 = _to_float(row.get("ma5"))
            k.ma10 = _to_float(row.get("ma10"))
            # ... 其余 15 个字段 ...
        return klines
```

> **关键点**：计算指标必须基于「完整时间序列」（至少 60 天窗口）, 否则新一天入库时窗口数据不足会算出错的 MA60。`_enrich_with_indicators` 拿到的是全量序列, 没问题。

---

## 6. 技术指标计算

### 6.1 复用 `analysis` 模块的计算逻辑

> `backend/docs/01/backend/analysis/analysis_module.md` 已经定义了 `IndicatorCalculator`。**本步骤直接复用**, 不重复实现。

```python
# analysis/indicators.py （已有, 此处引用其接口）

class IndicatorCalculator:
    """技术指标计算器（复用）"""

    def calculate_all(self, klines: list[KlineData]) -> list[IndicatorData]:
        """返回与 klines 等长的 IndicatorData 列表"""
        ...

    def to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """接受 close/high/low DataFrame, 返回 17 列指标的 DataFrame"""
        # 输出列：ma5, ma10, ma20, ma60, ema12, ema26,
        #        dif(=macd_dif), dea(=macd_dea), macd_hist(=macd_bar),
        #        rsi6, rsi12, rsi24, k(=kdj_k), d(=kdj_d), j(=kdj_j),
        #        boll_upper(=boll_up), boll_mid(=boll_mid), boll_lower(=boll_dn)
        ...
```

> 注：`analysis` 模块用的是 `dif / dea / macd_hist / boll_upper / boll_lower / k / d / j`, 展宽到 `daily_klines` 时统一改为 `macd_dif / macd_dea / macd_bar / boll_up / boll_dn / kdj_k / kdj_d / kdj_j`, 命名风格更一致（带前缀,避免歧义）。

### 6.2 KlineAppService 计算流程

```python
# application/kline_service.py （接续 §5.1）

async def collect(self, symbol: str, days: int = 365):
    klines = await self._fetcher.fetch(...)

    # ── 计算指标 ────────────────────────────────────────
    # 取该股票最近 60 + days 天 K 线（确保窗口数据充足）
    full_klines = await self._repo.find_by_symbol(
        symbol=StockCode(symbol),
        start_date=date.today() - timedelta(days=days + 60),
    )
    df = self._klines_to_df(full_klines)
    ind_df = self._calc.to_dataframe(df)

    # 把「最近 days 天」的指标写回 Kline 对象
    target_dates = {k.trade_date.date for k in klines}
    ind_by_date = ind_df.set_index("date").to_dict("index")
    for k in klines:
        row = ind_by_date.get(k.trade_date.date)
        if row:
            self._fill_indicators(k, row)

    saved = await self._repo.upsert_batch(klines)
    return KlineCollectResponse(saved_count=saved, total_count=len(klines))


async def recalculate(self, symbol: str, days: int = 60) -> int:
    """增量重算：拉最近 N 天 K 线, 重算指标列并 UPSERT"""
    end = date.today()
    start = end - timedelta(days=days)
    full_klines = await self._repo.find_by_symbol(symbol, start_date=start - timedelta(days=60))

    df = self._klines_to_df(full_klines)
    ind_df = self._calc.to_dataframe(df)

    # 只更新最近 days 天
    target_dates = {d.date() for d in pd.date_range(start, end)}
    target_klines = [k for k in full_klines if k.trade_date.date in target_dates]
    for k in target_klines:
        row = ind_df[ind_df["date"] == k.trade_date.date].iloc[0]
        self._fill_indicators(k, row)

    return await self._repo.upsert_batch(target_klines)
```

### 6.3 池级全量重算（管理员命令）

```python
# application/kline_service.py

async def recalculate_pool(self, pool_id: int, days: int = 365) -> dict[str, int]:
    """一次性重算整个池（不需要异步任务, < 200 只股票秒级完成）"""
    members = await self._pool_repo.list_members(pool_id)
    results = {}
    for m in members:
        try:
            saved = await self.recalculate(m.symbol, days=days)
            results[m.symbol] = saved
        except Exception as e:
            results[m.symbol] = -1
            logger.exception("recalculate %s failed", m.symbol)
    return results
```

> 原方案的 `indicator_calc` 异步任务 **取消**。理由：
> - 单股票重算 < 50ms, 池级 200 只 < 10s, 同步即可
> - 异步任务反而增加复杂度（progress / cancel / 重试）
> - 池级重算极少触发, 用同步 API 调用即可

---

## 7. AI 归因分析接口

### 7.1 `GET /stocks/{symbol}/analysis`

> **核心接口**: 给前端图表 + 后续 AI Agent 用的统一入口。一次拿全「股票档案」。

```python
# route/api/v1/stock_analysis.py
from fastapi import APIRouter, Depends, Query
from application.stock_analysis_service import StockAnalysisService

router = APIRouter()

@router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(
    symbol: str,
    days: int = Query(365, ge=30, le=1825),
    service: StockAnalysisService = Depends(),
):
    return await service.build(symbol=symbol, days=days)
```

### 7.2 响应 Schema

```python
# application/dto/stock_analysis.py
from pydantic import BaseModel, Field
from typing import Optional

class StockInfo(BaseModel):
    symbol: str
    name: str
    industry: Optional[str] = None
    market: Optional[str] = None        # 主板 / 创业板 / 科创板

class TechnicalSummary(BaseModel):
    """技术形态摘要 — 后端算好, AI 直接用"""
    latest_close: float
    pct_change_1d: float                # 当日涨幅 %
    pct_change_30d: float               # 近 30 日涨幅 %

    # 均线
    ma_alignment: str                   # "bullish" | "bearish" | "neutral"
    ma5_above_ma20: bool
    golden_cross_recent: bool           # 近 5 日内是否出现金叉

    # MACD
    macd_status: str                    # "golden_cross" | "death_cross" | "above_zero" | "below_zero"
    macd_dif: float
    macd_dea: float
    macd_bar: float

    # RSI
    rsi6: float
    rsi_status: str                     # "overbought" | "oversold" | "neutral"

    # KDJ
    kdj_k: float
    kdj_d: float
    kdj_j: float
    kdj_status: str                     # "golden_cross" | "death_cross" | "overbought" | "oversold"

    # BOLL
    boll_position: str                  # "above_upper" | "below_lower" | "upper_half" | "lower_half"

    # 综合信号
    signals: list[str] = []            # ["MACD 金叉", "KDJ 超卖", "突破布林上轨", ...]

class KlineWithIndicator(BaseModel):
    """单日 K 线 + 指标（喂给 AI 的最小单元）"""
    date: str                           # YYYY-MM-DD
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: Optional[float] = None
    # 指标（每日一行, 一并返回, AI 拿到就能直接分析）
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    ema12: Optional[float] = None
    ema26: Optional[float] = None
    macd_dif: Optional[float] = None
    macd_dea: Optional[float] = None
    macd_bar: Optional[float] = None
    rsi6: Optional[float] = None
    rsi12: Optional[float] = None
    rsi24: Optional[float] = None
    kdj_k: Optional[float] = None
    kdj_d: Optional[float] = None
    kdj_j: Optional[float] = None
    boll_up: Optional[float] = None
    boll_mid: Optional[float] = None
    boll_dn: Optional[float] = None

class PoolMembership(BaseModel):
    pool_id: int
    pool_name: str
    joined_at: str

class StockAnalysisResponse(BaseModel):
    """完整响应"""
    stock: StockInfo
    summary: TechnicalSummary
    klines: list[KlineWithIndicator]
    pools: list[PoolMembership] = []
```

### 7.3 响应示例

```json
GET /stocks/000001/analysis?days=90

{
  "code": 0,
  "data": {
    "stock": {
      "symbol": "000001",
      "name": "平安银行",
      "industry": "银行",
      "market": "主板"
    },
    "summary": {
      "latest_close": 12.34,
      "pct_change_1d": 1.2,
      "pct_change_30d": 5.2,
      "ma_alignment": "bullish",
      "ma5_above_ma20": true,
      "golden_cross_recent": true,
      "macd_status": "golden_cross",
      "macd_dif": 0.15,
      "macd_dea": 0.10,
      "macd_bar": 0.10,
      "rsi6": 65.3,
      "rsi_status": "neutral",
      "kdj_k": 78.5,
      "kdj_d": 72.3,
      "kdj_j": 91.0,
      "kdj_status": "overbought",
      "boll_position": "upper_half",
      "signals": ["MA 多头排列", "MACD 金叉", "KDJ 超买"]
    },
    "klines": [
      {
        "date": "2025-01-02",
        "open": 12.10, "high": 12.30, "low": 12.05, "close": 12.25,
        "volume": 1234567, "change_pct": 1.2,
        "ma5": 12.18, "ma20": 12.05,
        "macd_dif": 0.15, "macd_dea": 0.10, "macd_bar": 0.10,
        "rsi6": 65.3, "kdj_k": 78, "kdj_d": 72, "kdj_j": 91,
        "boll_up": 13.50, "boll_mid": 12.25, "boll_dn": 11.00
      }
      // ... 共 ~60 行
    ],
    "pools": [
      { "pool_id": 3, "pool_name": "核心持仓", "joined_at": "2025-01-10" }
    ]
  }
}
```

### 7.4 StockAnalysisService 实现

```python
# application/stock_analysis_service.py

class StockAnalysisService:
    """AI 归因分析入口服务"""

    def __init__(
        self,
        kline_repo: KlineRepository,
        stock_repo: StockRepository,
        pool_repo: StockPoolRepository,
        signal_detector: SignalDetector,    # §8
    ):
        self._kline_repo = kline_repo
        self._stock_repo = stock_repo
        self._pool_repo = pool_repo
        self._signal = signal_detector

    async def build(self, symbol: str, days: int) -> dict:
        # 1) 股票基本信息
        stock_info = await self._stock_repo.find_by_symbol(symbol)
        if not stock_info:
            raise NotFoundError(f"股票不存在: {symbol}")

        # 2) K 线 + 指标（一行一交易日, 来自 daily_klines）
        end = date.today()
        start = end - timedelta(days=days)
        klines = await self._kline_repo.find_by_symbol(
            StockCode(symbol), start_date=start, end_date=end
        )
        if not klines:
            raise NotFoundError(f"暂无 K 线数据, 请先采集: {symbol}")

        # 3) 技术形态摘要（基于最近一日 + 前 5 日）
        summary = self._signal.summarize(klines)

        # 4) 所在池
        pools = await self._pool_repo.list_pools_containing_symbol(symbol)

        # 5) 转 VO
        return {
            "stock": StockInfo(
                symbol=stock_info.symbol,
                name=stock_info.name,
                industry=stock_info.industry,
                market=stock_info.market,
            ).model_dump(),
            "summary": summary.model_dump(),
            "klines": [self._to_kline_vo(k) for k in klines],
            "pools": [PoolMembership(...).model_dump() for p in pools],
        }
```

---

## 8. 技术形态摘要（SignalDetector）

> 把"金叉/死叉/超买/突破"这种**形态判断**放在后端做, AI 拿到的是已经提炼过的信号 + 原始数据, 不用自己再算一遍。

```python
# application/signals.py（独立小模块, 不依赖 analysis/）

class SignalDetector:
    """技术形态摘要生成器（基于已计算好的指标列）"""

    def summarize(self, klines: list[Kline]) -> TechnicalSummary:
        latest = klines[-1]
        prev = klines[-2] if len(klines) > 1 else None
        prev5 = klines[-6] if len(klines) >= 6 else None

        signals: list[str] = []

        # ── 均线 ──────────────────────────────────────────
        ma_align = "neutral"
        if all([latest.ma5, latest.ma10, latest.ma20]):
            if latest.ma5 > latest.ma10 > latest.ma20:
                ma_align = "bullish"
                signals.append("MA 多头排列")
            elif latest.ma5 < latest.ma10 < latest.ma20:
                ma_align = "bearish"
                signals.append("MA 空头排列")

        golden_cross_recent = False
        if prev and prev5:
            # 近 5 日内 MA5 上穿 MA20
            if (
                prev5.ma5 and prev5.ma20
                and prev.ma5 and prev.ma20
                and prev5.ma5 <= prev5.ma20
                and prev.ma5 > prev.ma20
            ):
                golden_cross_recent = True
                signals.append("MA 金叉")

        # ── MACD ──────────────────────────────────────────
        macd_status = "neutral"
        if latest.macd_dif is not None and latest.macd_dea is not None:
            if prev and prev.macd_dif is not None:
                if prev.macd_dif <= prev.macd_dea and latest.macd_dif > latest.macd_dea:
                    macd_status = "golden_cross"
                    signals.append("MACD 金叉")
                elif prev.macd_dif >= prev.macd_dea and latest.macd_dif < latest.macd_dea:
                    macd_status = "death_cross"
                    signals.append("MACD 死叉")
            if latest.macd_dif > 0 and macd_status == "neutral":
                macd_status = "above_zero"
            elif latest.macd_dif < 0 and macd_status == "neutral":
                macd_status = "below_zero"

        # ── RSI ───────────────────────────────────────────
        rsi_status = "neutral"
        if latest.rsi6 is not None:
            if latest.rsi6 > 70:
                rsi_status = "overbought"
                signals.append("RSI 超买")
            elif latest.rsi6 < 30:
                rsi_status = "oversold"
                signals.append("RSI 超卖")

        # ── KDJ ───────────────────────────────────────────
        kdj_status = "neutral"
        if latest.kdj_k is not None and latest.kdj_d is not None:
            if prev and prev.kdj_k is not None:
                if prev.kdj_k <= prev.kdj_d and latest.kdj_k > latest.kdj_d:
                    kdj_status = "golden_cross"
                    signals.append("KDJ 金叉")
                elif prev.kdj_k >= prev.kdj_d and latest.kdj_k < latest.kdj_d:
                    kdj_status = "death_cross"
                    signals.append("KDJ 死叉")
            if kdj_status == "neutral":
                if latest.kdj_j > 100:
                    kdj_status = "overbought"
                    signals.append("KDJ 超买")
                elif latest.kdj_j < 0:
                    kdj_status = "oversold"
                    signals.append("KDJ 超卖")

        # ── BOLL ──────────────────────────────────────────
        boll_position = "middle"
        if latest.boll_up and latest.boll_dn:
            if latest.close > latest.boll_up:
                boll_position = "above_upper"
                signals.append("突破布林上轨")
            elif latest.close < latest.boll_dn:
                boll_position = "below_lower"
                signals.append("跌破布林下轨")
            elif latest.close > latest.boll_mid:
                boll_position = "upper_half"
            else:
                boll_position = "lower_half"

        # ── 涨跌幅 ────────────────────────────────────────
        pct_1d = latest.change_pct or 0.0
        pct_30d = 0.0
        if len(klines) >= 30:
            pct_30d = (latest.close / klines[-30].close - 1) * 100

        return TechnicalSummary(
            latest_close=latest.close,
            pct_change_1d=pct_1d,
            pct_change_30d=pct_30d,
            ma_alignment=ma_align,
            ma5_above_ma20=(latest.ma5 or 0) > (latest.ma20 or 0),
            golden_cross_recent=golden_cross_recent,
            macd_status=macd_status,
            macd_dif=latest.macd_dif or 0.0,
            macd_dea=latest.macd_dea or 0.0,
            macd_bar=latest.macd_bar or 0.0,
            rsi6=latest.rsi6 or 0.0,
            rsi_status=rsi_status,
            kdj_k=latest.kdj_k or 0.0,
            kdj_d=latest.kdj_d or 0.0,
            kdj_j=latest.kdj_j or 0.0,
            kdj_status=kdj_status,
            boll_position=boll_position,
            signals=signals,
        )
```

---

## 9. K 线查询 API

### 9.1 端点表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`  | `/klines/{symbol}` | 查询 K 线 + 指标（带时间范围） |
| `GET`  | `/klines/{symbol}/latest` | 最新一天 |
| `GET`  | `/klines/{symbol}/stats` | 统计（总天数/最新日期） |
| `POST` | `/klines/collect` | 单只采集（同步） |
| `POST` | `/pools/{id}/operations` | 池级批量采集（异步, 复用） |
| `GET`  | `/operations/{id}/progress` | 轮询进度（复用） |
| `GET`  | `/stocks/{symbol}/analysis` | 🆕 AI 归因分析入口 |
| `POST` | `/admin/indicators/recalculate` | 🆕 管理员：全市场重算（异步） |

### 9.2 `GET /klines/{symbol}` 响应

```json
GET /klines/000001?start_date=2025-01-01&end_date=2025-03-31&limit=60

{
  "code": 0,
  "data": {
    "symbol": "000001",
    "total": 60,
    "items": [
      {
        "date": "2025-01-02",
        "open": 12.10, "high": 12.30, "low": 12.05, "close": 12.25,
        "volume": 1234567, "amount": 1.5e8, "change_pct": 1.2,
        "ma5": 12.18, "ma10": 12.15, "ma20": 12.05, "ma60": 11.80,
        "ema12": 12.20, "ema26": 12.10,
        "macd_dif": 0.15, "macd_dea": 0.10, "macd_bar": 0.10,
        "rsi6": 65.3, "rsi12": 62.1, "rsi24": 58.7,
        "kdj_k": 78.5, "kdj_d": 72.3, "kdj_j": 91.0,
        "boll_up": 13.50, "boll_mid": 12.25, "boll_dn": 11.00
      }
    ]
  }
}
```

> **注意**：K 线查询与 `/stocks/{symbol}/analysis` 返回结构略有不同 ——
> - `/klines/{symbol}`：返回原始数据数组, 用于图表绘制
> - `/stocks/{symbol}/analysis`：聚合对象（含 summary / pools）, 用于 AI / 详情面板

---

## 10. 数据流与时序

### 10.1 单只采集（含指标）

```
POST /klines/collect  { symbol: "000001", days: 365 }
   │
   ▼
KlineAppService.collect()
   ├─► TushareFetcher.fetch() → pro.daily(000001, 1y)
   ├─► KlineRepoImpl.find_by_symbol(最近 425 天)  ← 取窗口数据
   ├─► IndicatorCalculator.to_dataframe(df)      ← 算 17 个指标
   ├─► 把指标写回 Kline 对象
   └─► KlineRepoImpl.upsert_batch()
         └─► ON CONFLICT (symbol, date) DO UPDATE SET
               ma5=EXCLUDED.ma5, macd_dif=EXCLUDED.macd_dif, ...

返回 { saved_count, total_count }
```

### 10.2 每日增量（15:10 定时任务）

```
15:10  cron
   │
   ▼
KlineAppService.collect_latest(all_symbols)
   ├─► 对每只股票：
   │     ├─► 拉取自上次以来的 K 线
   │     ├─► 拉最近 60 天 K 线（用于指标窗口）
   │     ├─► 重算指标
   │     └─► UPSERT
   └─► 全部完成
```

### 10.3 池级批量拉取（异步, 复用现有）

```
POST /pools/{id}/operations  { operation_type: "kline_collect", days: 365 }
   │
   ▼
PoolOperationAppService.create_kline_collect_operation()
   ├─► 取池成员 symbols
   ├─► 创建 PoolOperation (status=pending)
   └─► OperationDispatcher.dispatch_kline_collect()
         └─► asyncio.create_task(_run())
               ├─► 遍历 symbols:
               │     └─► KlineAppService.collect()  ← 已经含指标
               └─► 更新 progress + 最终状态
```

> 池级采集完成后 **不需要** 再单独触发指标计算 — 因为 `KlineAppService.collect()` 已经把指标算好并入库了。

### 10.4 AI 查询（前端图表 / Agent）

```
GET /stocks/000001/analysis?days=90
   │
   ▼
StockAnalysisService.build()
   ├─► StockRepository.find_by_symbol()
   ├─► KlineRepository.find_by_symbol(最近 90 天)
   ├─► SignalDetector.summarize()        ← 金叉/超买/突破 等
   ├─► PoolRepository.list_pools_containing_symbol()
   └─► 组装 StockAnalysisResponse
```

---

## 11. 关键设计决策

### 11.1 数据存储：方案 A（展宽）✅

| 对比项 | 展宽到 kline ✅ | 独立长表 ❌ | JSON 字段 |
|--------|--------|--------|--------|
| 行数 | 3000 万 | **5.4 亿** | 3000 万 |
| AI 友好 | 一次取齐 | 需服务端聚合 | 需解析 |
| 扩展性 | ALTER TABLE | 加行 | 加字段 |
| 写性能 | UPSERT 单表 | 多次 INSERT | JSON 序列化 |

### 11.2 取消独立的 `IndicatorAppService`

指标是 K 线的派生属性, 与 K 线生命周期绑定（K 线入库即算指标）。
合到 `KlineAppService` 后少一层抽象, 代码更内聚。

### 11.3 取消 `indicator_calc` 异步任务

| 方案 | 耗时（200 只股票） | 异步价值 |
|------|--------------------|----------|
| 同步调用 | < 10s | ❌ 没必要 |
| 异步任务 | 同样 < 10s | 多一层复杂度, 多一个状态机**不值得** |

池级重算极少触发, 用 `POST /admin/indicators/recalculate` 一次性同步调用即可。

### 11.4 K 线不复权

归因分析使用不复权价格计算收益率, 与 Barra / CITIC 模型一致。

### 11.5 节假日

Tushare 返回的是实际交易日数据, 自动跳过节假日。

---

## 12. 文件清单

### 新增文件

```
backend/src/
├── application/
│   ├── stock_analysis_service.py       # 🆕 AI 入口服务
│   ├── signals.py                       # 🆕 SignalDetector 技术形态
│   └── dto/
│       └── stock_analysis.py            # 🆕 Response Schemas
│
└── route/api/v1/
    └── stock_analysis.py                # 🆕 /stocks/{symbol}/analysis
```

### 修改文件

| 文件 | 修改 |
|------|------|
| `domain/kline/entity.py` | 加 17 个指标字段 |
| `domain/kline/schemas.py` | 加 17 个指标字段 |
| `infrastructure/database/models/kline.py` | 加 17 列 |
| `infrastructure/repositories/kline_repository.py` | `upsert_batch` 写指标列 |
| `application/kline_service.py` | 合并指标计算（注入 `IndicatorCalculator`） |
| `route/api/v1/kline.py` | 响应包含指标字段 |
| `alembic/versions/xxxx_add_indicators.py` | 加 17 列 migration |
| `dependencies.py` | 注入 `StockAnalysisService` |
| `route/api/router.py` | 注册 stock_analysis router |

### 路由注册

```python
# route/api/router.py
from route.api.v1.stock_analysis import router as stock_analysis_router

router.include_router(stock_analysis_router, tags=["AI 归因"])
```

---

## 13. 单元测试要点

### 13.1 指标计算（已有 `analysis` 模块测试）

```python
def test_indicator_calculator_enriches_kline():
    """指标计算后 Kline 对象的指标字段被填充"""
    klines = [Kline.create(...)] * 100  # mock 100 天
    calc = IndicatorCalculator()
    ind_df = calc.to_dataframe(_to_df(klines))
    assert "ma5" in ind_df.columns
    assert "kdj_j" in ind_df.columns
    assert len(ind_df) == 100
```

### 13.2 SignalDetector（形态判断）

```python
def test_macd_golden_cross_detected():
    """DIF 上穿 DEA → golden_cross"""
    klines = _make_klines_with_macd(
        dif_series=[0.05, 0.06, 0.07, 0.08],   # 单调上升
        dea_series=[0.10, 0.10, 0.10, 0.10],
    )
    sig = SignalDetector().summarize(klines)
    assert "MACD 金叉" in sig.signals
    assert sig.macd_status == "golden_cross"

def test_rsi_overbought():
    klines = _make_klines_with_rsi(rsi6=85.0)
    sig = SignalDetector().summarize(klines)
    assert sig.rsi_status == "overbought"
    assert "RSI 超买" in sig.signals
```

### 13.3 AI Analysis 接口

```python
@pytest.mark.asyncio
async def test_stock_analysis_returns_complete_payload(async_session):
    service = StockAnalysisService(...)
    # 准备 60 天 mock kline + 股票信息
    await _seed_stock(async_session, "000001", "平安银行")
    await _seed_klines(async_session, "000001", days=60)

    result = await service.build("000001", days=60)

    assert result["stock"]["symbol"] == "000001"
    assert len(result["klines"]) == 60
    assert "summary" in result
    assert isinstance(result["summary"]["signals"], list)
```

---

## 14. 实施计划

### Step 5.1：数据模型扩展
- [ ] `daily_klines` 加 17 个指标列（migration）
- [ ] `Kline` 实体加 17 个字段
- [ ] `Kline` ORM 加 17 个字段
- [ ] 跑迁移 + 回归

### Step 5.2：K 线 + 指标入库一体化
- [ ] `KlineAppService.collect()` 接入 `IndicatorCalculator`
- [ ] `KlineRepoImpl.upsert_batch()` 支持 ON CONFLICT 更新指标列
- [ ] 单元测试

### Step 5.3：K 线查询返回指标
- [ ] `/klines/{symbol}` 响应加 17 个字段
- [ ] 前端能直接拿到 MA / MACD / KDJ 等

### Step 5.4：AI 归因分析接口
- [ ] `StockAnalysisService.build()` 实现
- [ ] `SignalDetector` 实现（金叉 / 超买 / 突破 等）
- [ ] `/stocks/{symbol}/analysis` 路由注册
- [ ] OpenAPI 文档更新

### Step 5.5：池级采集（保留异步）+ 取消 indicator_calc
- [ ] `PoolOperation.operation_type` 移除 `indicator_calc` 类型
- [ ] 池级批量拉取测试（确认 K 线 + 指标同时入库）

### Step 5.6：管理后台
- [ ] `POST /admin/indicators/recalculate` 同步端点
- [ ] 前端管理页（可选）

### Step 5.7：端到端联调
- [ ] 采集 → 入库 → AI 接口 完整链路
- [ ] 前端 K 线图渲染（蜡烛图 + 副图指标）
- [ ] AI Agent 调用 `/analysis` 验证返回结构