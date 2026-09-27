# 系统架构文档

**版本**：v4.0  
**日期**：2026年6月  
**技术栈**：Vue-ts + Python LangGraph FastAPI + PostgreSQL pgvector + Redis + Docker

---

## 一、技术选型

### 1.1 后端技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **运行时** | Python 3.11+ | 高性能异步，AI 生态完善 |
| **框架** | FastAPI 0.115 | 高性能 Web 框架，原生异步 OpenAPI |
| **AI 编排** | LangGraph 0.3 | 多 Agent 协作编排，状态管理 |
| **AI 基础** | LangChain 0.3 | LLM 调用、Tool 定义、Prompt 管理 |
| **嵌入模型** | QianfanEmbeddings | 百度千帆 Embedding（中文优化） |
| **LLM** | 通义千问 / GPT-4 | AI 判断和报告生成 |
| **数据库** | PostgreSQL 16 | 关系数据持久化 |
| **向量存储** | pgvector | PostgreSQL 扩展，经验向量存储 |
| **ORM** | SQLAlchemy 2.0 | Python ORM，类型安全 |
| **迁移工具** | Alembic | 数据库版本管理 |
| **缓存** | Redis | 会话缓存、热点数据、限流 |

### 1.2 前端技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **框架** | Vue 3.4+ | 响应式前端框架 |
| **语言** | TypeScript 5.x | 类型安全 |
| **构建** | Vite 5.x | 快速构建工具 |
| **UI 组件** | Element Plus | Vue 3 组件库 |
| **图表** | ECharts 5.x | 瀑布图、折线图、贡献度图 |
| **状态** | Pinia | Vue 3 状态管理 |
| **HTTP** | Axios | API 请求 |

### 1.3 基础设施

| 组件 | 选型 | 说明 |
|------|------|------|
| **容器化** | Docker + Docker Compose | 开发/生产部署 |
| **网关** | Nginx | 反向代理、静态资源 |
| **进程管理** | Uvicorn | Python ASGI 服务器 |

---

## 二、系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         前端层 (Vue 3 + TypeScript)                      │
│  数据上传 → 指标配置 → 看板展示 → 交互式下钻 → 用户反馈                │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Nginx 网关层                                     │
│                     反向代理 + 静态资源服务                               │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     API 网关层 (FastAPI)                                 │
│  POST /api/v1/analyze  POST /api/v1/feedback  GET /api/v1/experiences   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 LangGraph 多 Agent 编排层                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  异常检测    │→ │  情感分析    │→ │  归因分析    │→ │  报告生成  │ │
│  │   Agent      │  │   Agent      │  │   Agent      │  │   Agent    │ │
│  │  (算法+AI)   │  │    (AI)      │  │  (算法+AI)   │  │    (AI)    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│         │                │                │                             │
│         └────────────────┴────────────────┴──────────────────────────┐  │
│                                │                                       │  │
│                          经验检索/存储                                  │  │
└─────────────────────────────────────────────────────────────────────────┘  │
                              │                                           │
                              ▼                                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         算法引擎层                                       │
│  StatisticalDetector  SignalExtractor  ContributionCalculator           │
│  技术指标计算（MA/EMA/RSI/MACD/BOLL）  异常检测（3σ/IQR）              │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         数据接入层                                       │
│       AkShare (A股)  │  PostgreSQL (持久化)  │  Redis (缓存)           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Docker 微服务架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            Nginx 网关                                    │
│                    (反向代理 + 静态资源服务)                              │
│                         端口: 80 / 443                                   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     Frontend     │  │     Backend      │  │     Backend      │
│   (Vue-ts SPA)   │  │   (Python API)   │  │   (Python API)   │
│     端口:80      │  │    端口:8000     │  │    端口:8001     │
│   (Nginx 托管)   │  │                  │  │   (Worker)       │
└─────────────────┘  └────────┬────────┘  └────────┬────────┘
                              │                    │
                              └──────────┬───────────┘
                                         │
          ┌──────────────────────────────┼──────────────────────────────┐
          │                              │                              │
          ▼                              ▼                              ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────┐
