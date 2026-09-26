# 02 DataObject 与接口契约设计

> Python 服务的 Pydantic DTO 定义、字段语义、命名规范、版本兼容策略。这是 Java 与 Python 联调的**唯一事实来源**。

---

## 1. 设计原则

| 原则     | 说明                                                          |
| -------- | ------------------------------------------------------------- |
| **稳定** | 一旦进入 `v1.0`，只增字段、不改字段类型、不删字段              |
| **扁平** | 不嵌套超过 2 层；时间字段统一 ISO 8601 字符串                  |
| **明确** | 所有数字字段类型固定（`float` / `int`），不混用 string 数字      |
| **可溯源** | 每个响应带 `source` 字段（enum），告诉 Java 数据从哪个源来的   |
| **可观测** | 大批量响应附带 `fetched_at` / `fetched_count` / `duration_ms` |

---

## 2. 通用类型

```python
# app/schemas/common.py
from enum import Enum
from datetime import datetime

class Source(str, Enum):
    TUSHARE = "tushare"
    AKSHARE = "akshare"
    EASTMONEY = "eastmoney"
    SINA = "sina"
    PYTDX = "pytdx"
    MIXED = "mixed"          # 多源合并

class AdjustType(str, Enum):
    NONE = "none"            # 不复权
    QFQ = "qfq"              # 前复权
    HFQ = "hfq"              # 后复权

class Interval(str, Enum):
    M1 = "1min"
    M5 = "5min"
    M15 = "15min"
    M30 = "30min"
    M60 = "60min"
    DAILY = "daily"          # 日 K（虽然是日级别，但放这里方便复用）

class Meta(BaseModel):
    """响应元信息。"""
    source: Source                          # 数据源
    fetched_at: datetime                    # 服务端拉取时间
    fetched_count: int                      # 原始条数（未去重前）
    duration_ms: int                        # Python 内部耗时
    warnings: list[str] = []                # 数据质量问题（不致命）
```

---

## 3. K 线 DataObject

### 3.1 日 K

```python
# app/schemas/kline.py
from pydantic import BaseModel, Field
from datetime import date
from .common import Source, AdjustType, Meta

class DailyKlineItem(BaseModel):
    """单条日 K 数据。"""
    symbol: str = Field(..., description="ts_code，例如 000001.SZ")
    trade_date: date = Field(..., description="交易日")
    open: float = Field(..., ge=0)
    high: float = Field(..., ge=0)
    low: float = Field(..., ge=0)
    close: float = Field(..., ge=0)
    volume: int = Field(..., ge=0, description="成交量（股）")
    amount: float = Field(..., ge=0, description="成交额（元）")
    change_pct: float | None = Field(None, description="涨跌幅 %，可能为 None（停牌）")
    adj_factor: float | None = Field(None, description="复权因子（仅 tushare）")
    adj: AdjustType = Field(AdjustType.QFQ, description="复权类型")

class DailyKlineRequest(BaseModel):
    symbol: str = Field(..., min_length=9, max_length=9, examples=["000001.SZ"])
    start_date: str = Field(..., regex=r"^\d{8}$", examples=["20250101"])
    end_date: str = Field(..., regex=r"^\d{8}$", examples=["20251231"])
    adj: AdjustType = Field(AdjustType.QFQ)

class DailyKlineResponse(BaseModel):
    symbol: str
    items: list[DailyKlineItem]
    meta: Meta
```

### 3.2 分 K

```python
class MinuteKlineItem(BaseModel):
    symbol: str
    datetime: str = Field(..., description="YYYY-MM-DD HH:MM，如 2026-01-02 09:35")
    interval: Interval
    open: float
    close: float
    high: float
    low: float
    volume: int
    amount: float | None = None

class MinuteKlineResponse(BaseModel):
    symbol: str
    interval: Interval
    items: list[MinuteKlineItem]
    meta: Meta
```

---

## 4. 股票基础信息

