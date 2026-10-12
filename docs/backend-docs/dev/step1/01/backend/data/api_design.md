# 数据采集功能文档

## 功能概述

数据采集模块负责从 AkShare 获取 A 股 K 线数据，存储到 PostgreSQL 数据库，并提供完整的 CRUD 接口。

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集整体流程                           │
└─────────────────────────────────────────────────────────────────┘

  ┌─────────┐      ┌─────────────┐      ┌───────────┐      ┌──────────┐
  │  AkShare │ ───▶ │  Collector  │ ───▶ │  Service  │ ───▶ │ PostgreSQL │
  │   API    │      │  (编排层)    │      │ (存储层)  │      │   DB     │
  └─────────┘      └─────────────┘      └───────────┘      └──────────┘
                                              │
                                              ▼
                                       ┌─────────────┐
                                       │  FastAPI    │
                                       │    API      │
                                       └─────────────┘
```

---

## 功能清单

| 功能 | API | 说明 |
|------|-----|------|
| **采集数据** | `POST /api/v1/stocks/collect` | 从 AkShare 采集 K 线并存入数据库 |
| **查询数据** | `GET /api/v1/stocks/` | 查询已有 K 线数据 |
| **数据清单** | `GET /api/v1/stocks/inventory` | 查看已采集的股票列表 |
| **删除股票** | `DELETE /api/v1/stocks/{symbol}` | 删除整只股票的数据 |
| **删除单条** | `DELETE /api/v1/stocks/{symbol}/{date}` | 删除指定日期的数据 |

---

## API 详细设计

### 1. 采集数据

**请求**

```http
POST /api/v1/stocks/collect
Content-Type: application/json

