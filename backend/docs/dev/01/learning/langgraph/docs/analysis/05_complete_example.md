# 完整示例详解

## 一、项目结构总结

```
股票异常检测 Agent
│
├── 工具 (Tools)
│   ├── get_stock_realtime    # 实时行情
│   ├── get_stock_history     # 历史数据
│   ├── detect_price_anomaly  # 价格异常检测
│   ├── detect_volume_anomaly # 成交量异常检测
│   ├── generate_report       # 报告生成
│   └── send_alert            # 警报发送
│
├── 状态 (State)
│   ├── stock_code            # 股票代码
│   ├── realtime_data         # 实时数据
│   ├── history_data          # 历史数据
│   ├── anomalies            # 异常列表
│   ├── report               # 报告
│   └── alert_sent           # 警报状态
│
└── 工作流 (Workflow)
    fetch_data → analyze → aggregate → report → alert/skip → END
```

## 二、与 FastAPI 集成

### 创建 API 接口

```python
# app/api/anomaly.py
from fastapi import APIRouter, Depends
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from typing import Literal, TypedDict, Annotated
from langgraph.graph import add_messages

router = APIRouter(prefix="/api/v1/anomaly", tags=["异常检测"])

class AnomalyRequest(BaseModel):
    """异常检测请求"""
    stock_code: str

class AnomalyResponse(BaseModel):
    """异常检测响应"""
    stock_code: str
    has_anomaly: bool
    anomaly_count: int
    severity: str
    report: str
    alert_sent: bool

# 复用之前的工具和节点定义...

@router.post("/detect", response_model=AnomalyResponse)
async def detect_anomaly(request: AnomalyRequest):
    """执行异常检测"""
    # 构建初始状态
    initial_state: AnomalyDetectionState = {
        "stock_code": request.stock_code,
        # ... 其他初始字段
    }
    
    # 运行工作流
    result = app.invoke(initial_state)
    
    # 返回结果
    return AnomalyResponse(
        stock_code=request.stock_code,
        has_anomaly=len(result["all_anomalies"]) > 0,
        anomaly_count=len(result["all_anomalies"]),
        severity=determine_severity(result["all_anomalies"]),
        report=result["report"],
        alert_sent=result["alert_sent"]
    )
```

### 异步运行

```python
import asyncio
from langgraph.graph import StateGraph

@router.post("/detect/async")
async def detect_anomaly_async(request: AnomalyRequest):
    """异步执行异常检测"""
    loop = asyncio.get_event_loop()
    
    # 在线程池中运行（避免阻塞）
    result = await loop.run_in_executor(
        None,
        app.invoke,
        {"stock_code": request.stock_code, ...}
    )
    
    return result
```

## 三、状态持久化

```python
from langgraph.checkpoint.memory import MemorySaver

# 创建检查点
checkpointer = MemorySaver()

# 编译工作流
app = workflow.compile(checkpointer=checkpointer)

# 运行
config = {"configurable": {"thread_id": "detection_123"}}
result = app.invoke(initial_state, config)

# 获取状态
snapshot = app.get_state(config)
print(snapshot.values)

# 继续运行
result = app.invoke({"action": "proceed"}, config)
```

## 四、与 LangServe 集成

```python
# serve.py
from langserve import add_routes
from fastapi import FastAPI

app = FastAPI(title="股票异常检测 Agent")

# 添加 LangServe 路由
add_routes(
    app,
    app,  # LangGraph compiled app
    path="/agent"
)

# 运行
# uvicorn serve:app --reload
```

## 五、完整项目结构

```
stock_anomaly_agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py          # 状态定义
│   │   ├── tools.py          # 工具定义
│   │   ├── nodes.py          # 节点函数
│   │   ├── workflow.py       # 工作流
│   │   └── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── anomaly.py        # API 路由
│   └── schemas/
│       └── anomaly.py        # Pydantic 模型
├── tests/
│   ├── test_tools.py
│   ├── test_workflow.py
│   └── test_api.py
├── requirements.txt
└── README.md
```

## 六、测试策略

### 单元测试

