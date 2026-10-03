# 07 — Dashboard 综合大盘（全链路方案）

> 状态：方案，**未改代码**
> 路由：**重写** `/home/index`（原 `Dashboard.vue` → 新 `Dashboard.vue`，路由路径不变）
> 后端：新增 `dashboard.py` + 1 个接口 `GET /dashboard/summary` + 仓储扩展 3 个聚合方法
> 前端：完整重写 `views/Dashboard.vue`
> 实时：30 秒轮询（卡 + Top 榜；图表按需刷）

---

## 1. 业务需求

| 维度 | 说明 |
|---|---|
| 场景 | 用户进首页 `/home/index` 看到**今日全市场概览**：涨跌家数 / 量能 / 行业板块表现 / Top 涨跌幅 / 概念榜 / 自选 / 池速览 |
| 核心功能 | ① 8 张统计卡（A 股总数 / 涨 / 跌 / 平 / 涨停 / 跌停 / 成交额 / 北向净流入） ② 行业涨跌幅柱状图（Top 10 / Bottom 10） ③ 概念涨跌幅柱状图（Top 10） ④ 涨停 / 跌停 / 炸板分布饼图 ⑤ Top 涨 / 跌榜（各 10） ⑥ 自选 / 池速览 ⑦ 30s 轮询卡和榜 |
| 与现状区别 | 现状 `Dashboard.vue`（项目索引 §4 描述）内容简单，本方案**完全重写**为综合大盘，**路由 `/home/index` 不变** |

---

## 2. 路由与菜单接入

**0 改动**。原路由 `/home/index` 仍指向 `Dashboard.vue`（同文件覆盖式重写）。

---

## 3. 后端设计

### 3.1 文件清单

| # | 路径 | 性质 | 改动行数 |
|---|---|---|---|
| 1 | `backend/src/route/api/v1/dashboard.py` | **新增** | ~50 行 |
| 2 | `backend/src/route/api/router.py` | **追加 1 个 include** | +3 行 |
| 3 | `backend/src/route/dto/response/dashboard.py` | **新增** | ~80 行 |
| 4 | `backend/src/application/service/dashboard_app_service.py` | **新增** | ~120 行 |
| 5 | `backend/src/infrastructure/config/di.py` | **追加 1 个工厂** | +15 行 |
| 6 | `backend/src/infrastructure/persistence/repositories/stock_repository.py` | **追加 3 个方法** | +60 行 |

> **0 新表**。

### 3.2 响应 VO

```python
# backend/src/route/dto/response/dashboard.py
from typing import Optional
from pydantic import BaseModel, Field

from route.dto.response.panel import StockRealtimeItemVO


class DashboardCountVO(BaseModel):
    """统计卡 VO（一组卡）"""
    total: int = 0                  # A 股总数
    up: int = 0
    down: int = 0
    flat: int = 0
    limit_up: int = 0
    limit_down: int = 0
    broken_limit_up: int = 0        # 炸板数
    total_amount: float = 0.0       # 成交额（亿元）
    north_net: Optional[float] = None   # 北向净流入（亿元）— 如未实现则 None

    model_config = {"from_attributes": True}


class SectorRankItemVO(BaseModel):
    """行业板块涨跌幅（来自 fin_daily_basics 聚合）"""
    name: str
    pct_change: float
    up_count: int
    down_count: int
    total: int

    model_config = {"from_attributes": True}


class LimitUpListItemVO(BaseModel):
    """涨停 / 跌停列表行（只含关键字段）"""
    symbol: str
    name: str
    pct_change: float
    latest_close: float
    continuous: int = 1             # 连板数
    industry: Optional[str] = None

    model_config = {"from_attributes": True}


class ConceptRankItemVO(BaseModel):
    """概念榜行（精简版）"""
    concept_id: int
    name: str
    pct_change: float
    stock_count: int
    up_count: int

    model_config = {"from_attributes": True}


class PoolOverviewVO(BaseModel):
    """池速览（一组）"""
    pool_id: int
    name: str
    pool_type: str
    member_count: int
    avg_pct_change: Optional[float] = None
    top_symbol: Optional[str] = None
    top_pct_change: Optional[float] = None

    model_config = {"from_attributes": True}


class DashboardSummaryVO(BaseModel):
    """综合大盘聚合响应"""
    counts: DashboardCountVO
    sector_top: list[SectorRankItemVO]        # 行业涨幅 Top 10
    sector_bottom: list[SectorRankItemVO]     # 行业跌幅 Top 10
    concept_top: list[ConceptRankItemVO]      # 概念 Top 10
    top_gainers: list[LimitUpListItemVO]      # 涨幅 Top 10
    top_losers: list[LimitUpListItemVO]       # 跌幅 Top 10
    limit_up_list: list[LimitUpListItemVO]    # 涨停列表（25）
    broken_up_list: list[LimitUpListItemVO]   # 炸板列表（10）
    pools: list[PoolOverviewVO]               # 池速览

    captured_at: Optional[str] = None
    stale: bool = False                       # 行情源失败 fallback

    model_config = {"from_attributes": True}
```

