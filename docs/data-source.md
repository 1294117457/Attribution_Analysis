# 数据源说明

**版本**：v4.0  
**日期**：2026年6月  
**技术栈**：AkShare + PostgreSQL

---

## 数据源全景图

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据源全景图                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   A股数据                    Web3 数据              全球金融数据  │
│   ┌─────────┐              ┌─────────┐           ┌─────────┐   │
│   │ AkShare │              │DeFiLlama│           │ Finnhub │   │
│   │ (主力)   │              │  Dune   │           │TwelveData│  │
│   │ BaoStock│              │Nansen   │           │ EODHD   │   │
│   │ Stoke   │              │         │           │         │   │
│   └─────────┘              └─────────┘           └─────────┘   │
│      免费                      免费+付费              免费+付费    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 核心数据源：AkShare

### 简介

**AkShare** 是一个开源的 Python 金融数据库，专注于 A 股市场的免费数据获取。

- **官网**：https://akshare.akfamily.xyz/
- **GitHub**：https://github.com/jindaxiang/akshare
- **数据接口**：200+ 接口
- **更新频率**：实时/日频

### 支持的数据类型

| 类型 | 接口 | 说明 |
|------|------|------|
| **股票行情** | `stock_zh_a_hist()` | 日线/周线/月线 |
| **实时行情** | `stock_zh_a_spot_em()` | 当日实时数据 |
| **分时数据** | `stock_zh_a_minute()` | 1/5/15/30/60 分钟 |
| **基本面** | `stock_financial_analysis_indicator()` | 财务指标 |
| **资金流向** | `stock_individual_fund_flow()` | 主力/散户资金流 |
| **龙虎榜** | `stock_lhb_detail_em()` | 龙虎榜数据 |
| **大宗交易** | `stock_block_trade()` | 大宗交易数据 |
| **股票新闻** | `stock_news_em()` | 个股新闻 |
| **公告数据** | `stock_announcement()` | 上市公司公告 |

### 安装

```bash
pip install akshare
```

### 基本使用

```python
import akshare as ak

# 获取贵州茅台日线数据
df = ak.stock_zh_a_hist(
    symbol="600519",      # 股票代码
    period="daily",        # 周期：daily/weekly/monthly
    start_date="20240101", # 开始日期
    end_date="20240625",   # 结束日期
    adjust="qfq"           # 复权：qfq（前复权）/ hfq（后复权）
)

print(df.head())
#           日期       开盘     收盘     最高     最低    成交量 ...
# 0  2024-01-02  1680.00  1695.50  1705.30  1678.20  3520000
# 1  2024-01-03  1695.50  1702.30  1710.00  1688.50  2850000
```

---

## 数据采集架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AkShare 数据采集                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐             │
│   │  日线数据    │     │  实时行情   │     │   新闻数据   │             │
│   │ 历史K线     │     │ 当日分时   │     │  个股新闻   │             │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘             │
│          │                    │                    │                    │
│          └────────────────────┼────────────────────┘                    │
│                               │                                         │
│                               ▼                                         │
│                    ┌──────────────────┐                                │
│                    │   数据处理层      │                                │
│                    │  • 格式转换       │                                │
│                    │  • 数据校验       │                                │
│                    │  • 异常处理       │                                │
│                    └────────┬─────────┘                                │
│                             │                                          │
│                             ▼                                          │
│                    ┌──────────────────┐                                │
│                    │   PostgreSQL      │                                │
│                    │   • K线数据      │                                │
│                    │   • 指标缓存      │                                │
│                    │   • 经验案例      │                                │
│                    └──────────────────┘                                │
│                             │                                          │
│                             ▼                                          │
│                    ┌──────────────────┐                                │
│                    │   pgvector       │                                │
│                    │   经验向量       │                                │
│                    └──────────────────┘                                │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 数据采集代码示例

### 单只股票采集

```python
# backend/scripts/collect_data.py
import akshare as ak
from datetime import datetime, timedelta
from app.db.session import get_db
from app.models.domain.kline import StockKline

def collect_single_stock(symbol: str, days: int = 365):
    """采集单只股票数据"""
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    # 获取日线数据
    df = ak.stock_zh_a_hist(
        symbol=symbol,
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )

    # 转换为数据库模型
    klines = []
    for _, row in df.iterrows():
        kline = StockKline(
            symbol=symbol,
            trade_date=datetime.strptime(row['日期'], '%Y-%m-%d').date(),
            open=row['开盘'],
            high=row['最高'],
            low=row['最低'],
            close=row['收盘'],
            volume=row['成交量'],
            amount=row['成交额']
        )
        klines.append(kline)

    # 批量写入数据库
    with get_db() as db:
        db.bulk_save_objects(klines)
        db.commit()

    return len(klines)
```