```python
# tests/test_tools.py
import pytest
from app.agent.tools import detect_price_anomaly

def test_detect_high_change():
    """测试高涨幅检测"""
    result = detect_price_anomaly.invoke({
        "current": 1500,
        "change_pct": 8.0,
        "history": []
    })
    
    assert result["has_anomaly"] == True
    assert result["count"] == 1
    assert result["anomalies"][0]["type"] == "price_change"

def test_detect_normal():
    """测试正常价格"""
    result = detect_price_anomaly.invoke({
        "current": 1500,
        "change_pct": 1.0,
        "history": []
    })
    
    assert result["has_anomaly"] == False
```

### 集成测试

```python
# tests/test_workflow.py
import pytest
from app.agent.workflow import create_anomaly_workflow

def test_workflow_normal():
    """测试正常工作流"""
    workflow = create_anomaly_workflow()
    
    initial_state = {
        "stock_code": "600519",
        # ... 其他字段
    }
    
    result = workflow.invoke(initial_state)
    
    assert result["report"] != ""
    assert len(result["steps_taken"]) > 0
```

## 七、性能优化

### 并行执行

```python
# 节点内并行调用工具
def analyze(state: AnomalyDetectionState) -> dict:
    # 并行获取多个数据源
    import concurrent.futures
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_price = executor.submit(get_price, state["code"])
        future_news = executor.submit(get_news, state["code"])
        future_volume = executor.submit(get_volume, state["code"])
        
        price = future_price.result()
        news = future_news.result()
        volume = future_volume.result()
    
    return {"price": price, "news": news, "volume": volume}
```

### 缓存

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_price(code: str):
    """缓存价格数据"""
    return fetch_real_price(code)

def workflow_node(state):
    # 使用缓存的价格
    price = get_cached_price(state["code"])
```

## 八、部署建议

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### 环境变量

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    alert_webhook_url: str = ""
    redis_url: str = "redis://localhost:6379"
    
    class Config:
        env_file = ".env"
```

## 九、监控和日志

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_node(state):
    logger.info(f"开始分析 {state['stock_code']}")
    try:
        result = perform_analysis(state)
        logger.info(f"分析完成，发现 {len(result['anomalies'])} 个异常")
        return result
    except Exception as e:
        logger.error(f"分析失败: {e}")
        raise
```

## 十、持续改进

### 添加更多检测规则

```python
@tool
def detect_technical_anomaly(code: str, history: list) -> dict:
    """检测技术指标异常"""
    # 添加均线偏离、MACD 等检测
    anomalies = []
    
    # 均线偏离
    if detect_ma_deviation(history):
        anomalies.append({
            "type": "ma_deviation",
            "severity": "medium",
            "description": "价格偏离均线"
        })
    
    # MACD 背离
    if detect_macd_divergence(history):
        anomalies.append({
            "type": "macd_divergence",
            "severity": "high",
            "description": "MACD 底背离"
        })
    
    return {"has_anomaly": len(anomalies) > 0, "anomalies": anomalies}
```

### 添加人工审核

```python
# 在工作流中添加人工审核节点
workflow.add_conditional_edges(
    "analyze",
    should_review,
    {
        "review": "human_review",
        "auto": "generate_report"
    }
)

# 中断等待人工确认
app = workflow.compile(
    interrupt_before=["send_alert"]
)

# API 审核接口
@app.post("/api/v1/anomaly/{id}/approve")
async def approve_alert(id: str, approved: bool):
    # 人工确认后继续执行
    config = {"configurable": {"thread_id": id}}
    app.invoke({"approved": approved}, config)
```

## 总结

你现在掌握了：

1. **LangGraph 基础**: StateGraph、节点、边
2. **条件分支**: 条件边、循环
3. **工具调用**: @tool、ToolNode
4. **完整工作流**: 组合所有知识
5. **与 FastAPI 集成**: 构建 API 服务

下一步：
- 在你的项目中应用这些知识
- 集成真实的 akshare 数据
- 添加更多 AI 能力（如 LLM 分析）
- 部署和监控