### 3.3 仓储扩展（**只在 `stock_repository.py` 末尾追加**）

```python
# backend/src/infrastructure/persistence/repositories/stock_repository.py 末尾追加

async def count_dashboard(self) -> dict:
    """统计卡聚合

    返回:
      {
        'total': int,
        'up': int, 'down': int, 'flat': int,
        'limit_up': int, 'limit_down': int, 'broken_limit_up': int,
        'total_amount': float,
      }

    策略：
    - total / up / down / flat / total_amount 来自 realtime / latest_fin_daily_basics
    - limit_up / limit_down / broken_limit_up 来自 fin_daily_basics（同日 pct_change >= 9.95% / <= -9.95%）
    - 注：涨停按科创板 / 创业 / 北交 阈值不同，简化按 9.95% / -9.95%
    """
    # 1) 今日日期
    today = (await self._session.scalar(select(func.max(FinDailyBasic.trade_date)))) or date.today()

    # 2) 涨 / 跌 / 平 计数（来自 fin_daily_basics 最新一日）
    row = await self._session.execute(
        select(
            func.count().label("total"),
            func.sum(case((FinDailyBasic.pct_change > 0, 1), else_=0)).label("up"),
            func.sum(case((FinDailyBasic.pct_change < 0, 1), else_=0)).label("down"),
            func.sum(case((FinDailyBasic.pct_change == 0, 1), else_=0)).label("flat"),
            func.sum(FinDailyBasic.amount_mv).label("total_amount"),
        ).where(FinDailyBasic.trade_date == today)
    )
    r = row.one()
    total_amount = (r.total_amount or 0) * 10000 / 1e8  # 转亿元

    # 3) 涨停 / 跌停 / 炸板（仅主板 9.95%；科创 19.95% 等暂忽略）
    limit_row = await self._session.execute(
        select(
            func.sum(case((FinDailyBasic.pct_change >= 9.95, 1), else_=0)).label("lu"),
            func.sum(case((FinDailyBasic.pct_change <= -9.95, 1), else_=0)).label("ld"),
            # 炸板：昨涨停今日开板（昨 high-pct >=9.95 但 close-pct < 9.95）— 复杂，本期省略
        ).where(FinDailyBasic.trade_date == today)
    )
    lu = limit_row.one()
    return {
        "total": r.total or 0,
        "up": int(r.up or 0),
        "down": int(r.down or 0),
        "flat": int(r.flat or 0),
        "limit_up": int(lu.lu or 0),
        "limit_down": int(lu.ld or 0),
        "broken_limit_up": 0,
        "total_amount": round(total_amount, 1),
    }


async def list_sector_ranks(self, top_k: int = 10) -> tuple[list[dict], list[dict]]:
    """行业板块涨跌幅 Top / Bottom

    按 industry 分组聚合 fin_daily_basics 最新一日 pct_change
    """
    today = await self._session.scalar(select(func.max(FinDailyBasic.trade_date)))
    if not today:
        return [], []
    stmt = (
        select(
            StockInfo.industry.label("name"),
            func.avg(FinDailyBasic.pct_change).label("pct_change"),
            func.sum(case((FinDailyBasic.pct_change > 0, 1), else_=0)).label("up_count"),
            func.sum(case((FinDailyBasic.pct_change < 0, 1), else_=0)).label("down_count"),
            func.count().label("total"),
        )
        .select_from(FinDailyBasic)
        .join(StockInfo, StockInfo.symbol == FinDailyBasic.symbol)
        .where(
            FinDailyBasic.trade_date == today,
            StockInfo.industry.isnot(None),
        )
        .group_by(StockInfo.industry)
    )
    all_rows = (await self._session.execute(stmt)).mappings().all()
    sorted_desc = sorted(all_rows, key=lambda x: -(x["pct_change"] or 0))
    sorted_asc  = sorted(all_rows, key=lambda x:  (x["pct_change"] or 0))
    return sorted_desc[:top_k], sorted_asc[:top_k]


async def list_top_movers(
    self, direction: Literal["up", "down"], limit: int = 10
) -> list[dict]:
    """涨幅 / 跌幅 Top 10
    direction='up'  按 pct_change DESC
    direction='down' 按 pct_change ASC
    """
    today = await self._session.scalar(select(func.max(FinDailyBasic.trade_date)))
    if not today:
        return []
    stmt = (
        select(
            FinDailyBasic.symbol, StockInfo.name,
            FinDailyBasic.pct_change, FinDailyBasic.close.label("latest_close"),
            StockInfo.industry,
        )
        .join(StockInfo, StockInfo.symbol == FinDailyBasic.symbol)
        .where(FinDailyBasic.trade_date == today, FinDailyBasic.pct_change.isnot(None))
        .order_by(FinDailyBasic.pct_change.desc() if direction == "up" else FinDailyBasic.pct_change.asc())
        .limit(limit)
    )
    return [dict(r) for r in (await self._session.execute(stmt)).mappings().all()]
```

