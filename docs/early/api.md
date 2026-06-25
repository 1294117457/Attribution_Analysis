# API 接口文档

**版本**：v2.0  
**日期**：2026年6月  
**Base URL**：`http://localhost:3000/api`

---

## 目录

1. [分析接口](#1-分析接口)
2. [反馈接口](#2-反馈接口)
3. [经验接口](#3-经验接口)
4. [数据接口](#4-数据接口)
5. [健康检查](#5-健康检查)

---

## 1. 分析接口

### 1.1 发起分析

发起一个新的归因分析任务。

**请求**

```
POST /analyze
Content-Type: multipart/form-data
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 否 | CSV 文件（与 dataSourceId 二选一） |
| dataSourceId | string | 否 | 数据源 ID（与 file 二选一） |
| metric | string | 是 | 分析指标名称 |
| dimensions | string | 是 | 维度列表，逗号分隔（如 `region,category`） |
| compareType | string | 是 | 比较类型：`MONTH_OVER_MONTH` / `YEAR_OVER_YEAR` / `PERIOD_OVER_PERIOD` |
| currentPeriod | string | 否 | 当前期日期（YYYY-MM），默认上月 |
| baselinePeriod | string | 否 | 对比期日期（YYYY-MM），默认上上年同期 |

**请求示例**

```bash
curl -X POST http://localhost:3000/api/analyze \
  -H "Authorization: Bearer <token>" \
  -F "file=@data.csv" \
  -F "metric=比特币价格" \
  -F "dimensions=区域,交易所" \
  -F "compareType=YEAR_OVER_YEAR"
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "analysis_20240625_001",
    "status": "completed",
    "createdAt": "2026-06-25T10:00:00Z",

    "anomaly": {
      "isAnomaly": true,
      "score": 0.92,
      "methods": [
        {
          "name": "zscore",
          "result": true,
          "value": 3.2,
          "threshold": 3.0,
          "description": "超出3倍标准差"
        },
        {
          "name": "yoy_change",
          "result": true,
          "value": 0.25,
          "threshold": 0.15,
          "description": "同比变化25%"
        }
      ],
      "signal": {
        "direction": "down",
        "velocity": -0.08,
        "acceleration": -0.02,
        "inflection": true,
        "seasonality": false
      },
      "reason": "检测到显著下跌，符合V型反转特征"
    },

    "attribution": {
      "contributions": [
        {
          "dimension": "亚洲市场",
          "baseline": 45000,
          "current": 42000,
          "change": -3000,
          "contributionPercent": 45.5
        },
        {
          "dimension": "美国市场",
          "baseline": 38000,
          "current": 36500,
          "change": -1500,
          "contributionPercent": 22.7
        },
        {
          "dimension": "欧洲市场",
          "baseline": 28000,
          "current": 27500,
          "change": -500,
          "contributionPercent": 7.6
        }
      ],
      "totalChange": -6600,
      "topDrivers": [],
      "topDraggers": ["亚洲市场", "美国市场"]
    },

    "experience": {
      "matched": {
        "id": "exp_2023_06_25_001",
        "confidence": 0.87,
        "similarity": 0.91,
        "conclusion": "去年同期的下跌由美联储加息预期导致..."
      },
      "isReused": true
    },

    "report": {
      "summary": "比特币今日出现显著下跌，亚洲市场为主要拖累因素",
      "insights": [
        "亚洲市场贡献了45.5%的下跌幅度，是主要拖累因素",
        "下跌呈现V型反转特征，可能与短期恐慌情绪相关",
        "与去年同期模式相似度91%，历史经验显示此类下跌通常在3-5日内恢复"
      ],
      "suggestions": [
        "建议关注亚洲市场情绪变化",
        "可考虑在低位适度配置，但需设置止损",
        "建议持续关注美联储政策动向"
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
    "code": "INVALID_FILE_FORMAT",
    "message": "仅支持 CSV 格式文件",
    "details": "上传的文件格式为 .xlsx，请转换为 CSV 后重试"
  }
}
```

---

### 1.2 查询分析状态

查询异步分析任务的状态。

**请求**

```
GET /analyze/:id/status
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "analysis_20240625_001",
    "status": "processing",
    "progress": 65,
    "currentStep": "attribution_analysis",
    "startedAt": "2026-06-25T10:00:00Z",
    "estimatedTimeRemaining": 3
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

## 2. 反馈接口

### 2.1 提交反馈

对分析结果提交用户反馈。

**请求**

```
POST /feedback
Content-Type: application/json
Authorization: Bearer <token>
```

**请求体**

```json
{
  "analysisId": "analysis_20240625_001",
  "experienceId": "exp_2023_06_25_001",
  "isHelpful": true,
  "rating": 5,
  "comment": "分析准确，与实际情况吻合",
  "correction": null
}
```

**参数说明**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| analysisId | string | 是 | 分析 ID |
| experienceId | string | 否 | 关联的经验 ID |
| isHelpful | boolean | 是 | 分析是否有帮助 |
| rating | number | 否 | 评分 1-5 |
| comment | string | 否 | 详细评论 |
| correction | string | 否 | 修正内容（当 isHelpful=false 时建议填写） |

**响应**

```json
{
  "success": true,
  "data": {
    "feedbackId": "fb_20240625_001",
    "experience": {
      "id": "exp_2023_06_25_001",
      "previousConfidence": 0.87,
      "newConfidence": 0.92,
      "updatedAt": "2026-06-25T10:05:00Z"
    },
    "message": "感谢反馈，经验置信度已更新"
  }
}
```

---

### 2.2 获取反馈历史

获取当前用户的反馈历史。

**请求**

```
GET /feedback/history
Authorization: Bearer <token>
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| limit | number | 20 | 每页数量 |
| isHelpful | boolean | - | 按有帮助筛选 |

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "fb_20240625_001",
        "analysisId": "analysis_20240625_001",
        "isHelpful": true,
        "rating": 5,
        "comment": "分析准确",
        "createdAt": "2026-06-25T10:05:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 42,
      "totalPages": 3
    }
  }
}
```

---

## 3. 经验接口

### 3.1 查询经验库

获取匹配的经验记录。

**请求**

```
GET /experiences
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | number | 1 | 页码 |
| limit | number | 20 | 每页数量 |
| minConfidence | number | 0 | 最低置信度 |
| metric | string | - | 按指标筛选 |
| startDate | string | - | 开始日期 |
| endDate | string | - | 结束日期 |

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "exp_2023_06_25_001",
        "metric": "比特币价格",
        "confidence": 0.87,
        "feedbackCount": 15,
        "anomaly": {
          "isAnomaly": true,
          "score": 0.92
        },
        "conclusion": "去年同期的下跌由美联储加息预期导致...",
        "createdAt": "2023-06-25T10:00:00Z",
        "updatedAt": "2026-06-20T08:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 156,
      "totalPages": 8
    }
  }
}
```

---

### 3.2 获取经验详情

获取单条经验的详细信息。

**请求**

```
GET /experiences/:id
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "exp_2023_06_25_001",
    "metric": "比特币价格",
    "dimensions": ["区域", "交易所"],
    "compareType": "YEAR_OVER_YEAR",

    "features": {
      "zscore": 3.2,
      "changeRate": 0.25,
      "direction": -1,
      "velocity": -0.08,
      "acceleration": -0.02,
      "inflection": true,
      "seasonality": false
    },

    "anomaly": {
      "isAnomaly": true,
      "score": 0.92,
      "methods": [...]
    },

    "attribution": {
      "contributions": [...]
    },

    "conclusion": "去年同期的下跌由美联储加息预期导致...",
    "confidence": 0.87,
    "feedbackCount": 15,
    "helpfulCount": 12,
    "unhelpfulCount": 3,

    "createdAt": "2023-06-25T10:00:00Z",
    "updatedAt": "2026-06-20T08:30:00Z"
  }
}
```

---

### 3.3 删除经验

删除指定的经验记录（仅管理员）。

**请求**

```
DELETE /experiences/:id
Authorization: Bearer <token> (需要 admin 角色)
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "exp_2023_06_25_001",
    "deleted": true
  }
}
```

---

### 3.4 批量更新置信度

根据反馈批量更新经验置信度（定时任务）。

**请求**

```
POST /experiences/batch-update-confidence
Authorization: Bearer <token> (仅系统调用)
```

**响应**

```json
{
  "success": true,
  "data": {
    "updatedCount": 25,
    "deletedLowConfidence": 3,
    "promotedHighConfidence": 5
  }
}
```

---

## 4. 数据接口

### 4.1 上传数据文件

上传 CSV 数据文件。

**请求**

```
POST /data/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>
```

**参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | 是 | CSV 文件 |
| name | string | 是 | 数据源名称 |
| dateColumn | string | 是 | 日期列名 |
| metricColumns | string | 是 | 指标列名，逗号分隔 |
| dimensionColumns | string | 否 | 维度列名，逗号分隔 |
| delimiter | string | 否 | 分隔符，默认 `,` |

**响应**

```json
{
  "success": true,
  "data": {
    "id": "ds_20240625_001",
    "name": "比特币历史数据",
    "recordCount": 3650,
    "dateRange": {
      "start": "2020-01-01",
      "end": "2025-12-31"
    },
    "columns": ["date", "price", "volume", "region", "exchange"]
  }
}
```

---

### 4.2 获取数据源列表

获取已上传的数据源列表。

**请求**

```
GET /data/sources
```

**响应**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "ds_20240625_001",
        "name": "比特币历史数据",
        "type": "csv",
        "recordCount": 3650,
        "dateRange": {
          "start": "2020-01-01",
          "end": "2025-12-31"
        },
        "createdAt": "2026-06-20T10:00:00Z"
      },
      {
        "id": "ds_binance_btcusdt",
        "name": "币安 BTC/USDT 实时数据",
        "type": "api",
        "recordCount": null,
        "lastSync": "2026-06-25T10:00:00Z"
      }
    ]
  }
}
```

---

### 4.3 预览数据

预览数据文件的前 N 行。

**请求**

```
GET /data/sources/:id/preview
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| rows | number | 10 | 预览行数 |

**响应**

```json
{
  "success": true,
  "data": {
    "columns": ["date", "price", "volume", "region"],
    "rows": [
      ["2026-06-01", 45000.00, 2500000, "亚洲"],
      ["2026-06-02", 44500.00, 2800000, "亚洲"],
      ["2026-06-03", 43000.00, 3500000, "美国"]
    ]
  }
}
```

---

### 4.4 删除数据源

删除指定的数据源。

**请求**

```
DELETE /data/sources/:id
Authorization: Bearer <token>
```

**响应**

```json
{
  "success": true,
  "data": {
    "id": "ds_20240625_001",
    "deleted": true
  }
}
```

---

## 5. 健康检查

### 5.1 健康检查

获取系统健康状态。

**请求**

```
GET /health
```

**响应**

```json
{
  "status": "healthy",
  "timestamp": "2026-06-25T10:00:00Z",
  "version": "2.0.0",
  "services": {
    "database": "connected",
    "vectorDb": "connected",
    "llm": "available"
  },
  "uptime": 86400
}
```

---

### 5.2 指标

获取 Prometheus 格式的指标。

**请求**

```
GET /metrics
```

**响应**

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/analyze",status="200"} 1523

# HELP analysis_duration_seconds Analysis duration
# TYPE analysis_duration_seconds histogram
analysis_duration_seconds_bucket{le="1"} 234
analysis_duration_seconds_bucket{le="5"} 1523
```

---

## 错误码说明

| 错误码 | HTTP 状态 | 说明 |
|--------|-----------|------|
| `INVALID_FILE_FORMAT` | 400 | 文件格式错误 |
| `MISSING_PARAMETER` | 400 | 缺少必填参数 |
| `INVALID_PARAMETER` | 400 | 参数值无效 |
| `UNAUTHORIZED` | 401 | 未认证 |
| `FORBIDDEN` | 403 | 无权限 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `ANALYSIS_NOT_FOUND` | 404 | 分析任务不存在 |
| `EXPERIENCE_NOT_FOUND` | 404 | 经验记录不存在 |
| `RATE_LIMITED` | 429 | 请求过于频繁 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `LLM_ERROR` | 502 | AI 服务调用失败 |
| `VECTOR_DB_ERROR` | 502 | 向量数据库错误 |

---

## 认证说明

除 `/health` 和 `/metrics` 接口外，其他接口需要 Bearer Token 认证：

```bash
curl -H "Authorization: Bearer <token>" http://localhost:3000/api/analyze
```

---

## 相关文档

- [架构文档](./architecture.md)
- [快速开始](./getting-started.md)
- [部署指南](./deployment.md)
