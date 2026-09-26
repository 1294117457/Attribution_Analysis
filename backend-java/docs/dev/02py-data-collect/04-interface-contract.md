# 04 跨服务 HTTP 接口契约

> `data-collector`（Python）对 `backend-java`（Java）暴露的 HTTP 接口清单。
> 前端不直接调用 Python。所有 Python 接口只服务于 Java 内部调用。

---

## 0. 当前契约版本（Phase 1）

> **本 PR**：使用「明细 items」契约（Python 返回清洗后的明细，Java 入库）。
> **Phase 2**：将切换为「摘要 saved」契约（Python 自行入库，Java 只收摘要）。

| 字段 | Phase 1（本 PR） | Phase 2（后续 PR） |
| --- | --- | --- |
| `items` | ✅ 明细数组 | ❌ 移除 |
| `fetched` | ✅ 原始条数 | ✅ 保留 |
| `saved` | ❌ Java 端计算后回传 | ✅ Python 自填 |
| `source` | ✅ 实际命中源 | ✅ 保留 |
| `meta.warnings` | ✅ | ✅ |

---

## 1. 接口路径前缀

| 前缀         | 用途           | 调用方           | 数据流向 |
| ------------ | -------------- | ---------------- | -------- |
| `/v1/collect/*` | 批量采集（落库前） | Java → Python    | Java 入库 |
| `/v1/query/*`   | 即时查询（透传）   | Java → Python    | Java 返回前端 |
| `/v1/health`   | 健康检查        | Java 心跳 / K8s probe | -        |
| `/metrics`     | Prometheus 指标 | 监控系统           | -        |
| `/docs`        | OpenAPI 文档   | 联调人             | -        |

> 所有接口必须走 HMAC 验签（详见 `00-overview.md §3.2`）。

---

## 2. 接口清单（v1.0）

### 2.1 K 线

| Method | Path                     | 说明                              | Request Body                            | Response                  |
| ------ | ------------------------ | --------------------------------- | --------------------------------------- | ------------------------- |
| POST   | `/v1/collect/kline/daily` | 批量日 K 采集                      | `DailyKlineRequest`                     | `DailyKlineResponse`      |
| POST   | `/v1/collect/kline/minute` | 批量分 K 采集（如需落库）         | `MinuteKlineRequest`                    | `MinuteKlineResponse`     |
| GET    | `/v1/query/kline/minute`   | 即时分 K 查询（透传）             | query: `symbol, interval, count`         | `MinuteKlineResponse`     |

### 2.2 股票基础信息

| Method | Path                        | 说明                       | Request                  | Response                |
| ------ | --------------------------- | -------------------------- | ------------------------ | ----------------------- |
| POST   | `/v1/collect/stock/basic`   | 全量或按 symbols 采集       | `StockBasicRequest`      | `StockBasicResponse`    |
| GET    | `/v1/query/stock/info/{symbol}` | 单只股票信息即时查询     | -                        | `StockBasicItem`        |

### 2.3 财务

| Method | Path                       | 说明                       | Request                  | Response                |
| ------ | -------------------------- | -------------------------- | ------------------------ | ----------------------- |
| POST   | `/v1/collect/fin/report`   | 财务报表（全量或单股）      | `FinReportRequest`       | `FinReportResponse`     |
| POST   | `/v1/collect/daily/basic`  | 日频估值（按日期区间）      | `DailyBasicRequest`      | `DailyBasicResponse`    |

### 2.4 资金 / 龙虎榜

| Method | Path                       | 说明                       | Request                  | Response                |
| ------ | -------------------------- | -------------------------- | ------------------------ | ----------------------- |
| POST   | `/v1/collect/moneyflow`    | 个股资金流向                | `MoneyflowRequest`       | `MoneyflowResponse`     |
| POST   | `/v1/collect/top/list`     | 龙虎榜                      | `TopListRequest`         | `TopListResponse`       |
| POST   | `/v1/collect/block/trade`  | 大宗交易                    | `BlockTradeRequest`      | `BlockTradeResponse`    |
| POST   | `/v1/collect/holder/num`   | 股东人数                    | `HolderNumRequest`       | `HolderNumResponse`     |
| POST   | `/v1/collect/holder/top10` | 前十大股东                  | `Top10HolderRequest`     | `Top10HolderResponse`   |
| POST   | `/v1/collect/margin/detail` | 融资融券                    | `MarginDetailRequest`    | `MarginDetailResponse`  |

### 2.5 概念板块

| Method | Path                          | 说明                       | Request                       | Response                   |
| ------ | ----------------------------- | -------------------------- | ------------------------------ | -------------------------- |
| POST   | `/v1/collect/concept/list`    | 概念列表                    | `ConceptListRequest`           | `ConceptResponse`          |
| POST   | `/v1/collect/concept/members` | 概念成分股                  | `ConceptMemberRequest`         | `ConceptMemberResponse`    |

### 2.6 市场 / 大盘

| Method | Path                          | 说明                       | Request                  | Response                |
| ------ | ----------------------------- | -------------------------- | ------------------------ | ----------------------- |
| POST   | `/v1/collect/market/calendar` | 交易日历                    | `MarketCalendarRequest`  | `MarketCalendarResponse`|
| POST   | `/v1/collect/market/index`    | 大盘 / 行业指数日行情        | `MarketIndexRequest`     | `MarketIndexResponse`   |
| POST   | `/v1/collect/market/sector`   | 行业板块行情                | `SectorDailyRequest`     | `SectorDailyResponse`   |