### 批量采集

```python
def collect_batch_stocks(symbols: list[str], days: int = 365):
    """批量采集多只股票"""
    results = []
    for symbol in symbols:
        try:
            count = collect_single_stock(symbol, days)
            results.append({"symbol": symbol, "status": "success", "count": count})
        except Exception as e:
            results.append({"symbol": symbol, "status": "failed", "error": str(e)})
    return results
```

### 命令行使用

```bash
# 采集单只股票
python scripts/collect_data.py --symbol 600519 --days 365

# 批量采集
python scripts/collect_data.py --mode batch --symbols 600519,000858,600036

# 全市场采集（需要较长时间）
python scripts/collect_data.py --mode market
```

---

## 数据存储设计

### K线数据表

```sql
-- PostgreSQL 表结构
CREATE TABLE stock_klines (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open DECIMAL(10, 2),
    high DECIMAL(10, 2),
    low DECIMAL(10, 2),
    close DECIMAL(10, 2),
    volume DECIMAL(20, 2),
    amount DECIMAL(20, 2),
    indicators JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(symbol, trade_date)
);

-- 索引
CREATE INDEX idx_klines_symbol ON stock_klines(symbol);
CREATE INDEX idx_klines_date ON stock_klines(trade_date);
CREATE INDEX idx_klines_symbol_date ON stock_klines(symbol, trade_date);
```

### 新闻数据表

```sql
CREATE TABLE stock_news (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    publish_date TIMESTAMP,
    source VARCHAR(100),
    url VARCHAR(1000),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_news_symbol ON stock_news(symbol);
CREATE INDEX idx_news_date ON stock_news(publish_date);
```

---

## 数据更新策略

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据更新策略                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   更新类型          │ 频率      │ 数据范围         │ 说明                │
│   ─────────────────────────────────────────────────────────────────   │
│   日线数据          │ 每日收盘后 │ 全市场          │ T+1 日 16:00 后    │
│   实时行情          │ 交易时间内 │ 全市场          │ 9:30 - 15:00       │
│   分时数据          │ 按需      │ 单只股票        │ 分析时获取          │
│   新闻数据          │ 每日      │ 全市场          │ 爬取财经网站        │
│   资金流向          │ 每日收盘后 │ 全市场          │ T+1 日 16:30 后    │
│   龙虎榜            │ 不定期    │ 上榜股票        │ 收盘后公布          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 定时任务配置

### 定时采集任务

```python
# backend/app/tasks/scheduled_tasks.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler()

def setup_scheduled_tasks():
    """配置定时任务"""

    # 每日 16:30 采集日线数据
    scheduler.add_job(
        collect_daily_klines,
        CronTrigger(hour=16, minute=30),
        id='collect_daily_klines'
    )

    # 每小时采集实时行情（交易时间内）
    scheduler.add_job(
        collect_realtime_quotes,
        CronTrigger(hour='9-11,13-15', minute=0),
        id='collect_realtime_quotes',
        if_running='skip'
    )

    # 每日 17:00 采集资金流向
    scheduler.add_job(
        collect_fund_flow,
        CronTrigger(hour=17, minute=0),
        id='collect_fund_flow'
    )

    # 每日 20:00 采集新闻数据
    scheduler.add_job(
        collect_news_data,
        CronTrigger(hour=20, minute=0),
        id='collect_news_data'
    )
```

---

## 其他数据源

### Web3 数据（可选）

```python
# DeFiLlama TVL 数据
def get_defi_tvl():
    url = "https://api.llama.fi/protocols"
    response = requests.get(url)
    return response.json()

# Dune Analytics 合约数据
def get_dune_data(query_id: int):
    url = f"https://api.dune.com/api/v1/query/{query_id}/results"
    headers = {"x-dune-api-key": DUNE_API_KEY}
    response = requests.get(url, headers=headers)
    return response.json()
```

### 全球金融数据（可选）

```python
# Twelve Data（需要 API Key）
def get_twelve_data(symbol: str):
    url = f"https://api.twelvedata.com/quote?symbol={symbol}&apikey=YOUR_KEY"
    response = requests.get(url)
    return response.json()

# Finnhub（需要 API Key）
def get_finnhub_news():
    url = "https://finnhub.io/api/v1/news?category=general&token=YOUR_KEY"
    response = requests.get(url)
    return response.json()
```

---

## 相关文档

- [架构文档](./architecture.md)
- [快速开始](./getting-started.md)
- [API 接口](./api.md)
- [部署指南](./deployment.md)