> 类似地扩展 `list_limit_up_list`（按 pct_change >= 9.95）、`list_concept_top`（复用 01 的 concept board，sort_by=pct_change, top 10）、`list_pool_overview`（聚合 stock_pool_members + fin_daily_basics），本处不展开。

### 3.4 应用服务（**新建**）

```python
# backend/src/application/service/dashboard_app_service.py
from datetime import datetime
from typing import Optional

from application.service.base import BaseAppService
from domain.entitys.dashboard import DashboardSummary       # 协议 (新建)
from infrastructure.persistence.repositories.stock_repository import StockRepository
from infrastructure.persistence.repositories.concept_repository import ConceptRepository
from infrastructure.persistence.repositories.pool_repository import PoolRepository
from route.dto.response.dashboard import DashboardSummaryVO


class DashboardAppService(BaseAppService):
    def __init__(
        self,
        stock_repo: StockRepository,
        concept_repo: ConceptRepository,
        pool_repo: PoolRepository,
    ):
        self._stock_repo = stock_repo
        self._concept_repo = concept_repo
        self._pool_repo = pool_repo

    async def query_summary(self) -> DashboardSummaryVO:
        # 并发查 6 类数据
        import asyncio
        counts, (sector_top, sector_bottom), concept_top, gainers, losers, limit_up, pools = await asyncio.gather(
            self._stock_repo.count_dashboard(),
            self._stock_repo.list_sector_ranks(10),
            self._concept_repo.list_board_rows(type_filter=None, sort_by="pct_change", order="desc", page=1, page_size=10),
            self._stock_repo.list_top_movers("up", 10),
            self._stock_repo.list_top_movers("down", 10),
            self._stock_repo.list_limit_up_list(25),
            self._pool_repo.list_overview(top_k_per_pool=1),
        )
        return DashboardSummaryVO(
            counts=DashboardCountVO(**counts),
            sector_top=[SectorRankItemVO(**s) for s in sector_top],
            sector_bottom=[SectorRankItemVO(**s) for s in sector_bottom],
            concept_top=[ConceptRankItemVO(
                concept_id=r.concept_id, name=r.name,
                pct_change=0,   # 实时值由前端单独再请求 /concepts/board?page_size=10 覆盖
                stock_count=r.stock_count, up_count=0,
            ) for r in concept_top],
            top_gainers=[LimitUpListItemVO(**g, continuous=1) for g in gainers],
            top_losers=[LimitUpListItemVO(**l, continuous=1) for l in losers],
            limit_up_list=[LimitUpListItemVO(**x, continuous=1) for x in limit_up],
            broken_up_list=[],
            pools=[PoolOverviewVO(**p) for p in pools],
            captured_at=datetime.now().isoformat(),
        )
```

