# Step 01: 什么是 LangGraph

## 学习目标
理解 LangGraph 的基本概念、使用场景、架构设计

## 概念速览

```
LangGraph = LangChain + Graph
         = LLM 应用 + 图结构

解决的问题：
├── 多步骤 AI 任务
├── 循环和条件分支
├── 状态持久化
└── 人机交互
```

## 什么是 LangGraph？

### 对比普通 LLM 调用

```python
# 普通 LLM 调用：一步完成
response = llm.invoke("分析一下贵州茅台的股票")
# 简单，但复杂任务难处理
```

```python
# LangGraph：多步骤工作流
graph = StateGraph(StockState)
graph.add_node("fetch_data", fetch_data)
graph.add_node("analyze", analyze)
graph.add_node("report", generate_report)
# → 可控制每一步
# → 可循环、可分支
# → 可中断等待输入
```

### 使用场景

| 场景 | 普通 LLM | LangGraph |
|------|----------|-----------|
| 简单问答 | ✅ | ❌ |
| 新闻情感分析 | ⚠️ 可以 | ✅ 更精确 |
| 多步骤分析 | ❌ | ✅ |
| 需要回滚重试 | ❌ | ✅ |
| 实时数据 + 分析 | ⚠️ | ✅ |

## LangGraph 核心概念

```
StateGraph
├── State（状态）→ 定义工作流的状态结构
├── Node（节点）→ 执行特定任务的函数
├── Edge（边）  → 连接节点，控制流程
└── Graph（图） → 节点和边的组合
```

### 基本结构

```python
from langgraph.graph import StateGraph, END

# 1. 定义状态
class State(TypedDict):
    messages: list
    stock_code: str
    analysis_result: str

# 2. 定义节点（函数）
def fetch_data(state):
    return {"messages": ["数据已获取"]}

def analyze(state):
    return {"messages": ["分析完成"]}

# 3. 创建图
graph = StateGraph(State)
graph.add_node("fetch", fetch_data)
graph.add_node("analyze", analyze)
graph.add_edge("fetch", "analyze")  # fetch → analyze

# 4. 编译
app = graph.compile()

# 5. 运行
result = app.invoke({"messages": [], "stock_code": "600519"})
```

## 任务

### 任务 1: 安装依赖

创建 `demo_01_intro.py`：

```python
"""
LangGraph 简介
"""
print("=" * 50)
print("LangGraph 入门示例")
print("=" * 50)

# 检查版本
try:
    import langgraph
    print(f"✅ LangGraph 版本: {langgraph.__version__}")
except ImportError:
    print("❌ 请先安装 LangGraph: pip install langgraph")
    exit(1)

try:
    from langchain_core.messages import HumanMessage, AIMessage
    print("✅ LangChain Core 已安装")
except ImportError:
    print("❌ 请先安装 LangChain: pip install langchain-core")
    exit(1)

print("\n基本概念:")
print("""
1. StateGraph - 工作流图
2. Node - 节点（执行任务的函数）
3. Edge - 边（连接节点，控制流程）
4. State - 状态（工作流中的数据）
""")
```

### 任务 2: 理解状态管理

```python
"""
状态（State）示例
"""
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

# 定义状态结构
class StockAnalysisState(TypedDict):
    """股票分析状态"""
    # 基本信息
    stock_code: str
    stock_name: str
    
    # 消息历史
    messages: Annotated[list, add_messages]
    
    # 分析结果
    price_data: dict | None
    anomaly_detected: bool
    anomaly_details: str
    report: str

# 使用状态
initial_state = StockAnalysisState(
    stock_code="600519",
    stock_name="贵州茅台",
    messages=[],
    price_data=None,
    anomaly_detected=False,
    anomaly_details="",
    report=""
)

print("初始状态:")
for key, value in initial_state.items():
    print(f"  {key}: {value}")
```

### 任务 3: 简单工作流

```python
"""
简单的工作流示例
"""
from langgraph.graph import StateGraph, START, END

# 定义状态
class SimpleState(TypedDict):
    step: str
    result: str

# 定义节点
def step_1(state):
    return {"step": "step_1_done", "result": "第一步完成"}

def step_2(state):
    return {"step": "step_2_done", "result": "第二步完成"}

def step_3(state):
    return {"step": "step_3_done", "result": "第三步完成"}

# 创建图
workflow = StateGraph(SimpleState)

# 添加节点
workflow.add_node("step_1", step_1)
workflow.add_node("step_2", step_2)
workflow.add_node("step_3", step_3)

# 添加边
workflow.add_edge(START, "step_1")
workflow.add_edge("step_1", "step_2")
workflow.add_edge("step_2", "step_3")
workflow.add_edge("step_3", END)

# 编译
app = workflow.compile()

# 运行
print("\n运行工作流:")
result = app.invoke({"step": "start", "result": ""})

print("\n最终状态:")
for key, value in result.items():
    print(f"  {key}: {value}")
```

## 概念回顾

| 概念 | 作用 | 类比 |
|------|------|------|
| **State** | 工作流中的数据 | 流水线上传递的产品 |
| **Node** | 执行任务的函数 | 流水线上的工作站 |
| **Edge** | 连接节点 | 流水线上的传送带 |
| **Graph** | 整体工作流 | 完整的流水线 |

## 下一步
阅读 `../docs/analysis/01_what_is_langgraph.md` 深入理解