│   PostgreSQL      │  │   pgvector       │  │      Redis       │  │  AkShare │
│   + pgvector      │  │   (内嵌)         │  │    (缓存)        │  │ (数据源) │
│    端口:5432     │  │                  │  │    端口:6379    │  │         │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────┘
```

### 2.3 数据流

```
用户发起分析请求
        │
        ▼
┌──────────────────┐
│  数据采集        │  AkShare 采集股票数据
│  (AkShare)       │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  技术指标计算    │  MA/EMA/RSI/MACD/BOLL
│  (Python)        │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  异常检测 Agent   │  8种算法 + AI判断
│  (LangGraph)     │
└──────────────────┘
        │
   经验匹配? ──── Yes ──── 直接复用结论
        │
        No (继续)
        │
        ▼
┌──────────────────┐
│  情感分析 Agent   │  新闻/公告情感提取
│  (LangGraph)     │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  归因分析 Agent   │  基期拆解 + 贡献度
│  (LangGraph)     │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  报告生成 Agent   │  AI 生成业务报告
│  (LangGraph)     │
└──────────────────┘
        │
        ▼
┌──────────────────┐
│  经验保存        │  向量化存入 pgvector
│  (pgvector)      │
└──────────────────┘
        │
        ▼
    返回前端展示
```

---

## 三、LangGraph Agent 设计

### 3.1 核心状态 (State)

```python
# backend/app/agents/types.py
from typing import Optional
from pydantic import BaseModel
from datetime import date

class AnalysisState(BaseModel):
    # 输入
    symbol: str
    trade_date: date
    metric: str = "close"

    # K线数据
    kline_data: dict = {}

    # 异常检测结果
    anomaly: Optional[dict] = None

    # 情感分析结果
    sentiment: Optional[dict] = None

    # 归因分析结果
    attribution: Optional[dict] = None

    # 经验匹配
    experience: Optional[dict] = None

    # 技术指标
    indicators: Optional[dict] = None

    # AI 报告
    report: Optional[dict] = None

    # 元数据
    errors: list[str] = []
    step: str = "start"
```

### 3.2 Agent 节点定义

```python
# backend/app/agents/graphs/analysis_graph.py
from langgraph.graph import StateGraph, END
from app.agents.nodes import (
    data_collection_node,
    indicator_calculation_node,
    anomaly_detection_node,
    sentiment_analysis_node,
    attribution_analysis_node,
    experience_lookup_node,
    experience_save_node,
    report_generation_node,
)

workflow = StateGraph(AnalysisState)

# 添加节点
workflow.add_node("data_collection", data_collection_node)
workflow.add_node("indicator_calculation", indicator_calculation_node)
workflow.add_node("experience_lookup", experience_lookup_node)
workflow.add_node("anomaly_detection", anomaly_detection_node)
workflow.add_node("sentiment_analysis", sentiment_analysis_node)
workflow.add_node("attribution_analysis", attribution_analysis_node)
workflow.add_node("report_generation", report_generation_node)
workflow.add_node("experience_save", experience_save_node)

# 定义边
workflow.set_entry_point("data_collection")
workflow.add_edge("data_collection", "indicator_calculation")
workflow.add_edge("indicator_calculation", "experience_lookup")

# 条件边：经验匹配
workflow.add_conditional_edges(
    "experience_lookup",
    should_skip_analysis,
    {
        "skip": "report_generation",  # 复用经验
        "continue": "anomaly_detection"
    }
)

workflow.add_edge("anomaly_detection", "sentiment_analysis")
workflow.add_edge("sentiment_analysis", "attribution_analysis")
workflow.add_edge("attribution_analysis", "report_generation")
workflow.add_edge("report_generation", "experience_save")
workflow.add_edge("experience_save", END)

graph = workflow.compile()
```

### 3.3 异常检测 Agent

```python
# backend/app/agents/nodes/anomaly_detection.py
from app.agents.nodes.base import base_node
from app.services.detectors import (
    ZScoreDetector,
    IQRDetector,
    DirectionDetector,
    VelocityDetector,
    InflectionDetector,
)

