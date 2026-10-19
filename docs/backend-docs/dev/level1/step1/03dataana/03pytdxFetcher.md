# PytdxFetcher 分钟 K 线接入方案

## 一、目标

接入 pytdx（通达信行情协议），获取分钟级 K 线数据（5min / 30min），与现有 TushareFetcher 日 K 线并列。
前端 StockInfoList 表格支持点击行展开，在展开行中显示日 K 和分 K 两个 mini 图表。

## 二、整体架构

```
现有日 K 管线（保持不变）：
  POST /klines/collect → KlineAppService → TushareFetcher → tech_kline_dailys

新增分 K 管线（本次新增）：
  POST /minute-klines/collect → MinuteKlineService → PytdxFetcher → tech_kline_minutes

前端：
  StockInfoList 行点击 → expand row → 并发请求日K + 分K → 两个 mini CandleChart
```

## 三、后端改动

### 3.1 新增依赖

```
# requirements.txt 新增
pytdx>=1.72
```

### 3.2 新增文件清单

```
backend/src/
├── infrastructure/
│   ├── collectors/
│   │   └── pytdx/                          # 新增目录
│   │       ├── __init__.py
│   │       ├── fetcher.py                  # PytdxFetcher
│   │       └── parser.py                   # pytdx 数据 → MinuteKlineBO
│   ├── database/models/
│   │   └── tech_kline_minute.py            # 新增 ORM 模型
│   └── repositories/
│       └── minute_kline_repository.py      # 新增 Repository 实现
├── domain/
│   └── minute_kline/                       # 新增领域模块
│       ├── __init__.py
│       ├── entity.py                       # MinuteKline 实体
│       ├── schemas.py                      # MinuteKlineBO / MinuteKlineVO
│       └── repository.py                   # Repository 协议
├── application/
│   ├── minute_kline_service.py             # 新增服务
│   └── dto/
│       └── minute_kline.py                 # 新增 DTO
└── route/api/v1/
    └── minute_kline.py                     # 新增路由
```

### 3.3 数据库表：`tech_kline_minutes`

```sql
CREATE TABLE tech_kline_minutes (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(10)   NOT NULL,
    name        VARCHAR(50),
    datetime    TIMESTAMP     NOT NULL,   -- 分钟级时间戳（如 2026-09-18 10:35:00）
    interval    VARCHAR(10)   NOT NULL,   -- '5min' / '30min'
    open        FLOAT         NOT NULL,
    high        FLOAT         NOT NULL,
    low         FLOAT         NOT NULL,
    close       FLOAT         NOT NULL,
    volume      INTEGER       NOT NULL,
    amount      FLOAT         NOT NULL,
    change_pct  FLOAT,

    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),

    UNIQUE (symbol, datetime, interval)
);

CREATE INDEX ix_minute_kline_symbol_interval ON tech_kline_minutes (symbol, interval, datetime);
```

与日 K 表的区别：
- 时间字段用 `datetime`（DateTime）而非 `date`（Date）
- 新增 `interval` 字段区分周期
- **不存技术指标**（分 K 指标按需在前端/查询时计算，不展宽存储）

不存指标的理由：
1. 分 K 数据量大（一只股票一天 48 根 5min K 线），存 17 个指标列会膨胀
2. 分 K 的 mini 图表只展示 K 线走势，不需要 MA/MACD 等指标
3. 后续如需指标，可复用 `IndicatorCalculator` 在查询时实时计算

### 3.4 PytdxFetcher

```python
# backend/src/infrastructure/collectors/pytdx/fetcher.py

class PytdxFetcher(BaseCollector):
    """通达信分钟 K 线采集器"""

    # pytdx category 映射
    INTERVAL_MAP = {
        '1min':  7,
        '5min':  0,
        '15min': 1,
        '30min': 2,
        '60min': 3,
    }

    # pytdx 市场代码：0=深圳 1=上海
    # 根据 symbol 前缀判断

    def __init__(self):
        super().__init__()
        from pytdx.hq import TdxHq_API
        self._api = TdxHq_API(heartbeat=True, auto_retry=True)
        self._connected = False

    @property
    def source_name(self) -> str:
        return "Pytdx"

    def _ensure_connected(self):
        """确保连接到通达信服务器"""
        if not self._connected:
            # 优先尝试的服务器列表
            hosts = [
                ('119.147.212.81', 7709),
                ('14.17.75.71', 7709),
                ('218.75.126.9', 7709),
            ]
            for host, port in hosts:
                if self._api.connect(host, port):
                    self._connected = True
                    self._log("info", f"连接通达信服务器成功: {host}:{port}")
                    return
            raise RuntimeError("无法连接通达信服务器")

    def _symbol_to_market(self, symbol: str) -> int:
        """股票代码 → pytdx 市场代码（0=深圳 1=上海）"""
        prefix = symbol[:2]
        if prefix in ('60', '68', '11', '51'):
            return 1  # 上海
        return 0  # 深圳

    def fetch_minute_klines(
        self,
        symbol: str,
        interval: str = '5min',
        count: int = 800,
    ) -> list[MinuteKlineBO]:
        """采集分钟 K 线

        Args:
            symbol:   6 位股票代码
            interval: '1min' / '5min' / '15min' / '30min' / '60min'
            count:    获取的 K 线数量（最大 800/次，需分页）
        """
        category = self.INTERVAL_MAP.get(interval)
        if category is None:
            raise ValueError(f"不支持的周期: {interval}")

        market = self._symbol_to_market(symbol)
        self._ensure_connected()

        all_bars = []
        fetched = 0
        start = 0

        # pytdx 单次最多 800 根，分页获取
        while fetched < count:
            batch_size = min(800, count - fetched)
            bars = self._api.get_security_bars(
                category, market, symbol, start, batch_size
            )
            if not bars:
                break
            all_bars.extend(bars)
            fetched += len(bars)
            start += len(bars)
            if len(bars) < batch_size:
                break

        # 转为 DataFrame 后交给 parser
        df = self._api.to_df(all_bars) if all_bars else pd.DataFrame()
        return PytdxKlineParser.parse(df, symbol, interval)
```