```python
# app/schemas/stock_basic.py
class StockBasicItem(BaseModel):
    symbol: str              # 6 位代码（无后缀）
    ts_code: str             # 带后缀，如 000001.SZ
    name: str
    industry: str | None = None
    market: str | None = None        # 主板/创业板/科创板
    exchange: str | None = None      # SSE/SZSE
    list_date: date | None = None
    delist_date: date | None = None
    is_hs: str | None = None         # 是否沪深港通标的 N/H/S
    act_name: str | None = None      # 实控人
    act_ent_type: str | None = None  # 实控人企业性质

class StockBasicResponse(BaseModel):
    items: list[StockBasicItem]
    meta: Meta
```

---

## 5. 概念板块

```python
# app/schemas/concept.py
class ConceptItem(BaseModel):
    code: str                # 东方财富 BK0xxx
    name: str                # 概念名称
    stock_count: int = 0
    change_pct: float | None = None

class ConceptResponse(BaseModel):
    items: list[ConceptItem]
    meta: Meta

class ConceptMemberItem(BaseModel):
    symbol: str
    name: str

class ConceptMemberRequest(BaseModel):
    concept_code: str        # BK0xxx

class ConceptMemberResponse(BaseModel):
    concept_code: str
    concept_name: str
    items: list[ConceptMemberItem]
    meta: Meta
```

---

## 6. 财务

```python
# app/schemas/financial.py
class FinReportItem(BaseModel):
    symbol: str
    ann_date: date
    end_date: date
    report_type: str         # 1=合并报表
    comp_type: str           # 1=一般工商业
    basic_eps: float | None = None
    diluted_eps: float | None = None
    total_revenue: float | None = None
    revenue: float | None = None
    operate_profit: float | None = None
    total_profit: float | None = None
    n_income: float | None = None
    n_income_attr_p: float | None = None
    total_assets: float | None = None
    total_liab: float | None = None
    total_hldr_eqy_exc_min_int: float | None = None
    n_cashflow_act: float | None = None
    n_cash_flows_fnc_act: float | None = None
    n_cashflow_inv_act: float | None = None

class FinReportResponse(BaseModel):
    items: list[FinReportItem]
    meta: Meta
```

---

## 7. 日频估值 / 资金 / 龙虎榜

```python
# app/schemas/daily_basic.py
class DailyBasicItem(BaseModel):
    symbol: str
    trade_date: date
    close: float | None = None
    turnover_rate: float | None = None
    turnover_rate_f: float | None = None
    volume_ratio: float | None = None
    pe: float | None = None
    pe_ttm: float | None = None
    pb: float | None = None
    ps: float | None = None
    ps_ttm: float | None = None
    dv_ratio: float | None = None
    dv_ttm: float | None = None
    total_share: float | None = None
    float_share: float | None = None
    free_share: float | None = None
    total_mv: float | None = None
    circ_mv: float | None = None
```

```python
# app/schemas/moneyflow.py
class MoneyflowItem(BaseModel):
    symbol: str
    trade_date: date
    buy_sm_vol: float | None
    buy_sm_amount: float | None
    sell_sm_vol: float | None
    sell_sm_amount: float | None
    # ... 略
    net_mf_vol: float | None
    net_mf_amount: float | None
```

```python
# app/schemas/top_list.py
class TopListItem(BaseModel):
    symbol: str
    trade_date: date
    name: str | None
    close: float | None
    pct_change: float | None
    amount: float | None
    net_buy: float | None
    # ... 略
```

---

## 8. 错误响应

所有错误响应统一格式：

```json
{
  "code": 50301,
  "msg": "upstream source unavailable: tushare 502",
  "trace_id": "uuid",
  "details": null
}
```

错误码体系：

| 范围   | 含义                       |
| ------ | -------------------------- |
| 400xx  | 客户端错误（参数非法）     |
| 401xx  | 鉴权失败（HMAC / nonce）   |
| 403xx  | IP 不在白名单              |
| 404xx  | 数据未找到                 |
| 429xx  | 限流                       |
| 500xx  | Python 服务内部错误        |
| 503xx  | 上游数据源不可用           |

---

## 9. 字段命名约定