@base_node
async def anomaly_detection_node(state: AnalysisState) -> dict:
    symbol = state.symbol
    kline_data = state.kline_data

    # 1. 算法检测
    detectors = [
        ZScoreDetector(threshold=3.0),
        IQRDetector(k=1.5),
        DirectionDetector(),
        VelocityDetector(),
        InflectionDetector(),
    ]

    algorithm_results = []
    for detector in detectors:
        result = await detector.detect(kline_data)
        algorithm_results.append(result)

    # 2. AI 判断（综合算法结果）
    llm = get_llm()
    ai_decision = await llm.ainvoke([
        SystemMessage('你是一个金融异常检测专家...'),
        HumanMessage(JSON.dumps({
            "algorithm_results": algorithm_results,
            "kline_data": kline_data
        }))
    ])

    return {
        "anomaly": {
            "is_anomaly": ai_decision.is_anomaly,
            "score": ai_decision.confidence,
            "methods": algorithm_results,
            "signal": extract_signals(kline_data),
            "reason": ai_decision.reason
        },
        "step": "anomaly_detection"
    }
```

### 3.4 情感分析 Agent

```python
# backend/app/agents/nodes/sentiment_analysis.py
from langchain.schema import SystemMessage, HumanMessage
from app.agents.nodes.base import base_node
from app.services.sentiment import SentimentAnalyzer

@base_node
async def sentiment_analysis_node(state: AnalysisState) -> dict:
    symbol = state.symbol
    trade_date = state.trade_date

    # 1. 获取相关新闻
    news = await fetch_news(symbol, trade_date)

    # 2. LLM 情感分析
    llm = get_llm()
    sentiment_result = await llm.ainvoke([
        SystemMessage('''你是一个金融情感分析专家。
分析新闻对股票的影响，给出：
- sentiment: positive/negative/neutral
- score: -1.0 到 1.0
- key_events: 关键事件列表'''),
        HumanMessage(JSON.dumps({"news": news}))
    ])

    return {
        "sentiment": {
            "label": sentiment_result.sentiment,
            "score": sentiment_result.score,
            "key_events": sentiment_result.key_events,
            "news_count": len(news)
        },
        "step": "sentiment_analysis"
    }
```

### 3.5 归因分析 Agent

```python
# backend/app/agents/nodes/attribution_analysis.py
from app.agents.nodes.base import base_node
from app.services.attribution import ContributionCalculator

@base_node
async def attribution_analysis_node(state: AnalysisState) -> dict:
    anomaly = state.anomaly
    sentiment = state.sentiment
    indicators = state.indicators

    # 1. 贡献度计算
    calculator = ContributionCalculator()
    contributions = calculator.calculate(
        anomaly=anomaly,
        sentiment=sentiment,
        indicators=indicators
    )

    # 2. 核心驱动因素排序
    sorted_contributions = sort_by_impact(contributions)

    # 3. AI 业务洞察
    llm = get_llm()
    insights = await llm.ainvoke([
        SystemMessage('''你是一个金融归因分析专家。
基于异常检测和情感分析结果，给出归因结论。'''),
        HumanMessage(JSON.dumps({
            "anomaly": anomaly,
            "sentiment": sentiment,
            "contributions": sorted_contributions[:5]
        }))
    ])

    return {
        "attribution": {
            "contributions": sorted_contributions,
            "total_change": sum(c["change"] for c in contributions),
            "top_drivers": [c["name"] for c in sorted_contributions if c["change"] > 0][:3],
            "top_draggers": [c["name"] for c in sorted_contributions if c["change"] < 0][:3],
            "conclusion": insights.conclusion
        },
        "step": "attribution_analysis"
    }
```

### 3.6 报告生成 Agent

```python
# backend/app/agents/nodes/report_generation.py
from langchain.schema import SystemMessage, HumanMessage
from app.agents.nodes.base import base_node

@base_node
async def report_generation_node(state: AnalysisState) -> dict:
    anomaly = state.anomaly
    sentiment = state.sentiment
    attribution = state.attribution
    experience = state.experience

    llm = get_llm()

    report = await llm.ainvoke([
        SystemMessage('''你是一个专业的金融分析师，生成简洁专业的分析报告。

格式要求：
1. 结论先行
2. 使用业务语言，避免技术术语
3. 提供可行动的建議
4. 参考历史相似案例'''),
        HumanMessage(JSON.dumps({
            "symbol": state.symbol,
            "trade_date": str(state.trade_date),
            "anomaly": anomaly,
            "sentiment": sentiment,
            "attribution": attribution,
            "experience": experience.get("matched", {}).get("conclusion") if experience else None
        }))
    ])

    return {
        "report": {
            "summary": report.summary,
            "insights": report.insights,
            "suggestions": report.suggestions
        },
        "step": "report_generation"
    }