### 3.5 路由（**新建**）

```python
# backend/src/route/api/v1/dashboard.py
from fastapi import APIRouter, Depends
from application.service.dashboard_app_service import DashboardAppService
from infrastructure.config.di import get_dashboard_app_service

router = APIRouter(tags=["dashboard"])


@router.get("/summary", response_model=None, summary="综合大盘聚合")
async def get_dashboard_summary(
    app: DashboardAppService = Depends(get_dashboard_app_service),
):
    """首页 `/home/index` 调用。30s 缓存（前端轮询即可）。"""
    return R.ok((await app.query_summary()).model_dump())
```

### 3.6 `di.py` 追加

```python
# backend/src/infrastructure/config/di.py 末尾追加

def get_dashboard_app_service(
    stock_repo: StockRepository = Depends(get_stock_repository),
    concept_repo: ConceptRepository = Depends(get_concept_repository),
    pool_repo: PoolRepository = Depends(get_pool_repository),
) -> DashboardAppService:
    return DashboardAppService(stock_repo, concept_repo, pool_repo)
```

### 3.7 `router.py` 追加

```python
# backend/src/route/api/router.py
from route.api.v1 import dashboard  # 末尾追加

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
```

---

## 4. 前端设计

### 4.1 文件清单

| # | 路径 | 性质 |
|---|---|---|
| 1 | `frontend/src/views/Dashboard.vue` | **完全重写** |
| 2 | `frontend/src/views/dashboard/api.ts` | **新建** |
| 3 | `frontend/src/views/dashboard/components/CountCards.vue` | **新建** |
| 4 | `frontend/src/views/dashboard/components/SectorBar.vue` | **新建** |
| 5 | `frontend/src/views/dashboard/components/LimitUpList.vue` | **新建** |
| 6 | `frontend/src/views/dashboard/components/TopMovers.vue` | **新建** |
| 7 | `frontend/src/views/dashboard/components/PoolOverview.vue` | **新建** |
| 8 | `frontend/src/views/dashboard/components/ConceptTopList.vue` | **新建** |

### 4.2 `Dashboard.vue`（重写后骨架）