| 维度         | 规则                                       | 例                       |
| ------------ | ------------------------------------------ | ------------------------ |
| 时间字段     | date → ISO 字符串 `YYYYMMDD` 或 `YYYY-MM-DD` | `trade_date` 字符串      |
|              | datetime → ISO 8601 字符串                 | `fetched_at`             |
| 数字字段     | 始终 Python 数值类型（int / float），不传 string | `close: float`           |
| 股票代码     | 6 位 `symbol`（无后缀） + 9 位 `ts_code`（带后缀） | `000001` / `000001.SZ`   |
| null 字段    | 缺失值用 `None`，JSON 序列化为 `null`（不省略） | `change_pct: null`       |
| 大小写        | 字段名统一 snake_case                       | `trade_date`             |
| 枚举          | 字符串枚举（`Source.TUSHARE` → `"tushare"`） | `"source": "tushare"`    |

---

## 10. 版本兼容策略

> **核心规则**：Java 端的反序列化配置 `FAIL_ON_UNKNOWN_PROPERTIES = false`（见 `application.yml`），允许 Python 端新增字段时不破坏 Java 解析。

### 10.1 兼容矩阵

| 操作               | 是否允许 | 说明                                       |
| ------------------ | -------- | ------------------------------------------ |
| 新增字段           | ✅       | Java 端忽略未知字段                         |
| 新增枚举值         | ✅       | Java 端以 string 接收                       |
| 字段类型扩展       | ⚠️       | 仅限 `int → int/float` 或 `None → T`        |
| 字段重命名         | ❌       | 必须新版本 + 双版本并行                      |
| 删除字段           | ❌       | 必须先标记 deprecated，运行 1 个版本后再删    |
| 修改字段语义       | ❌       | 必须新版本                                  |
| 修改枚举语义       | ❌       | 必须新版本                                  |

### 10.2 版本管理

- 接口路径带版本前缀：`/v1/collect/*`、`/v1/klines/*`
- 同一接口多版本并行至少 1 个季度
- 版本切换走 Nginx 灰度：90% 流量 `/v1`，10% 流量 `/v2`
- 版本切换完成后 `/v1` 标记 deprecated，再下个季度下线

### 10.3 Java 端反序列化约定

```java
// application.yml
spring:
  jackson:
    deserialization:
      fail-on-unknown-properties: false   # 必须保持 false
```

Java DTO 上 `@JsonIgnoreProperties(ignoreUnknown = true)` 兜底。

---

## 11. 字段语义对照表（Java ↔ Python）

> 这是联调时的速查表。字段必须一一对应（命名上 Python 是 snake_case，Java 端 Jackson 自动转 camelCase）。

| Python 字段          | Java 字段              | 类型       | 必填 | 备注                            |
| -------------------- | ---------------------- | ---------- | ---- | ------------------------------- |
| `symbol`             | `symbol`               | String     | ✅   | 6 位代码                        |
| `ts_code`            | `tsCode`               | String     | ✅   | 带后缀 9 位                     |
| `trade_date`         | `tradeDate`            | LocalDate  | ✅   | ISO 日期                        |
| `datetime`           | `datetime`             | String     | ✅   | "YYYY-MM-DD HH:MM"             |
| `open/high/low/close`| `open/high/low/close`  | Double     | ✅   |                                 |
| `volume`             | `volume`               | Long       | ✅   |                                 |
| `amount`             | `amount`               | Double     | ✅   |                                 |
| `change_pct`         | `changePct`            | Double     | ❌   | 停牌时为 null                   |
| `adj_factor`         | `adjFactor`            | Double     | ❌   | 仅 tushare 有                   |
| `source`             | `source`               | String     | ✅   | enum 字符串                     |
| `fetched_at`         | `fetchedAt`            | String     | ✅   | ISO 8601                        |
| `meta.warnings`      | `meta.warnings`        | List<String> | ❌ | 非致命告警                       |

---

## 12. 总结

- **DTO 是契约**：变字段先改文档
- **稳定向前**：新增字段兼容，破坏性变更走版本
- **null 是合法值**：缺失字段显式传 null，不省略
- **source 必填**：Java 拿到数据能立即知道来源
- **meta 可选**：用于排查，但不影响业务

---

## 13. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |
