# API 接口文档

**版本**：v4.0  
**日期**：2026年6月  
**Base URL**：`http://localhost:8000/api/v1`

---

## 目录

1. [分析接口](#1-分析接口)
2. [K线数据接口](#2-k线数据接口)
3. [技术指标接口](#3-技术指标接口)
4. [经验接口](#4-经验接口)
5. [反馈接口](#5-反馈接口)
6. [健康检查](#6-健康检查)

---

## 1. 分析接口

### 1.1 发起分析

发起一个新的归因分析任务。

**请求**

```
POST /api/v1/analyze
Content-Type: application/json
```

**请求体**

```json
{
  "symbol": "600519",
  "trade_date": "2024-06-25",
  "include_news": true,
  "force_refresh": false
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| trade_date | string | 是 | 交易日期（YYYY-MM-DD） |
| include_news | boolean | 否 | 是否包含新闻情感分析，默认 true |
| force_refresh | boolean | 否 | 是否强制刷新（跳过缓存），默认 false |

**请求示例**

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "600519",
    "trade_date": "2024-06-25",
    "include_news": true
  }'
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "analysis_20240625_001",
    "status": "completed",
    "created_at": "2024-06-25T10:00:00Z",
    "processing_time_ms": 2350,

    "anomaly": {
      "is_anomaly": true,
      "score": 0.85,
      "methods": [
        {
          "name": "rsi",
          "result": true,
          "value": 72.5,
          "threshold": 70,
          "description": "RSI 进入超买区域"
        },
        {
          "name": "zscore",
          "result": true,
          "value": 2.8,
          "threshold": 3.0,
          "description": "价格偏离均值 2.8 个标准差"
        }
      ],
      "signal": {
        "direction": "down",
        "velocity": -0.025,
        "acceleration": -0.008,
        "inflection": true,
        "seasonality": false
      }
    },

    "sentiment": {
      "label": "negative",
      "score": -0.35,
      "news_count": 8,
      "key_events": [
        "北向资金净流出 5.2 亿",
        "券商下调目标价",
        "消费数据不及预期"
      ]
    },

    "attribution": {
      "contributions": [
        {
          "factor": "北向资金",
          "change": -2.5,
          "contribution_percent": 45.5
        },
        {
          "factor": "板块轮动",
          "change": -1.8,
          "contribution_percent": 32.7
        },
        {
          "factor": "业绩预期",
          "change": -1.2,
          "contribution_percent": 21.8
        }
      ],
      "total_change": -5.5,
      "top_drivers": [],
      "top_draggers": ["北向资金", "板块轮动", "业绩预期"],
      "conclusion": "茅台下跌主要由北向资金持续流出和板块轮动导致"
    },

    "experience": {
      "matched": {
        "id": 123,
        "similarity": 0.87,
        "confidence": 0.82,
        "trade_date": "2024-03-15",
        "conclusion": "当时下跌由美联储加息预期导致，3 日后反弹"
      },
      "is_reused": true
    },

    "report": {
      "summary": "贵州茅台今日出现调整，RSI 指标显示超买，短期资金面偏紧",
      "insights": [
        "北向资金连续净流出是主要拖累因素，贡献了 45.5% 的下跌幅度",
        "RSI 指标进入超买区域，短期存在调整压力",
        "与历史相似案例匹配度 87%，可参考历史走势"
      ],
      "suggestions": [
        "建议关注北向资金动向，若持续流出需警惕",
        "等待 RSI 回落至合理区间后再考虑介入",
        "关注消费数据边际变化"
      ]
    }
  }
}
```

**错误响应**

```json
{
  "success": false,
  "error": {
    "code": "SYMBOL_NOT_FOUND",
    "message": "股票代码不存在",
    "details": "请检查股票代码 600519 是否正确"
  }
}
```

---

### 1.2 查询分析状态

查询异步分析任务的状态。

**请求**

```
GET /api/v1/analyze/{id}/status
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "analysis_20240625_001",
    "status": "completed",
    "progress": 100,
    "current_step": "report_generation",
    "started_at": "2024-06-25T10:00:00Z",
    "completed_at": "2024-06-25T10:00:02Z"
  }
}
```

**状态说明**

| 状态 | 说明 |
|------|------|
| `pending` | 等待处理 |
| `processing` | 处理中 |
| `completed` | 完成 |
| `failed` | 失败 |

---

### 1.3 获取分析历史

获取历史分析记录。

**请求**

```
GET /api/v1/analyze
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| limit | number | 20 | 每页数量 |
| symbol | string | - | 按股票代码筛选 |
| start_date | string | - | 开始日期 |
| end_date | string | - | 结束日期 |

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "analysis_20240625_001",
        "symbol": "600519",
        "trade_date": "2024-06-25",
        "status": "completed",
        "anomaly_score": 0.85,
        "sentiment_label": "negative",
        "created_at": "2024-06-25T10:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "total_pages": 8
    }
  }
}
```

---

## 2. K线数据接口

### 2.1 获取K线数据

获取股票K线数据。

**请求**

```
GET /api/v1/klines
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| start_date | string | 是 | 开始日期（YYYY-MM-DD） |
| end_date | string | 是 | 结束日期（YYYY-MM-DD） |
| period | string | 否 | 周期：daily/weekly/monthly，默认 daily |

**响应**

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "period": "daily",
    "items": [
      {
        "date": "2024-06-20",
        "open": 1680.00,
        "high": 1695.50,
        "low": 1675.00,
        "close": 1688.20,
        "volume": 3250000,
        "amount": 5480000000
      },
      {
        "date": "2024-06-21",
        "open": 1688.20,
        "high": 1690.00,
        "low": 1670.00,
        "close": 1675.50,
        "volume": 4120000,
        "amount": 6910000000
      }
    ],
    "count": 2
  }
}
```

---

### 2.2 采集K线数据

从 AkShare 采集股票K线数据。

**请求**

```
POST /api/v1/klines/collect
Content-Type: application/json
```

**请求体**

```json
{
  "symbol": "600519",
  "period": "daily",
  "start_date": "2024-01-01",
  "end_date": "2024-06-25"
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| period | string | 否 | 周期：daily/weekly/monthly，默认 daily |
| start_date | string | 否 | 开始日期，默认一年前 |
| end_date | string | 否 | 结束日期，默认今天 |

**响应**

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "period": "daily",
    "records_collected": 120,
    "records_updated": 5,
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-06-25"
    },
    "processing_time_ms": 1520
  }
}
```

---

### 2.3 批量采集K线数据

批量采集多只股票的K线数据。

**请求**

```
POST /api/v1/klines/collect/batch
Content-Type: application/json
```

**请求体**

```json
{
  "symbols": ["600519", "000858", "600036"],
  "period": "daily",
  "start_date": "2024-01-01",
  "end_date": "2024-06-25"
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "total_symbols": 3,
    "completed_symbols": 3,
    "failed_symbols": 0,
    "total_records": 356,
    "results": [
      {"symbol": "600519", "status": "success", "records": 120},
      {"symbol": "000858", "status": "success", "records": 118},
      {"symbol": "600036", "status": "success", "records": 118}
    ]
  }
}
```

---

## 3. 技术指标接口

### 3.1 获取技术指标

获取股票的技术指标数据。

**请求**

```
GET /api/v1/indicators
```

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| symbol | string | 是 | 股票代码 |
| date | string | 是 | 日期（YYYY-MM-DD） |
| indicators | string | 否 | 指标列表，逗号分隔，如 `ma,ema,rsi,macd` |

**可用指标**

| 指标 | 说明 |
|------|------|
| ma | 移动平均线（MA5/MA10/MA20/MA60） |
| ema | 指数移动平均线（EMA12/EMA26） |
| rsi | 相对强弱指数 |
| macd | MACD 指标 |
| boll | 布林带 |
| kdj | KDJ 随机指标 |

**响应**

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "date": "2024-06-25",
    "indicators": {
      "ma5": 1680.50,
      "ma10": 1675.20,
      "ma20": 1668.30,
      "ma60": 1655.80,
      "ema12": 1685.40,
      "ema26": 1672.10,
      "dif": 13.30,
      "dea": 8.50,
      "macd": 9.60,
      "rsi": 58.5,
      "boll_upper": 1720.30,
      "boll_middle": 1668.30,
      "boll_lower": 1616.30
    }
  }
}
```

---

### 3.2 计算自定义指标

根据自定义参数计算指标。

**请求**

```
POST /api/v1/indicators/calculate
Content-Type: application/json
```

**请求体**

```json
{
  "symbol": "600519",
  "start_date": "2024-01-01",
  "end_date": "2024-06-25",
  "indicators": [
    {
      "type": "ma",
      "params": {"period": 20}
    },
    {
      "type": "rsi",
      "params": {"period": 14}
    }
  ]
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "symbol": "600519",
    "indicators": [
      {
        "type": "ma",
        "params": {"period": 20},
        "values": [
          {"date": "2024-01-20", "value": 1650.30},
          {"date": "2024-01-21", "value": 1652.80}
        ]
      },
      {
        "type": "rsi",
        "params": {"period": 14},
        "values": [
          {"date": "2024-06-24", "value": 55.2},
          {"date": "2024-06-25", "value": 58.5}
        ]
      }
    ]
  }
}
```

---

## 4. 经验接口

### 4.1 查询经验库

获取匹配的经验记录。

**请求**

```
GET /api/v1/experiences
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| limit | number | 20 | 每页数量 |
| symbol | string | - | 按股票代码筛选 |
| case_type | string | - | 按案例类型筛选 |
| min_confidence | number | 0 | 最低置信度 |
| start_date | string | - | 开始日期 |
| end_date | string | - | 结束日期 |

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 123,
        "symbol": "600519",
        "trade_date": "2024-03-15",
        "case_type": "异常下跌",
        "confidence": 0.82,
        "feedback_count": 15,
        "anomaly_score": 0.88,
        "sentiment_label": "negative",
        "conclusion": "当时下跌由美联储加息预期导致，3 日后反弹",
        "created_at": "2024-03-15T10:00:00Z",
        "updated_at": "2024-06-20T08:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "total_pages": 8
    }
  }
}
```

---

### 4.2 获取经验详情

获取单条经验的详细信息。

**请求**

```
GET /api/v1/experiences/{id}
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": 123,
    "symbol": "600519",
    "trade_date": "2024-03-15",
    "case_type": "异常下跌",

    "indicators": {
      "ma5": 1720.50,
      "ma20": 1705.30,
      "rsi": 75.2
    },

    "anomaly_types": ["zscore", "direction", "velocity"],
    "sentiment": "negative",

    "attribution_result": {
      "top_drivers": ["北向资金流出", "美股下跌传导"],
      "top_draggers": [],
      "conclusion": "下跌由外部因素导致，基本面无变化"
    },

    "experience_vector": [0.123, -0.456, ...],
    "similarity_threshold": 0.85,
    "confidence": 0.82,
    "feedback_count": 15,
    "helpful_count": 12,
    "unhelpful_count": 3,

    "created_at": "2024-03-15T10:00:00Z",
    "updated_at": "2024-06-20T08:30:00Z"
  }
}
```

---

### 4.3 相似案例搜索

基于当前情况搜索相似历史案例。

**请求**

```
POST /api/v1/experiences/search
Content-Type: application/json
```

**请求体**

```json
{
  "symbol": "600519",
  "trade_date": "2024-06-25",
  "case_type": "异常下跌",
  "indicators": {
    "rsi": 72.5,
    "direction": "down",
    "velocity": -0.025
  },
  "sentiment": "negative",
  "limit": 5
}
```

**响应**

```json
{
  "success": true,
  "data": {
    "results": [
      {
        "id": 123,
        "trade_date": "2024-03-15",
        "similarity": 0.87,
        "confidence": 0.82,
        "case_type": "异常下跌",
        "conclusion": "当时下跌由美联储加息预期导致，3 日后反弹",
        "actual_outcome": "5 日后反弹 3.2%"
      },
      {
        "id": 89,
        "trade_date": "2024-01-20",
        "similarity": 0.82,
        "confidence": 0.75,
        "case_type": "异常下跌",
        "conclusion": "当时下跌由业绩不及预期导致",
        "actual_outcome": "横盘 2 周后继续下跌 5%"
      }
    ]
  }
}
```

---

## 5. 反馈接口

### 5.1 提交反馈

对分析结果提交用户反馈。

**请求**

```
POST /api/v1/feedback
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体**