### 3.5 MinuteKlineBO

```python
# backend/src/domain/minute_kline/schemas.py

class MinuteKlineBO(BaseModel):
    """分钟 K 线业务对象"""
    symbol:     str
    name:       str = ""
    datetime:   datetime      # 2026-09-18 10:35:00
    interval:   str           # '5min' / '30min'
    open:       float
    high:       float
    low:        float
    close:      float
    volume:     int
    amount:     float
    change_pct: Optional[float] = None
```

与日 K 的 `KlineBO` 的区别：`trade_date: date` → `datetime: datetime` + `interval: str`

### 3.6 API 路由

```
前缀：/minute-klines

POST /minute-klines/collect
  body: { symbol: "000001", interval: "5min", count: 800 }
  → 采集并存储

GET /minute-klines/{symbol}
  query: interval=5min&limit=200
  → 查询分 K 数据（按时间倒序）
```

### 3.7 不修改的部分

| 模块 | 说明 |
|------|------|
| TushareFetcher | 保持不变，继续负责日 K + stock_basic + daily_basic |
| KlineAppService | 保持不变，日 K 管线不动 |
| tech_kline_dailys | 表结构不变 |
| IndicatorCalculator | 保持不变，分 K 暂不存指标 |
| FetcherProtocol | 保持不变，PytdxFetcher 不实现此协议（它有自己的方法签名 `fetch_minute_klines`），避免侵入现有接口 |

## 四、前端改动

### 4.1 删除旧抽屉

删除以下文件和引用：
- `frontend/src/views/stock-info/components/StockDetailDrawer.vue`
- `StockInfoList.vue` 中的 `StockDetailDrawer` 引用、`detailVisible`、`detailStock`、`openDetail` 等相关代码

删除理由：
- 抽屉 Tab 1（基本信息）：TS 代码、交易所、行业等 8 个字段，表格列已全部展示，完全冗余
- 抽屉 Tab 2（K 线图）：改为展开行内嵌 mini 图表，体验更好
- 抽屉 Tab 3（归因分析）：只有一个占位按钮，还未实现

### 4.2 StockInfoList 展开行设计

将 `@row-click="openDetail"` 改为切换展开行：

```vue
<el-table ... @row-click="toggleExpand">
  <el-table-column type="expand">
    <template #default="{ row }">
      <StockExpandRow :stock="row" />
    </template>
  </el-table-column>
  ...
</el-table>
```

### 4.3 展开行布局

```
┌────────────────────────────────────────────────────────────────────┐
│ ☑ 000001  平安银行  12.35  1280亿  8.2  银行  主板  ...          │ ← 数据行
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─ 日K（30天）──────────────────┐  ┌─ 5分K（当日）─────────────┐ │
│  │                               │  │                           │ │
│  │  K 线蜡烛图                    │  │  K 线蜡烛图（纯 K 线）     │ │
│  │  + MA5 / MA20 均线叠加         │  │  无指标叠加               │ │
│  │  + 底部成交量柱                │  │  + 底部成交量柱            │ │
│  │                               │  │                           │ │
│  │  高度 160px                   │  │  高度 160px               │ │
│  └───────────────────────────────┘  └───────────────────────────┘ │
│                                                                    │
│  最新: 12.35  涨跌: +1.23%  成交量: 8.2万手   [拉取K线] [采集分K] │ ← 摘要 + 操作
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

**高度 160px（而非 120px）**：120 太挤，160 能同时显示 K 线主体 + 底部成交量柱。
展开行总高度约 200px（160 图 + 摘要行 + padding）。

### 4.4 展开行内容设计

| 区域 | 内容 | 说明 |
|------|------|------|
| 左图：日 K | K 线 + MA5/MA20 均线 + 成交量 | 数据已有（tech_kline_dailys 含指标列），显示最近 30 天 |
| 右图：分 K | 纯 K 线 + 成交量，无指标 | 新数据（pytdx 采集），显示最近 200 根 5min |
| 底部摘要 | 最新价、涨跌幅、成交量 | 从日 K 最后一条取 |
| 底部操作 | [拉取K线] [采集分K] | 手动触发采集 |

**不放 MACD/RSI/KDJ 等副图指标**，理由：
1. 副图本身需要 80-100px 高度，加上去展开行就要 300px+，太大
2. 展开行定位是"快速预览走势"，不是完整技术分析
3. 完整指标分析留给后续的操作池详情页 / 分析页

### 4.5 新增组件

**`frontend/src/views/stock-info/components/StockExpandRow.vue`**

展开行容器组件，负责：
- 接收 `stock` prop
- 展开时并发请求日 K + 分 K 数据
- 渲染两个 MiniKlineChart + 底部摘要

**`frontend/src/views/stock-info/components/MiniKlineChart.vue`**

精简版 K 线图组件，复用现有 `CandleChart.vue` 的 SVG 渲染逻辑，但：
- 固定高度 160px
- 日 K 模式：显示 K 线 + MA5/MA20 叠加 + 成交量
- 分 K 模式：只显示 K 线 + 成交量（无指标）
- 支持 hover 显示 OHLC 简要信息
- 无指标切换器、无时间范围选择器（精简）

### 4.6 新增 API 方法

```typescript
// frontend/src/views/stock-info/api.ts 新增