{
  "symbol": "000001",
  "days": 365,
  "start_date": "2023-01-01",
  "end_date": "2024-01-01"
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码，如 `000001` |
| `days` | int | ❌ | 采集天数，默认 365，最大 3650 |
| `start_date` | date | ❌ | 开始日期（优先于 days） |
| `end_date` | date | ❌ | 结束日期（默认今天） |

**响应**

```json
{
  "status": "success",
  "symbol": "000001",
  "count": 250,
  "message": "成功采集并存储 250 条数据"
}
```

**错误响应**

```json
{
  "status": "failed",
  "symbol": "000001",
  "count": 0,
  "message": "采集失败: 网络超时"
}
```

---

### 2. 查询数据

**请求**

```http
GET /api/v1/stocks/?symbol=000001&start_date=2024-01-01&end_date=2024-06-01&limit=100
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `symbol` | string | ✅ | 股票代码 |
| `start_date` | date | ❌ | 开始日期 |
| `end_date` | date | ❌ | 结束日期 |
| `limit` | int | ❌ | 返回数量，默认 365，最大 1000 |

**响应**

```json
{
  "total": 120,
  "items": [
    {
      "id": 1,
      "symbol": "000001",
      "name": "平安银行",
      "date": "2024-06-01",
      "open": 12.34,
      "high": 12.56,
      "low": 12.20,
      "close": 12.45,
      "volume": 1234567,
      "amount": 12345678.90,
      "change_pct": 1.23
    }
  ]
}
```

---

### 3. 数据清单

**请求**

```http
GET /api/v1/stocks/inventory
```

**响应**

```json
{
  "total_stocks": 5,
  "total_records": 1250,
  "stocks": [
    {
      "symbol": "000001",
      "name": "平安银行",
      "record_count": 250,
      "date_range": {
        "start": "2023-01-01",
        "end": "2024-01-01"
      }
    },
    {
      "symbol": "600519",
      "name": "贵州茅台",
      "record_count": 250,
      "date_range": {
        "start": "2023-01-01",
        "end": "2024-01-01"
      }
    }
  ]
}
```

---

### 4. 删除股票数据

**请求**

```http
DELETE /api/v1/stocks/000001
```

**响应**

```json
{
  "status": "success",
  "symbol": "000001",
  "deleted_count": 250,
  "message": "成功删除 250 条数据"
}
```

---

### 5. 删除单条数据

**请求**

```http
DELETE /api/v1/stocks/000001/2024-06-01
```

**响应**

```json
{
  "status": "success",
  "symbol": "000001",
  "date": "2024-06-01",
  "message": "成功删除 1 条数据"
}
```

---

## 数据模型

### 采集数据结构（Python）

```python
from dataclasses import dataclass
from datetime import date

@dataclass
class DailyKline:
    """日K线数据"""
    symbol: str           # 股票代码
    name: str             # 股票名称
    trade_date: date      # 交易日期
    open: float           # 开盘价
    high: float           # 最高价
    low: float            # 最低价
    close: float          # 收盘价
    volume: int           # 成交量
    amount: float         # 成交额
    change_pct: float     # 涨跌幅 (%)
```

### 数据库模型

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | PK, AUTO | 主键 |
| `symbol` | String(10) | NOT NULL, INDEX | 股票代码 |
| `name` | String(50) | NULL | 股票名称 |
| `date` | Date | NOT NULL | 交易日期 |
| `open` | Float | NOT NULL | 开盘价 |
| `high` | Float | NOT NULL | 最高价 |
| `low` | Float | NOT NULL | 最低价 |
| `close` | Float | NOT NULL | 收盘价 |
| `volume` | Integer | NOT NULL | 成交量 |
| `amount` | Float | NOT NULL | 成交额 |
| `change_pct` | Float | NULL | 涨跌幅 |
| `created_at` | DateTime | AUTO | 创建时间 |
| `updated_at` | DateTime | AUTO | 更新时间 |

**索引**

```sql
-- 普通索引
CREATE INDEX idx_symbol ON daily_klines(symbol);

-- 唯一索引（防止重复）
CREATE UNIQUE INDEX idx_symbol_date ON daily_klines(symbol, date);
```

---

## 架构设计

### 分层结构

```
┌─────────────────────────────────────────────────────────────┐
│                      API 层 (app/)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  schemas/     - Pydantic 模型（请求/响应）            │   │
│  │  api/v1/      - 路由定义                             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service 层 (data/services/)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  StockService  - 业务逻辑（采集、存储、查询、删除）   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐       ┌─────────────────────────┐
│   Collector (编排层)    │       │     PostgreSQL DB       │
│  ─────────────────────  │       │  ─────────────────────  │
│  调用 Fetcher 获取数据   │       │  存储 K 线数据          │
│  本身不关心数据来源      │       │  提供查询能力           │
└─────────────────────────┘       └─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Fetcher 层 (data/adapters/)              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AkShareFetcher  - 具体实现                          │   │
│  │  · 调用 akshare API                                 │   │
│  │  · 解析 DataFrame                                   │   │
│  │  · 转换为 DailyKline                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                      外部数据源                              │
│                        AkShare                               │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── stocks.py          # 股票 API 路由
│   ├── schemas/
│   │   └── stock.py              # Pydantic 模型
│   └── main.py                   # FastAPI 入口
│
├── data/
│   ├── interfaces/
│   │   └── fetcher.py            # FetcherProtocol
│   ├── schemas/
│   │   └── kline.py              # DailyKline dataclass
│   ├── adapters/
│   │   └── akshare/
│   │       └── fetcher.py        # AkShareFetcher
│   ├── collectors/
│   │   └── collector.py          # Collector
│   └── services/
│       └── stock_service.py      # 业务逻辑
│
└── infra/
    └── database/
        ├── models/
        │   └── stock.py          # ORM 模型
        └── connection.py         # 数据库连接
```

---

## 实现细节

### 采集流程

```python
def collect_and_save(self, symbol: str, days: int = 365) -> int:
    """
    采集并存储流程：
    1. 构建采集参数
    2. 调用 Collector 采集数据
    3. 遍历数据，检查是否已存在
    4. 批量插入新数据
    5. 提交事务
    """
    # 1. 构建参数
    params = CollectParams(symbol=symbol, days=days)

    # 2. 采集数据（从 AkShare）
    klines: list[DailyKline] = self.collector.collect(params)

    # 3. 遍历存储
    saved_count = 0
    for kline in klines:
        # 检查是否已存在
        exists = self.db.query(DailyKlineDB).filter(
            DailyKlineDB.symbol == kline.symbol,
            DailyKlineDB.date == kline.trade_date,
        ).first()

        # 不存在则插入
        if not exists:
            self.db.add(DailyKlineDB(...))
            saved_count += 1

    # 4. 提交
    self.db.commit()
    return saved_count
```

### 防重复机制

```sql
-- 数据库层面保证唯一性
INSERT INTO daily_klines (symbol, date, ...)
VALUES ('000001', '2024-06-01', ...)
ON CONFLICT (symbol, date) DO NOTHING;
-- 或使用应用层判断 exists
```

---

## 错误处理

| 错误场景 | 处理方式 |
|----------|----------|
| AkShare 网络超时 | 返回 `status: failed`，提示网络问题 |
| 股票代码不存在 | 返回 `status: failed`，提示代码无效 |
| 数据库连接失败 | 返回 500 错误 |
| 重复数据 | 自动跳过，不报错 |

---

## 性能考虑

| 场景 | 数据量 | 预计耗时 |
|------|--------|----------|
| 采集 1 年数据 | 250 条 | 1-3 秒 |
| 采集 10 年数据 | 2500 条 | 3-10 秒 |
| 查询 1000 条 | - | < 100ms |
| 批量插入 100 条 | - | < 500ms |

---

## 前端交互建议

### 采集页面

```
┌────────────────────────────────────────────────────────────┐
│  采集数据                                                    │
├────────────────────────────────────────────────────────────┤
│  股票代码: [000001        ] 🔍                              │
│  股票名称: 平安银行                                          │
│                                                            │
│  采集范围:                                                  │
│  ○ 最近 N 天: [365        ]                                 │
│  ● 自定义区间                                               │
│    开始日期: [2023-01-01]                                  │
│    结束日期: [2024-06-30]                                  │
│                                                            │
│  [采集数据]                    [取消]                       │
└────────────────────────────────────────────────────────────┘

采集中...
┌────────────────────────────────────────────────────────────┐
│  ⏳ 正在从 AkShare 采集数据...                               │
│  ████████████░░░░░░░░░░░░░░  60%  (150/250 条)             │
│                                                            │
│  预计剩余: 2 秒                                             │
└────────────────────────────────────────────────────────────┘

采集完成
┌────────────────────────────────────────────────────────────┐
│  ✅ 采集完成                                                 │
│                                                            │
│  股票: 平安银行 (000001)                                    │
│  新增数据: 250 条                                           │
│  日期范围: 2023-01-01 ~ 2024-06-30                         │
│                                                            │
│  [查看数据]    [继续采集]    [返回列表]                      │
└────────────────────────────────────────────────────────────┘
```

### 数据管理页面

```
┌────────────────────────────────────────────────────────────┐
│  数据管理                                                    │
├────────────────────────────────────────────────────────────┤
│  [全部股票] [已采集 5 只] [共 1250 条数据]                   │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 000001 平安银行    250 条   2023-01 ~ 2024-06  [删除]│  │
│  │ 600519 贵州茅台    250 条   2023-01 ~ 2024-06  [删除]│  │
│  │ 000002 万科A       250 条   2023-01 ~ 2024-06  [删除]│  │
│  │ ...                                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  [批量删除]                                                 │
└────────────────────────────────────────────────────────────┘
```

---

## 相关文档

- [架构设计](./architecture.md)
- [环境配置](./step/01_env_setup.md)
- [核心配置](./step/02_core_setup.md)
- [数据库设置](./step/03_database_setup.md)