```

---

## 四、数据模型

### 4.1 核心数据模型

```python
# backend/app/models/domain/kline.py
from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class StockKline(Base):
    __tablename__ = "stock_klines"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    open = Column(Numeric(10, 2))
    high = Column(Numeric(10, 2))
    low = Column(Numeric(10, 2))
    close = Column(Numeric(10, 2))
    volume = Column(Numeric(20, 2))
    amount = Column(Numeric(20, 2))

    # 技术指标缓存（JSONB）
    indicators = Column(JSONB, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

# backend/app/models/domain/experience.py
from sqlalchemy import Column, Integer, String, Date, JSON, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB, VECTOR
from app.db.session import Base

class AttributionCase(Base):
    __tablename__ = "attribution_cases"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    trade_date = Column(Date, nullable=False, index=True)
    case_type = Column(String(50))  # 异常类型
    indicators = Column(JSONB, default=dict)
    anomaly_types = Column(JSONB, default=list)
    sentiment = Column(String(20))
    attribution_result = Column(JSONB, default=dict)
    experience_vector = Column(Vector(768))  # pgvector
    similarity_threshold = Column(Float, default=0.85)
    confidence = Column(Float, default=0.5)
    feedback_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## 五、pgvector 经验系统设计

### 5.1 向量化特征 (768维)

基于百度千帆 Embedding 模型生成：

| 来源 | 维度 | 说明 |
|------|------|------|
| 异常描述 | 256维 | 异常类型 + 严重程度 + 持续时间 |
| 指标特征 | 256维 | 技术指标状态 + 变化模式 |
| 情感摘要 | 128维 | 新闻情感 + 关键事件 |
| 归因结论 | 128维 | 归因原因 + 贡献度排序 |

### 5.2 经验检索流程

```
新分析请求
     │
     ▼
异常 + 指标 + 情感 → 构造向量文本
     │
     ▼
Embedding → 768维向量
     │
     ▼
pgvector 余弦相似度检索（阈值 > 0.85）
     │
     ├─ 找到匹配 ──→ 复用结论，更新置信度
     │
     └─ 未找到 ──→ 完整分析流程 → 保存为新经验
```

### 5.3 SQL 查询示例

```sql
-- 创建向量扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建案例表
CREATE TABLE attribution_cases (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20),
    trade_date DATE,
    case_type VARCHAR(50),
    indicators JSONB,
    anomaly_types JSONB,
    sentiment VARCHAR(20),
    attribution_result JSONB,
    experience_vector VECTOR(768),
    similarity_threshold FLOAT DEFAULT 0.85,
    confidence FLOAT DEFAULT 0.5,
    feedback_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建 HNSW 索引（加速相似搜索）
CREATE INDEX idx_experience_vector_hnsw
ON attribution_cases
USING hnsw (experience_vector vector_cosine_ops);

-- 相似案例查询
SELECT
    id,
    symbol,
    trade_date,
    case_type,
    attribution_result,
    1 - (experience_vector <=> $1) AS similarity
FROM attribution_cases
WHERE symbol = $2
  AND case_type = $3
  AND trade_date < $4
ORDER BY experience_vector <=> $1
LIMIT 5;
```

### 5.4 置信度更新

```python
# backend/app/services/experience/feedback.py
async def update_confidence(experience_id: int, feedback: FeedbackUpdate):
    experience = await get_experience(experience_id)

    if feedback.is_helpful:
        experience.confidence = min(1.0, experience.confidence + 0.1)
    else:
        experience.confidence = max(0.0, experience.confidence - 0.15)
        if feedback.correction:
            await create_corrected_experience(experience, feedback.correction)

    experience.feedback_count += 1
    await save_experience(experience)
    return experience
```

---

## 六、Redis 缓存设计

### 6.1 缓存策略

| 数据类型 | 缓存键 | TTL | 说明 |
|----------|--------|-----|------|
| K线数据 | `kline:{symbol}:{date}` | 1小时 | 热点股票缓存 |
| 技术指标 | `indicator:{symbol}:{date}:{period}` | 30分钟 | 计算结果缓存 |
| 分析结果 | `analysis:{id}` | 24小时 | 分析结果缓存 |
| 用户会话 | `session:{user_id}` | 30分钟 | 会话数据 |
| API限流 | `rate:{user_id}:{endpoint}` | 1分钟 | 限流计数 |

### 6.2 缓存代码示例

```python
# backend/app/cache/redis_client.py
from redis.asyncio import Redis
from functools import wraps

redis = Redis.from_url("redis://localhost:6379", decode_responses=True)

async def cache_get(key: str) -> Optional[str]:
    return await redis.get(key)

async def cache_set(key: str, value: str, ttl: int = 3600):
    await redis.setex(key, ttl, value)

# 缓存装饰器
def cached(ttl: int = 3600, key_prefix: str = ""):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            cached_value = await cache_get(cache_key)
            if cached_value:
                return json.loads(cached_value)

            result = await func(*args, **kwargs)
            await cache_set(cache_key, json.dumps(result), ttl)
            return result
        return wrapper
    return decorator

@cached(ttl=3600, key_prefix="kline")
async def get_kline_data(symbol: str, date: str) -> dict:
    # 从数据库或 AkShare 获取
    pass
```

---

## 七、API 设计

### 7.1 核心接口

```
POST /api/v1/analyze          # 发起分析
POST /api/v1/feedback         # 用户反馈
GET  /api/v1/experiences     # 查询经验库
GET  /api/v1/experiences/:id  # 获取单条经验
GET  /api/v1/klines          # 获取K线数据
POST /api/v1/klines/collect   # 采集K线数据
GET  /api/v1/indicators      # 获取技术指标
GET  /health                  # 健康检查
```

详细接口定义见 [API 文档](./api.md)

---

## 八、安全设计

### 8.1 认证授权

- JWT Token 认证
- 角色基础访问控制 (RBAC)
- API 限流 (Redis + Nginx)

### 8.2 数据安全

- SQL 注入防护 (SQLAlchemy 参数化查询)
- XSS 防护 (前端转义)
- CORS 配置 (Nginx)
- 敏感数据加密

---

## 九、性能优化

### 9.1 后端优化

- **异步处理**：FastAPI 原生异步，AI 调用不阻塞主流程
- **缓存**：Redis 热点数据缓存
- **数据库**：索引优化、连接池复用
- **向量检索**：pgvector HNSW 索引加速

### 9.2 前端优化

- **懒加载**：路由和组件按需加载
- **虚拟滚动**：长列表虚拟滚动
- **图表优化**：ECharts 按需引入，减少包体积
- **缓存**：Pinia 持久化

---

## 十、监控与日志

### 10.1 日志

- 结构化日志 (Python logging)
- 日志级别：error, warn, info, debug
- 日志输出：文件 + 控制台

### 10.2 监控

- 健康检查端点 `/health`
- Prometheus 指标暴露（可选）
- 关键业务指标埋点

---

## 十一、环境配置

### 11.1 开发环境

```env
# .env.development
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/attribution

# Redis
REDIS_URL=redis://localhost:6379

# LLM (通义千问)
LLM_PROVIDER=qianfan
QWEN_API_KEY=sk-xxx
QWEN_MODEL=qwen-turbo

# Embedding
EMBEDDING_PROVIDER=qianfan
EMBEDDING_MODEL=text-embedding-v3

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 11.2 生产环境

```env
# .env.production
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000

# 数据库
DATABASE_URL=postgresql://user:password@postgres:5432/attribution?sslmode=require

# Redis
REDIS_URL=redis://:password@redis:6379

# LLM
LLM_PROVIDER=qianfan
QWEN_API_KEY=${QWEN_API_KEY}
QWEN_MODEL=qwen-plus

# Embedding
EMBEDDING_PROVIDER=qianfan
EMBEDDING_MODEL=text-embedding-v3

# CORS
CORS_ORIGINS=https://your-domain.com
```

---

## 十二、相关文档

- [快速开始](./getting-started.md) - 环境配置和启动
- [API 文档](./api.md) - 接口详细定义
- [部署指南](./deployment.md) - Docker 部署
- [数据源说明](./data-source.md) - AkShare 数据接入