/** 分钟 K 线数据 */
export interface MinuteKline {
  datetime:    string   // "2026-09-18T10:35:00"
  interval:    string   // "5min"
  open:        number
  high:        number
  low:         number
  close:       number
  volume:      number
  amount:      number
  change_pct:  number | null
}

/** POST /minute-klines/collect  采集分钟 K 线 */
export const collectMinuteKlines = (body: {
  symbol: string
  interval?: string
  count?: number
}) => http.post<{ saved_count: number }>('/minute-klines/collect', body).then(unwrap)

/** GET /minute-klines/{symbol}  查询分钟 K 线 */
export const getMinuteKlines = (
  symbol: string,
  params: { interval?: string; limit?: number } = {}
) => http.get<{ items: MinuteKline[] }>(`/minute-klines/${symbol}`, { params }).then(unwrap)
```

### 4.7 交互流程

1. 用户点击表格某一行 → 该行展开（再次点击收起），同一时间只展开一行
2. 展开时并发请求（懒加载，展开才请求，收起时缓存）：
   - `GET /klines/{symbol}?limit=30&order_desc=false`（已有接口，日 K）
   - `GET /minute-klines/{symbol}?interval=5min&limit=200`（新接口，分 K）
3. 两个 MiniKlineChart 并排渲染
4. 如果数据为空，显示"暂无数据"和采集按钮

## 五、实施步骤

按依赖关系排序，建议逐步实施：

### 第一阶段：后端分 K 管线

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 1 | `requirements.txt` 新增 `pytdx` | requirements.txt |
| 2 | 新建 `domain/minute_kline/` 领域模块（entity, schemas, repository protocol） | 4 个文件 |
| 3 | 新建 `infrastructure/database/models/tech_kline_minute.py` ORM 模型 | 1 个文件 |
| 4 | 新建 `infrastructure/collectors/pytdx/` 采集器（fetcher + parser） | 3 个文件 |
| 5 | 新建 `infrastructure/repositories/minute_kline_repository.py` | 1 个文件 |
| 6 | 新建 `application/minute_kline_service.py` + DTO | 2 个文件 |
| 7 | 新建 `route/api/v1/minute_kline.py` + 注册路由 | 2 个文件 |
| 8 | 验证：本地启动后端，调用 `POST /minute-klines/collect` 采集数据 | — |

### 第二阶段：前端展开行

| 步骤 | 内容 | 涉及文件 |
|------|------|---------|
| 9 | 新增 `MiniKlineChart.vue` 组件 | 1 个文件 |
| 10 | `api.ts` 新增 `MinuteKline` 接口和 API 方法 | api.ts |
| 11 | `StockInfoList.vue` 改为展开行模式 | StockInfoList.vue |
| 12 | 验证：点击行 → 展开 → 日 K 和分 K 图表正确渲染 | — |

### 第三阶段（可选增强）

| 内容 | 说明 |
|------|------|
| 支持 30min / 15min 周期切换 | 展开行中加周期选择器 |
| 分 K 技术指标 | 复用 IndicatorCalculator 在查询时计算 |
| pytdx 连接池 | 多用户并发时复用连接 |
| PlantUML 更新 | 01.puml 新增 `tech_kline_minute` 表定义 |

## 六、pytdx 注意事项

| 事项 | 说明 |
|------|------|
| 服务器连接 | pytdx 连接通达信公网行情服务器，无需注册/Token |
| 连接不稳定 | 需实现重连机制（`auto_retry=True`）和多服务器 fallback |
| 单次限制 | 最多 800 根 K 线/次，需分页 |
| 盘中数据 | 交易时段（9:30-15:00）获取的是实时数据；收盘后获取的是当日完整数据 |
| 北交所 | pytdx 对北交所支持有限，可能获取不到部分股票 |
| Docker 部署 | pytdx 是纯 Python 包，不需要 gcc，不影响当前精简 Dockerfile |