```vue
<template>
  <PageWrapper :style="densityStyle" class="dv-page">
    <template #title>
      <el-icon class="mr-1"><HomeFilled /></el-icon>
      综合大盘
      <span class="page-title-text">今日全市场概览 · 30秒刷新</span>
      <el-tag size="small" :type="isTrading ? 'success' : 'info'" class="ml-2">
        {{ isTrading ? '实时' : '已收盘' }} · {{ lastUpdateText }}
      </el-tag>
    </template>

    <template #toolbar>
      <div class="toolbar-row">
        <div class="toolbar-search">
          <el-input v-model="quickSymbol" placeholder="输入代码跳转详情..." clearable :prefix-icon="Search" @keyup.enter="onJump" />
        </div>
        <div class="toolbar-actions">
          <el-button @click="load"><el-icon class="mr-1"><Refresh /></el-icon>立即刷新</el-button>
        </div>
      </div>
    </template>

    <!-- 8 张统计卡 -->
    <CountCards :counts="summary.counts" class="dv-cards" />

    <!-- 主体 grid：4 张图 + Top 榜 + 池速览 -->
    <div class="dv-grid">
      <div class="dv-cell">
        <h3>📊 行业涨幅 Top 10</h3>
        <SectorBar :data="summary.sector_top" :direction="'up'" />
      </div>
      <div class="dv-cell">
        <h3>📉 行业跌幅 Top 10</h3>
        <SectorBar :data="summary.sector_bottom" :direction="'down'" />
      </div>
      <div class="dv-cell">
        <h3>🔥 涨停 / 跌停分布</h3>
        <LimitUpList :items="summary.limit_up_list" :broken="summary.broken_up_list" />
      </div>
      <div class="dv-cell">
        <h3>🏆 涨幅榜 Top 10</h3>
        <TopMovers :items="summary.top_gainers" :direction="'up'" />
      </div>
      <div class="dv-cell">
        <h3>🧊 跌幅榜 Top 10</h3>
        <TopMovers :items="summary.top_losers" :direction="'down'" />
      </div>
      <div class="dv-cell">
        <h3>💡 概念涨幅 Top 10</h3>
        <ConceptTopList :items="summary.concept_top" />
      </div>
      <div class="dv-cell dv-cell--span2">
        <h3>📂 池速览</h3>
        <PoolOverview :pools="summary.pools" />
      </div>
    </div>
  </PageWrapper>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { HomeFilled, Search, Refresh } from '@element-plus/icons-vue'
import PageWrapper from '@/components/PageWrapper.vue'
import { useRealtimePoll } from '@/composables/useRealtimePoll'
import { getDashboardSummary, type DashboardSummary } from './dashboard/api'
import CountCards from './dashboard/components/CountCards.vue'
import SectorBar from './dashboard/components/SectorBar.vue'
import LimitUpList from './dashboard/components/LimitUpList.vue'
import TopMovers from './dashboard/components/TopMovers.vue'
import PoolOverview from './dashboard/components/PoolOverview.vue'
import ConceptTopList from './dashboard/components/ConceptTopList.vue'

const router = useRouter()
const summary = ref<DashboardSummary>({} as any)
const quickSymbol = ref('')
const isTrading = ref(false)
const lastUpdate = ref<Date | null>(null)

const lastUpdateText = computed(() => {
  if (!lastUpdate.value) return '—'
  return lastUpdate.value.toLocaleTimeString()
})

async function load() {
  try {
    summary.value = await getDashboardSummary()
    lastUpdate.value = new Date()
  } catch { /* silent */ }
}

const { start, stop } = useRealtimePoll(load, { intervalMs: 30000 })

function onJump() {
  if (!quickSymbol.value) return
  router.push(`/home/stock-panel?q=${quickSymbol.value}`)
}

onMounted(() => { load(); start() })
onUnmounted(() => stop())
</script>

<style scoped>
.dv-page { display: flex; flex-direction: column; height: 100%; }
.dv-cards { margin: 0.5rem; }
.dv-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-auto-rows: minmax(280px, auto);
  gap: 0.75rem;
  padding: 0.5rem;
  overflow: auto;
}
.dv-cell {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
}
.dv-cell h3 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #1e293b; }
.dv-cell--span2 { grid-column: span 2; }
</style>
```

### 4.3 关键子组件

#### `CountCards.vue`

```vue
<template>
  <div class="cc-grid">
    <div class="cc-card" v-for="c in cards" :key="c.key" :class="c.cls">
      <div class="cc-card__label">{{ c.label }}</div>
      <div class="cc-card__value">{{ c.value }}</div>
      <div class="cc-card__unit">{{ c.unit }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ counts: any }>()

const cards = computed(() => [
  { key: 'total',   label: 'A 股总数', value: props.counts.total ?? 0,         unit: '只',   cls: '' },
  { key: 'up',      label: '上涨',     value: props.counts.up ?? 0,            unit: '只',   cls: 'cc-card--up' },
  { key: 'down',    label: '下跌',     value: props.counts.down ?? 0,          unit: '只',   cls: 'cc-card--down' },
  { key: 'flat',    label: '平盘',     value: props.counts.flat ?? 0,          unit: '只',   cls: '' },
  { key: 'lu',      label: '涨停',     value: props.counts.limit_up ?? 0,      unit: '只',   cls: 'cc-card--up' },
  { key: 'ld',      label: '跌停',     value: props.counts.limit_down ?? 0,    unit: '只',   cls: 'cc-card--down' },
  { key: 'amt',     label: '成交额',   value: (props.counts.total_amount ?? 0).toFixed(0), unit: '亿', cls: '' },
  { key: 'north',   label: '北向资金', value: props.counts.north_net == null ? '—' : props.counts.north_net.toFixed(1), unit: '亿', cls: '' },
])
</script>

<style scoped>
.cc-grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 0.5rem; }
.cc-card { padding: 0.75rem; border-radius: 6px; background: #f8fafc; text-align: center; }
.cc-card--up   { background: linear-gradient(135deg, #fef2f2, #fff); }
.cc-card--down { background: linear-gradient(135deg, #f0fdf4, #fff); }
.cc-card__label { font-size: 0.8rem; color: #64748b; }
.cc-card__value { font-size: 1.5rem; font-weight: 700; margin: 4px 0; }
.cc-card--up   .cc-card__value { color: #dc2626; }
.cc-card--down .cc-card__value { color: #16a34a; }
.cc-card__unit  { font-size: 0.7rem; color: #94a3b8; }
</style>
```