```json
{
  "analysis_id": "analysis_20240625_001",
  "experience_id": 123,
  "is_helpful": true,
  "rating": 5,
  "comment": "分析准确，与实际情况吻合",
  "correction": null
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| analysis_id | string | 是 | 分析 ID |
| experience_id | integer | 否 | 关联的经验 ID |
| is_helpful | boolean | 是 | 分析是否有帮助 |
| rating | integer | 否 | 评分 1-5 |
| comment | string | 否 | 详细评论 |
| correction | string | 否 | 修正内容（当 is_helpful=false 时建议填写） |

**响应**

```json
{
  "success": true,
  "data": {
    "feedback_id": "fb_20240625_001",
    "experience": {
      "id": 123,
      "previous_confidence": 0.82,
      "new_confidence": 0.87,
      "updated_at": "2024-06-25T10:05:00Z"
    },
    "message": "感谢反馈，经验置信度已更新"
  }
}
```

---

### 5.2 获取反馈历史

获取当前用户的反馈历史。

**请求**

```
GET /api/v1/feedback/history
Authorization: Bearer <token>
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| limit | number | 20 | 每页数量 |
| is_helpful | boolean | - | 按有帮助筛选 |

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "fb_20240625_001",
        "analysis_id": "analysis_20240625_001",
        "symbol": "600519",
        "trade_date": "2024-06-25",
        "is_helpful": true,
        "rating": 5,
        "comment": "分析准确",
        "created_at": "2024-06-25T10:05:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 42,
      "total_pages": 3
    }
  }
}
```

---

## 6. 健康检查

### 6.1 健康检查

获取系统健康状态。

**请求**

```
GET /health
```

**响应**

```json
{
  "status": "healthy",
  "timestamp": "2024-06-25T10:00:00Z",
  "version": "4.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "pgvector": "connected",
    "llm": "available"
  },
  "uptime": 86400
}
```

---

### 6.2 就绪检查

检查服务是否就绪接受请求。

**请求**

```
GET /ready
```

**响应**

```json
{
  "ready": true,
  "checks": {
    "database": true,
    "redis": true,
    "pgvector": true
  }
}
```

---

## 错误码说明

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `INVALID_PARAMETER` | 400 | 参数值无效 |
| `MISSING_PARAMETER` | 400 | 缺少必填参数 |
| `SYMBOL_NOT_FOUND` | 404 | 股票代码不存在 |
| `ANALYSIS_NOT_FOUND` | 404 | 分析任务不存在 |
| `EXPERIENCE_NOT_FOUND` | 404 | 经验记录不存在 |
| `UNAUTHORIZED` | 401 | 未认证 |
| `FORBIDDEN` | 403 | 无权限 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `LLM_ERROR` | 502 | AI 服务调用失败 |
| `DATABASE_ERROR` | 502 | 数据库错误 |
| `REDIS_ERROR` | 502 | Redis 缓存错误 |

---

## 相关文档

- [架构文档](./architecture.md)
- [快速开始](./getting-started.md)
- [部署指南](./deployment.md)