### 2.7 健康

| Method | Path         | 说明                  | Request | Response      |
| ------ | ------------ | --------------------- | ------- | ------------- |
| GET    | `/v1/health` | 服务存活              | -       | `{"status":"ok"}` |
| GET    | `/v1/health/sources` | 各数据源可达性 | -    | `{"tushare":"ok","akshare":"degraded"}` |

---

## 3. 请求/响应契约示例

### 3.1 POST `/v1/collect/kline/daily`

**Request**：
```json
{
  "symbol": "000001.SZ",
  "start_date": "20250101",
  "end_date": "20251231",
  "adj": "qfq"
}
```

**Response**（200）：
```json
{
  "symbol": "000001.SZ",
  "items": [
    {
      "symbol": "000001.SZ",
      "trade_date": "2025-12-31",
      "open": 10.50,
      "high": 10.80,
      "low": 10.40,
      "close": 10.75,
      "volume": 12345678,
      "amount": 132456789.0,
      "change_pct": 0.95,
      "adj_factor": 1.052,
      "adj": "qfq"
    }
  ],
  "meta": {
    "source": "tushare",
    "fetched_at": "2026-01-02T17:00:23.456+08:00",
    "fetched_count": 243,
    "duration_ms": 245,
    "warnings": []
  }
}
```

**Response**（503 上游不可用）：
```json
{
  "code": 50301,
  "msg": "upstream source unavailable: tushare quota exceeded",
  "trace_id": "uuid"
}
```

### 3.2 GET `/v1/query/kline/minute?symbol=000001&interval=5min&count=240`

**Response**（200）：
```json
{
  "symbol": "000001.SZ",
  "interval": "5min",
  "items": [
    {
      "symbol": "000001.SZ",
      "datetime": "2026-01-02 09:35",
      "interval": "5min",
      "open": 10.50,
      "close": 10.55,
      "high": 10.55,
      "low": 10.40,
      "volume": 12345,
      "amount": 234567.0
    }
  ],
  "meta": {
    "source": "eastmoney",
    "fetched_at": "2026-01-02T09:36:12.123+08:00",
    "fetched_count": 240,
    "duration_ms": 145,
    "warnings": []
  }
}
```

---

## 4. 头部约定

### 4.1 请求头（Java → Python）

| Header           | 必填 | 说明                                       |
| ---------------- | ---- | ------------------------------------------ |
| `Content-Type`   | ✅   | `application/json`（POST 时）              |
| `X-Service`      | ✅   | 固定 `backend-java`                         |
| `X-Timestamp`    | ✅   | Unix 秒，±60s 有效                         |
| `X-Nonce`        | ✅   | UUID hex，一次性                           |
| `X-Signature`    | ✅   | HMAC-SHA256 hex（详见 `00-overview.md`）   |
| `X-Trace-Id`     | ❌   | 链路追踪 ID（Java 生成并传递给 Python）    |

### 4.2 响应头（Python → Java）

| Header           | 必填 | 说明                                       |
| ---------------- | ---- | ------------------------------------------ |
| `X-Trace-Id`     | ✅   | 原样返回（用于日志关联）                   |
| `X-Source`       | ✅   | 实际命中的数据源（冗余在 body meta 中也带） |
| `X-Duration-Ms`  | ✅   | Python 处理耗时                              |
| `X-Fallback-Hit` | ❌   | `true` 表示走了 fallback（便于告警）         |

---

## 5. 接口废弃流程

1. **标记**：在 OpenAPI 注释加 `deprecated: true` + 响应头 `Deprecation: true`
2. **观测**：保留 1 个季度，期间告警未使用量
3. **下线**：返回 410 Gone，body 含迁移建议

```python
@router.post("/v1/collect/kline/legacy", deprecated=True, responses={410: {"description": "Moved to /v1/collect/kline/daily"}})
async def legacy_endpoint():
    raise HTTPException(
        status_code=410,
        detail={
            "code": 41001,
            "msg": "endpoint moved, please use /v1/collect/kline/daily"
        }
    )
```

---

## 6. 接口版本记录

| 版本 | 日期       | 变更                                                       |
| ---- | ---------- | ---------------------------------------------------------- |
| v1.0 | 2026-09-26 | 初版：日 K / 分 K / 股票基础 / 财务 / 资金 / 概念 / 市场 |

---

## 7. 接口验收 checklist

- [ ] 所有接口走 HMAC 验签（无密钥 = 401）
- [ ] 所有接口走 IP 白名单（不在白名单 = 403）
- [ ] 所有接口走 nonce 一次性（重放 = 401）
- [ ] 所有接口走 timestamp 校验（>60s 偏差 = 401）
- [ ] 所有响应带 `meta.source` 字段
- [ ] 所有响应带 `meta.fetched_at` / `duration_ms`
- [ ] 所有响应带 `X-Trace-Id` / `X-Source` / `X-Duration-Ms` 头部
- [ ] 所有错误响应统一格式（`code` / `msg` / `trace_id`）
- [ ] 所有 Python DTO 在 `02-data-objects.md` 中有定义
- [ ] 所有 Java DTO 在 `03-java-simplify.md` 中有对应
- [ ] 所有接口都有单元测试 + 集成测试

---

## 8. 变更记录

| 版本  | 日期       | 变更人 | 变更内容 |
| ----- | ---------- | ------ | -------- |
| v0.1  | 2026-09-26 | -      | 初稿    |