#### `SectorBar.vue`（ECharts 横向柱状）

```vue
<template>
  <div ref="chartRef" class="sb-chart"></div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { use } from 'echarts/core'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{ data: any[]; direction: 'up' | 'down' }>()
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let ro: ResizeObserver | null = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)
  const sorted = [...props.data].sort((a, b) => a.pct_change - b.pct_change)
  const names = sorted.map(d => d.name)
  const values = sorted.map(d => d.pct_change)
  const color = props.direction === 'up' ? '#ef4444' : '#16a34a'
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' }, formatter: (p: any) => `${p[0].name}<br/>${p[0].value.toFixed(2)}%<br/>上涨 ${p[0].data.up_count} / 下跌 ${p[0].data.down_count}` },
    grid: { left: 90, right: 20, top: 10, bottom: 25 },
    xAxis: { type: 'value', axisLabel: { formatter: '{value}%', color: '#94a3b8' }, splitLine: { lineStyle: { color: '#f1f5f9' } } },
    yAxis: { type: 'category', data: names, axisLabel: { color: '#475569', fontSize: 11 } },
    series: [{ type: 'bar', data: values.map((v, i) => ({ value: v, ...sorted[i] })), itemStyle: { color } }],
  })
}

onMounted(() => { render(); ro = new ResizeObserver(() => chart?.resize()); chartRef.value && ro.observe(chartRef.value) })
watch(() => props.data, render, { deep: true })
onUnmounted(() => { ro?.disconnect(); chart?.dispose() })
</script>

<style scoped>
.sb-chart { width: 100%; height: 100%; min-height: 240px; }
</style>
```

#### `TopMovers.vue` / `LimitUpList.vue` / `PoolOverview.vue` / `ConceptTopList.vue`

> 这 4 个组件结构相似：左侧排名、右侧股票列表 + 涨跌幅色块。完整代码在 PR 时一次性补齐（约 50 行 / 个，参考 4.2）。

---

## 5. 性能与边界

| 维度 | 数值 | 备注 |
|---|---|---|
| 首次加载 | ~600ms | 6 个并发查询（asyncio.gather） |
| 30s 轮询 | 同上 | 全部走 fin_daily_basics（同日不变时几乎 0 成本） |
| 数据规模 | 全 A 5000 只 | 6 个聚合查 < 1s |
| 实时性 | 收盘后是收盘数据 | 盘中用实时接口覆盖 Top 榜（本期仅 30s 轮询收盘数据；盘中数据可后续加） |

---

## 6. 关键决策

| 问 | 答 |
|---|---|
| 为什么 Dashboard 重写不算 "修改现有页面"？ | 路由 `/home/index` 不变；文件 `Dashboard.vue` 是同路径覆盖（先 git rm 再 write，git 历史可保留）；用户已明确同意 "可重写现状版 Dashboard" |
| 30s 轮询与 15s 的取舍？ | 首页是"概览"而非"盯盘"，30s 减少 50% 后端压力；如未来要"实时榜"再升级 |
| 为什么 8 张卡而非 4 张？ | 8 张全在首屏可一次性看到，节省用户点击；与同花顺 / 东方财富首页一致 |
| 北向资金怎么查？ | 后端数据表是否有北向待确认；接口预留 `north_net: Optional[float] = None` 字段，无数据时显示 "—" |
| 炸板列表怎么算？ | 简化为空（待补 fetcher），UI 占位 |

---

## 7. 现状文档更新点

实施完成后，更新 `docs/overview/00-项目索引.md`：
- §4 API 表加 1 行（`GET /dashboard/summary`）
- §5 数据表（无变化）
- §7 前端路由表（无变化；路由路径不变）

